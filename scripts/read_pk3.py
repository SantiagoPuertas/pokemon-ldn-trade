#!/usr/bin/env python3
"""Inspecciona y valida ficheros .pk3/.ek3 con el parser de frlg-ldn-trade.

    python3 scripts/read_pk3.py pk3/*.pk3

Usa `frlgsim.mon.Mon`, el mismo codigo que leera los ficheros durante el
intercambio: si aqui salen bien, el intercambio no fallara por el fichero.

Codigo de salida 0 si todos son validos, 1 si alguno no lo es.

La lectura vive en `analizar()`, que no imprime nada y devuelve un dict. La
GUI (`scripts/gui.py`) llama a esa misma funcion, asi que consola y ventana
nunca pueden decir cosas distintas del mismo fichero.
"""

import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _c in (os.path.join(RAIZ, "vendor", "frlg-ldn-trade"),
           os.path.join(RAIZ, "..", "frlg-ldn-trade"),
           os.environ.get("FRLG_PATH", "")):
    if _c and os.path.isdir(os.path.join(_c, "frlgsim")):
        sys.path.insert(0, os.path.abspath(_c))
        break
try:
    from frlgsim import basestats, mon as monmod, stats
except ImportError:
    sys.exit("No encuentro 'frlgsim'. Ejecuta antes:  bash scripts/setup_ubuntu.sh")

# Tablas de nombres (opcional: si no estan, se muestran solo los ids)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    import tablas
except Exception:
    tablas = None

VERDE, ROJO, AMAR, GRIS, FIN = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"

NATURALEZAS = """Fuerte Hurana Audaz Firme Picara Osada Docil Placida Agitada
Floja Miedosa Activa Seria Alegre Ingenua Modesta Afable Mansa Timida Alocada
Serena Amable Grosera Cauta Rara""".split()

# Nombres de las estadisticas en el orden interno de Gen III.
ORDEN_STATS = ("PS", "Ataque", "Defensa", "Velocidad", "At. Esp.", "Def. Esp.")


def es_shiny(pid, otid):
    return ((otid & 0xFFFF) ^ (otid >> 16) ^ (pid & 0xFFFF) ^ (pid >> 16)) < 8


def calcular_stats(canon):
    """Estadisticas reales que tendra el Pokemon, con el codigo del juego.

    `build_party_tail` es lo que usa el propio simulador para rellenar la cola
    de 20 bytes del formato de equipo: PS/PS max y las cinco restantes ya con
    el modificador de naturaleza aplicado. Devuelve None si la especie no
    tiene stats base.
    """
    cola = stats.build_party_tail(canon)
    if not cola:
        return None
    valores = [int.from_bytes(cola[8 + 2 * i:10 + 2 * i], "little") for i in range(6)]
    return dict(zip(ORDEN_STATS, valores))          # PS, Ata, Def, Vel, AtEsp, DefEsp


def analizar(ruta):
    """Lee un fichero .pk3/.ek3 y lo analiza. Ver `analizar_bytes`."""
    try:
        crudo = open(ruta, "rb").read()
    except OSError as e:
        return {"ruta": os.path.abspath(ruta), "nombre": os.path.basename(ruta),
                "tamano": None, "ok": False, "datos": None,
                "fallos": ["no se puede leer: %s" % e], "avisos": []}
    info = analizar_bytes(crudo, os.path.basename(ruta))
    info["ruta"] = os.path.abspath(ruta)
    return info


