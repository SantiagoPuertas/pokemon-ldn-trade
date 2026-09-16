#!/usr/bin/env python3
"""Valida un prod.keys para frlg-ldn-trade / kinnay/LDN.

    python3 scripts/check_keys.py [ruta]        # por defecto ~/.switch/prod.keys

Replica EXACTAMENTE las reglas de parseo de `ldn.load_keys()` para que los
problemas salgan aqui, con un mensaje claro, y no en mitad de una conexion LDN
con un KeyError o un ValueError sin contexto.

Nunca imprime el valor de ninguna clave: solo nombres, longitudes y veredicto.
"""

import os
import sys

VERDE = "\033[32m"
ROJO = "\033[31m"
AMAR = "\033[33m"
GRIS = "\033[2m"
NEGR = "\033[1m"
FIN = "\033[0m"


def ok(m):    print("  %s[ OK  ]%s %s" % (VERDE, FIN, m))
def mal(m):   print("  %s[FALLA]%s %s" % (ROJO, FIN, m))
def aviso(m): print("  %s[ ??  ]%s %s" % (AMAR, FIN, m))
def info(m):  print("  %s%s%s" % (GRIS, m, FIN))
def titulo(m): print("\n%s=== %s ===%s" % (NEGR, m, FIN))


# Nombre -> longitud esperada en bytes
SIEMPRE = {
    "aes_kek_generation_source": 16,
    "aes_key_generation_source": 16,
}
# Uno de los dos, segun la version del protocolo que negocie la sesion
MASTER = {
    "master_key_00": 16,   # protocolo LDN v1
    "master_key_12": 16,   # protocolo LDN v3
}


def main():
    ruta = sys.argv[1] if len(sys.argv) > 1 else "~/.switch/prod.keys"
    ruta = os.path.expanduser(ruta)

    fallos = 0
    avisos = 0

    titulo("Fichero")
    if not os.path.isfile(ruta):
        mal("no existe: %s" % ruta)
        info("frlg-ldn-trade lo busca ahi por defecto, o donde le digas con --keys")
        return 1
    ok(ruta)
    info("%d bytes" % os.path.getsize(ruta))

    # Permisos: no deberia ser legible por todo el mundo.
    # Solo tiene sentido en POSIX; en Windows los modos no significan lo mismo.
    modo = os.stat(ruta).st_mode & 0o777
    if os.name != "posix":
        info("permisos: no se comprueban fuera de POSIX")
    elif modo & 0o077:
        aviso("permisos %o: legible por otros usuarios. Arreglalo con:" % modo)
        info("     chmod 600 %s" % ruta)
        avisos += 1
    else:
        ok("permisos %o" % modo)

    # --- Parseo con las reglas EXACTAS de ldn.load_keys() -------------------
    # Esa funcion hace, por cada linea no vacia:
    #     name, key = line.split("=")
    #     keys[name.strip()] = bytes.fromhex(key)
    # O sea: una linea con ningun "=" o con dos revienta con ValueError, y un
    # valor no hexadecimal tambien. Ni comentarios ni cabeceras de seccion.
    titulo("Parseo (reglas de ldn.load_keys)")
    claves = {}
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            lineas = f.readlines()
    except OSError as e:
        mal("no se puede leer: %s" % e)
        return 1

    problemas = []
    for n, linea in enumerate(lineas, 1):
        linea = linea.strip()
        if not linea:
            continue
        partes = linea.split("=")
        if len(partes) != 2:
            que = "sin '='" if len(partes) == 1 else "con %d '='" % (len(partes) - 1)
            problemas.append((n, que, linea[:40]))
            continue
        nombre, valor = partes[0].strip(), partes[1].strip()
        try:
            claves[nombre] = bytes.fromhex(valor)
        except ValueError:
            problemas.append((n, "valor no hexadecimal", nombre))

    if problemas:
        mal("%d linea(s) harian reventar a ldn.load_keys():" % len(problemas))
        for n, que, muestra in problemas[:10]:
            info("     linea %d (%s): %s" % (n, que, muestra))
        if len(problemas) > 10:
            info("     ... y %d mas" % (len(problemas) - 10))
        info("")
        info("load_keys() no admite comentarios ni cabeceras de seccion:")
        info("hace split('=') a pelo sobre toda linea no vacia. Borra esas lineas.")
        fallos += 1
    else:
        ok("las %d linea(s) con contenido parsean sin problemas" % len(claves))

    # --- Claves necesarias --------------------------------------------------
    titulo("Claves necesarias")
    for nombre, largo in sorted(SIEMPRE.items()):
        if nombre not in claves:
            mal("falta %s" % nombre)
            fallos += 1
        elif len(claves[nombre]) != largo:
            mal("%s mide %d bytes, deberia medir %d" % (nombre, len(claves[nombre]), largo))
            fallos += 1
        else:
            ok("%s  (%d bytes)" % (nombre, largo))

    titulo("Master key")
    info("load_keys usa master_key_00 para el protocolo LDN v1 y master_key_12")
    info("para el v3. Con uno basta para arrancar, pero tener los dos evita")
    info("quedarse tirado si la sesion negocia la otra version.")
    presentes = []
    for nombre, largo in sorted(MASTER.items()):
        if nombre not in claves:
            continue
        if len(claves[nombre]) != largo:
            mal("%s mide %d bytes, deberia medir %d" % (nombre, len(claves[nombre]), largo))
            fallos += 1
        else:
            ok("%s  (%d bytes)" % (nombre, largo))
            presentes.append(nombre)

    if not presentes:
        mal("no hay ni master_key_00 ni master_key_12; hace falta al menos uno")
        fallos += 1
    elif len(presentes) == 1:
        falta = [n for n in MASTER if n not in presentes][0]
        proto = "v3" if falta == "master_key_12" else "v1"
        aviso("solo tienes %s; falta %s (protocolo %s)" % (presentes[0], falta, proto))
        avisos += 1

    # --- Veredicto ----------------------------------------------------------
    titulo("Veredicto")
    if fallos:
        print("  %sNO SIRVE: %d problema(s).%s" % (ROJO, fallos, FIN))
        print("  frlg-ldn-trade fallaria al cargarlo.")
        return 1
    if avisos:
        print("  %sSIRVE, con %d aviso(s).%s" % (AMAR, avisos, FIN))
    else:
        print("  %sFICHERO CORRECTO.%s" % (VERDE, FIN))
    print("")
    print("  %sOjo: esto valida el FORMATO, no que los valores sean los buenos." % GRIS)
    print("  Si algun valor fuera incorrecto no habria error al cargar: fallaria")
    print("  el descifrado y la Switch simplemente no responderia.%s" % FIN)
    return 0


if __name__ == "__main__":
    sys.exit(main())