def analizar_bytes(crudo, nombre=""):
    """Analiza los bytes de un .pk3/.ek3 y devuelve un dict con todo lo que se
    sabe de el.

    No imprime nada ni lanza excepciones: los problemas van en las listas
    `fallos` (invalidan el fichero) y `avisos` (raro pero no fatal). Si no se
    pudo llegar a decodificar, `datos` es None y `fallos` explica por que.

    Trabaja sobre bytes y no sobre una ruta para que la GUI pueda previsualizar
    un Pokemon sin llegar a escribirlo en el disco.
    """
    info = {
        "ruta": None,
        "nombre": nombre,
        "tamano": len(crudo),
        "ok": False,
        "fallos": [],
        "avisos": [],
        "datos": None,
    }

    if len(crudo) not in (80, 100):
        info["fallos"].append("debe medir 80 (caja) o 100 (equipo) bytes")
        return info

    try:
        m = monmod.Mon.from_pk3(crudo)
    except Exception as e:
        info["fallos"].append("frlgsim no lo puede cargar: %s" % e)
        return info

    d = m.decode()
    if not d:
        info["fallos"].append("no decodifica")
        return info

    # Los datos utiles viven en la forma descifrada canonica
    canon = monmod.to_decrypted(m.party_bytes())
    sec = canon[32:80]
    growth, evs, misc = sec[0:12], sec[24:36], sec[36:48]
    iv_word = int.from_bytes(misc[4:8], "little")
    ivs = [(iv_word >> (5 * i)) & 0x1F for i in range(6)]
    ev = list(evs[0:6])
    nat = d["pid"] % 25
    movimientos = [{"id": x,
                    "nombre": tablas.nombre_es_movimiento(x) if tablas else str(x),
                    "nombre_en": tablas.nombre_movimiento(x) if tablas else str(x)}
                   for x in d["moves"] if x]
    objeto_id = d["heldItem"]

    datos = {
        "especie": d["species"],
        "nombre_especie": d["species_name"],
        "mote": d["nickname"],
        "ot": d["otName"],
        "otid": d["otid"],
        "otid_visible": d["otid"] & 0xFFFF,
        "pid": d["pid"],
        "nivel": d["level"],
        "naturaleza": nat,
        "naturaleza_nombre": NATURALEZAS[nat],
        "shiny": es_shiny(d["pid"], d["otid"]),
        "ivs": ivs,
        "evs": ev,
        "suma_evs": sum(ev),
        "movimientos": movimientos,
        "objeto": objeto_id,
        "objeto_nombre": (tablas.nombre_es_objeto(objeto_id) if tablas and objeto_id else
                          ("ninguno" if not objeto_id else str(objeto_id))),
        "objeto_nombre_en": (tablas.nombre_objeto(objeto_id) if tablas and objeto_id
                             else "none"),
        "amistad": growth[9],
        "exp": d["exp"],
        "checksum_ok": d["checksum_ok"],
        "checksum_calc": d["calc"],
        "checksum_guardado": d["stored"],
        # bit 31 de la palabra de cintas: en FRLG decide si un Mew/Deoxys se
        # puede intercambiar y si obedece.
        "fateful": bool(int.from_bytes(misc[8:12], "little") >> 31 & 1),
        "necesita_fateful": d["species"] in (151, 410),
        "stats": None,
        "descripcion": m.describe(),
    }
    info["datos"] = datos

    if not d["checksum_ok"]:
        info["fallos"].append("checksum: calculado %04x, guardado %04x" % (d["calc"], d["stored"]))

    if d["species"] not in basestats.BASE_STATS:
        info["fallos"].append("especie sin stats base: el juego no la aceptara")
    else:
        datos["stats"] = calcular_stats(canon)
        # Coherencia entre la experiencia guardada y el nivel de la cola
        esperado = stats.level_from_exp(d["species"], d["exp"])
        datos["nivel_por_exp"] = esperado
        if d["level"] is not None and d["level"] != esperado:
            info["avisos"].append("el nivel %s no cuadra con la experiencia (seria %d)"
                                  % (d["level"], esperado))

    if sum(ev) > 510:
        info["avisos"].append("los EVs suman %d, mas del maximo legal de 510" % sum(ev))
    if any(v > 31 for v in ivs):
        info["avisos"].append("hay IVs por encima de 31")
    if datos["necesita_fateful"] and not datos["fateful"]:
        info["avisos"].append("Mew/Deoxys sin modernFatefulEncounter: el juego lo "
                              "RECHAZARA al intercambiar")

    info["ok"] = not info["fallos"]
    return info


def informar(ruta):
    """Imprime el informe de consola de un fichero. Devuelve True si es valido."""
    info = analizar(ruta)

    if info["tamano"] is None:                      # ni siquiera se pudo abrir
        print("  %s[FALLA]%s %s: %s" % (ROJO, FIN, ruta, info["fallos"][0].split(": ", 1)[-1]))
        return False

    print("\n%s" % info["nombre"])
    print("  %stamano: %d bytes%s" % (GRIS, info["tamano"], FIN))
    d = info["datos"]
    if d is None:
        print("  %s[FALLA]%s %s" % (ROJO, FIN, info["fallos"][0]))
        return False

    print("  especie      #%d (%s)" % (d["especie"], d["nombre_especie"]))
    print("  mote         %r" % d["mote"])
    print("  OT           %r   ID %d" % (d["ot"], d["otid_visible"]))
    print("  nivel        %s" % d["nivel"])
    print("  naturaleza   %s" % d["naturaleza_nombre"])
    print("  shiny        %s" % ("SI" if d["shiny"] else "no"))
    print("  IVs          %s" % "/".join(str(v) for v in d["ivs"]))
    print("  EVs          %s  (suma %d)" % ("/".join(str(v) for v in d["evs"]), d["suma_evs"]))
    print("  movimientos  %s" % ", ".join("%s (%d)" % (mv["nombre"], mv["id"])
                                          for mv in d["movimientos"]))
    print("  objeto       %s" % ("%d · %s" % (d["objeto"], d["objeto_nombre"])
                                 if d["objeto"] else "0 (ninguno)"))
    if d["necesita_fateful"]:     # Mew / Deoxys: el flag decide si es intercambiable
        etiqueta = "%s[ OK  ]%s" % (VERDE, FIN) if d["fateful"] else "%s[FALLA]%s" % (ROJO, FIN)
        print("  fateful      %s (%s)" % ("SI" if d["fateful"] else "no",
              "intercambiable" if d["fateful"] else "el juego lo RECHAZARA al intercambiar"))
        print("  %s Mew/Deoxys necesitan modernFatefulEncounter para intercambiarse" % etiqueta)
    print("  experiencia  %d" % d["exp"])

    if d["checksum_ok"]:
        print("  %s[ OK  ]%s checksum" % (VERDE, FIN))
    else:
        print("  %s[FALLA]%s checksum: calculado %04x, guardado %04x"
              % (ROJO, FIN, d["checksum_calc"], d["checksum_guardado"]))
    for f in info["fallos"]:
        if not f.startswith("checksum"):
            print("  %s[FALLA]%s %s" % (ROJO, FIN, f))
    for a in info["avisos"]:
        if a.startswith("Mew/Deoxys"):              # ya se ha dicho arriba, con detalle
            continue
        print("  %s[ ??  ]%s %s" % (AMAR, FIN, a))

    return info["ok"]


def main():
    rutas = sys.argv[1:]
    if not rutas:
        por_defecto = os.path.join(RAIZ, "pk3")
        rutas = sorted(os.path.join(por_defecto, f) for f in os.listdir(por_defecto)
                       if f.endswith((".pk3", ".ek3"))) if os.path.isdir(por_defecto) else []
    if not rutas:
        sys.exit("uso: python3 scripts/read_pk3.py FICHERO.pk3 [...]")

    todos_ok = True
    for r in rutas:
        todos_ok &= informar(r)
    print("\n%s" % ("Todos los ficheros son validos." if todos_ok
                    else "%sHay ficheros invalidos.%s" % (ROJO, FIN)))
    return 0 if todos_ok else 1


if __name__ == "__main__":
    sys.exit(main())
