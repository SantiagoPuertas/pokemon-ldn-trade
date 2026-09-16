#!/usr/bin/env python3
"""Interfaz grafica del proyecto: crear Pokemon, gestionar la caja, intercambiar.

    python3 scripts/gui.py                      # y abre http://127.0.0.1:8777
    python3 scripts/gui.py --puerto 9000 --sin-navegador

Es un servidor HTTP de la biblioteca estandar mas una pagina en `gui_web/`.
**No instala nada**: en este Ubuntu live no hay tkinter ni ganas de gastar
persistencia en paquetes, y el navegador ya esta ahi. Ademas sigue funcionando
por localhost aunque se pare NetworkManager para el intercambio, que es
justo el momento en el que hace falta.

Escucha SOLO en 127.0.0.1. Importa: hay botones que ejecutan cosas con sudo
(soltar la radio, lanzar el intercambio, apagar el equipo).

No reimplementa nada de lo que ya funciona:

    crear      -> make_pk3.construir_pk3 / make_pk3.generar
    leer       -> read_pk3.analizar (el mismo informe que la consola)
    interc.    -> vendor/frlg-ldn-trade/frlgtrade.py, con los argumentos del
                  runbook (docs/04_runbook_ubuntu.md, seccion 7)
"""

import argparse
import http.server
import json
import mimetypes
import os
import random
import re
import shlex
import subprocess
import sys
import threading
import time
import webbrowser

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_SCRIPTS = os.path.join(RAIZ, "scripts")
DIR_WEB = os.path.join(DIR_SCRIPTS, "gui_web")
DIR_PK3 = os.path.join(RAIZ, "pk3")
DIR_SALIDAS = os.path.join(RAIZ, "salidas")
VENDOR = os.path.join(RAIZ, "vendor", "frlg-ldn-trade")
VENV_PY = os.path.join(VENDOR, "venv", "bin", "python")

sys.path.insert(0, DIR_SCRIPTS)
import make_pk3                      # noqa: E402  (necesita el sys.path de arriba)
import read_pk3                      # noqa: E402
import tablas                        # noqa: E402


# ---------------------------------------------------------------------------
# Utilidades de sistema
# ---------------------------------------------------------------------------

def usuario_real():
    """(uid, gid) de quien lanzo esto, aunque se haya lanzado con sudo.

    Los ficheros que escriba el intercambio los crea root; hay que devolverlos
    a su dueno o el resto de herramientas no podran tocarlos.
    """
    return (int(os.environ.get("SUDO_UID", os.getuid())),
            int(os.environ.get("SUDO_GID", os.getgid())))


def home_real():
    """El HOME de verdad. Bajo sudo, `~` es /root y ahi no esta el prod.keys."""
    if os.environ.get("SUDO_USER"):
        return os.path.expanduser("~" + os.environ["SUDO_USER"])
    return os.path.expanduser("~")


CLAVES_POR_DEFECTO = os.path.join(home_real(), ".switch", "prod.keys")


def con_sudo(cmd):
    """Antepone `sudo -n` si no somos root. -n = nunca preguntar contrasena:
    si el sudo de esta maquina la pidiera, preferimos un fallo claro a que la
    GUI se quede colgada esperando una contrasena que nadie va a escribir."""
    return cmd if os.geteuid() == 0 else ["sudo", "-n"] + cmd


def ejecutar(cmd, timeout=20):
    """Lanza un comando y devuelve (codigo, salida). Nunca lanza excepcion."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, "no existe el comando %s" % cmd[0]
    except subprocess.TimeoutExpired:
        return 124, "el comando tardo demasiado"
    except Exception as e:                                    # noqa: BLE001
        return 1, str(e)


def ruta_segura(ruta, base=RAIZ):
    """Convierte una ruta que viene del navegador en absoluta y comprueba que
    cae dentro del repo. El servidor es local, pero un fallo aqui significa
    escribir o borrar donde no toca."""
    if not ruta:
        raise ValueError("falta la ruta")
    completa = os.path.abspath(os.path.join(base, os.path.expanduser(ruta)))
    if completa != base and not completa.startswith(base + os.sep):
        raise ValueError("ruta fuera del proyecto: %s" % ruta)
    return completa


# Identificadores de red que no interesa que acaben en el repo: la MAC del PC,
# la de la Switch y el SSID de la sesion LDN. Los registros SI se versionan (son
# la unica prueba de lo que paso en cada intento), asi que se censura al
# escribirlos y no despues: acordarse a mano ya costo una reescritura del
# historial el 2026-09-02. Ver "Que no se sube" en el README.
CENSURAS = [
    (re.compile(r"(\bus=[0-9.]+/)[0-9a-fA-F]{12}\b"), r"\1MAC-PC-CENSURADA"),
    (re.compile(r"(\bhost=[0-9.]+/)[0-9a-fA-F]{12}\b"), r"\1MAC-SWITCH-CENSURADA"),
    (re.compile(r"(\bssid=)[0-9a-fA-F]{32}\b"), r"\1SSID-CENSURADO"),
    (re.compile(r"\b(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b"), "MAC-CENSURADA"),
]
CENSURAR = True                       # se apaga con --sin-censura


def censurar(linea):
    """Tapa las MAC y el SSID de una linea del registro.

    Deja el resto intacto —las IP 169.254.x, los tiempos, el estado de Pia—,
    que es lo que de verdad sirve para depurar.
    """
    if not CENSURAR:
        return linea
    for patron, reemplazo in CENSURAS:
        linea = patron.sub(reemplazo, linea)
    return linea


def devolver_al_usuario(ruta):
    """chown del fichero al usuario real (lo habra creado root)."""
    uid, gid = usuario_real()
    try:
        if os.stat(ruta).st_uid != uid:
            ejecutar(con_sudo(["chown", "%d:%d" % (uid, gid), ruta]))
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Estado: catalogo, caja, sistema
# ---------------------------------------------------------------------------

def catalogo():
    """Todo lo que la pagina necesita para rellenar sus desplegables.

    Objetos y movimientos van ya agrupados —por categoria y por tipo— porque
    son 310 y 354: en una lista plana no se encuentra nada.
    """
    def grupos(pares):
        return [{"grupo": titulo, "opciones": opciones} for titulo, opciones in pares]

    # Naturalezas: nombre ES + que estadistica sube y cual baja, que es lo
    # unico que se mira al elegirla.
    orden = ["Ataque", "Defensa", "Velocidad", "At. Esp.", "Def. Esp."]
    naturalezas = []
    for i, en in enumerate(make_pk3.NATURALEZAS):
        fila = read_pk3.stats.NATURE_STAT_TABLE[i]
        sube = next((orden[j] for j, v in enumerate(fila) if v == 1), None)
        baja = next((orden[j] for j, v in enumerate(fila) if v == -1), None)
        naturalezas.append({
            "id": i,
            "es": read_pk3.NATURALEZAS[i],
            "en": en,
            "efecto": "+%s / −%s" % (sube, baja) if sube else "sin efecto",
        })

    return {
        "especies": [{"id": i + 1, "nombre": n} for i, n in enumerate(make_pk3.KANTO)],
        "naturalezas": naturalezas,
        "movimientos": grupos(tablas.movimientos_por_tipo()),
        "objetos": grupos(tablas.objetos_por_categoria()),
        "stats": list(read_pk3.ORDEN_STATS),
        "claves_por_defecto": CLAVES_POR_DEFECTO,
    }


def listar_pokemon():
    """Todos los .pk3/.ek3 del proyecto, ya analizados."""
    fichas = []
    for carpeta, _dirs, ficheros in os.walk(DIR_PK3):
        for f in sorted(ficheros):
            if not f.endswith((".pk3", ".ek3")):
                continue
            completa = os.path.join(carpeta, f)
            info = read_pk3.analizar(completa)
            info["relativa"] = os.path.relpath(completa, RAIZ)
            info["carpeta"] = os.path.relpath(carpeta, DIR_PK3).replace(".", "")
            try:
                info["modificado"] = os.path.getmtime(completa)
            except OSError:
                info["modificado"] = 0
            fichas.append(info)
    fichas.sort(key=lambda x: -x["modificado"])
    return {"pokemon": fichas}


def dispositivos_wifi():
    """Interfaces Wi-Fi con su estado en NetworkManager."""
    rc, salida = ejecutar(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "device"])
    devs = []
    if rc == 0:
        for linea in salida.splitlines():
            partes = linea.split(":")
            if len(partes) >= 3 and partes[1] == "wifi":
                devs.append({"nombre": partes[0], "estado": partes[2],
                             "libre": partes[2].startswith("unmanaged")
                                      or "no gestionado" in partes[2]})
    return devs


def estado_sistema():
    """Lo que hay que mirar antes de intentar un intercambio."""
    rc_sudo, _ = ejecutar(["sudo", "-n", "true"], timeout=5)
    claves = CLAVES_POR_DEFECTO
    n_claves = 0
    if os.path.isfile(claves):
        try:
            with open(claves) as f:
                n_claves = sum(1 for l in f if "=" in l)
        except OSError:
            pass
    servicios = {}
    for s in ("NetworkManager", "wpa_supplicant", "iwd"):
        rc, out = ejecutar(["systemctl", "is-active", s], timeout=5)
        servicios[s] = out or "unknown"
    phys = sorted(os.listdir("/sys/class/ieee80211")) \
        if os.path.isdir("/sys/class/ieee80211") else []

    return {
        "root": os.geteuid() == 0,
        "sudo_sin_contrasena": rc_sudo == 0,
        "claves": {"ruta": claves, "existe": os.path.isfile(claves), "n": n_claves},
        "frlgsim": os.path.isdir(os.path.join(VENDOR, "frlgsim")),
        "venv": os.path.isfile(VENV_PY),
        "servicios": servicios,
        "wifi": dispositivos_wifi(),
        "phys": phys,
        "usuario": os.environ.get("SUDO_USER") or os.environ.get("USER", "?"),
        "raiz": RAIZ,
    }


# ---------------------------------------------------------------------------
# Crear Pokemon
# ---------------------------------------------------------------------------

def _entero(p, clave, minimo, maximo, defecto):
    v = p.get(clave, defecto)
    if v in ("", None):
        v = defecto
    try:
        v = int(v)
    except (TypeError, ValueError):
        raise ValueError("%s: '%s' no es un numero" % (clave, v))
    if not minimo <= v <= maximo:
        raise ValueError("%s: %d fuera de rango %d..%d" % (clave, v, minimo, maximo))
    return v


def _seis(p, clave, maximo):
    valores = p.get(clave) or [0] * 6
    if len(valores) != 6:
        raise ValueError("%s: hacen falta 6 valores" % clave)
    salida = []
    for i, v in enumerate(valores):
        try:
            v = int(v)
        except (TypeError, ValueError):
            raise ValueError("%s: '%s' no es un numero" % (clave, v))
        if not 0 <= v <= maximo:
            raise ValueError("%s[%d]: %d fuera de rango 0..%d" % (clave, i, v, maximo))
        salida.append(v)
    return salida


def parametros(p):
    """Traduce lo que manda el formulario a los argumentos de construir_pk3.

    Las conversiones de nombre (especie, naturaleza, objeto, movimiento) las
    hacen las mismas funciones que usa la linea de ordenes, asi que la GUI
    acepta exactamente lo mismo: id, nombre EN o alias ES.
    """
    def traducir(fn, valor, que):
        try:
            return fn(valor)
        except Exception as e:                                # noqa: BLE001
            raise ValueError("%s: %s" % (que, e))

    especie = traducir(make_pk3.especie_id, str(p.get("especie", "")).strip(), "especie")
    naturaleza = traducir(make_pk3.naturaleza_id,
                          str(p.get("naturaleza", "hardy")).strip(), "naturaleza")
    objeto = 0
    if str(p.get("objeto", "")).strip():
        objeto = traducir(make_pk3.objeto_id, str(p["objeto"]).strip(), "objeto")

    movimientos = []
    for i, mv in enumerate(p.get("movimientos") or []):
        mv = str(mv).strip()
        if mv:
            movimientos.append(traducir(tablas.resolver_movimiento, mv, "movimiento %d" % (i + 1)))
    if not movimientos:
        movimientos = [33]                                   # placaje: sin movimientos no es legal
    movimientos = (movimientos + [0, 0, 0, 0])[:4]

    nivel = _entero(p, "nivel", 1, 100, 5)
    evs = _seis(p, "evs", 255)
    if sum(evs) > 510:
        raise ValueError("los EVs suman %d y el maximo es 510" % sum(evs))

    semilla = p.get("semilla")
    semilla = int(semilla) if str(semilla).strip() not in ("", "None") else random.randrange(1 << 32)
    rng = random.Random(semilla)

    otid = str(p.get("otid", "")).strip()
    otid = int(otid, 0) if otid else rng.randrange(1 << 32)

    fateful = p.get("fateful", "auto")
    fateful = {"auto": None, "si": True, "no": False}.get(fateful, None)

    mote = (p.get("mote") or "").strip()
    if not mote:
        mote = make_pk3.KANTO[especie - 1] if 1 <= especie <= len(make_pk3.KANTO) else "MON"

    return semilla, {
        "species": especie,
        "level": nivel,
        "nature": naturaleza,
        "shiny": bool(p.get("shiny")),
        "ivs": _seis(p, "ivs", 31),
        "evs": evs,
        "moves": movimientos,
        "item": objeto,
        "nickname": mote[:10],
        "ot_name": (p.get("ot") or "EMU").strip()[:7] or "EMU",
        "otid": otid,
        "ability_slot": _entero(p, "habilidad", 0, 1, 0),
        "friendship": _entero(p, "amistad", 0, 255, 70),
        "rng": rng,
        "fateful": fateful,
    }


def api_vista_previa(p):
    """Construye el Pokemon en memoria y lo analiza, sin tocar el disco.

    Con la misma semilla saldra byte a byte igual que al guardarlo, asi que
    lo que se ve aqui es exactamente lo que se va a crear."""
    semilla, kw = parametros(p)
    pk3 = make_pk3.construir_pk3(**kw)
    info = read_pk3.analizar_bytes(pk3, "(vista previa)")
    info["semilla"] = semilla
    return info


def api_crear(p):
    """Genera y guarda el .pk3 en pk3/."""
    semilla, kw = parametros(p)

    nombre = (p.get("fichero") or "").strip() or ("%s.pk3" % kw["nickname"].lower())
    if not nombre.endswith((".pk3", ".ek3")):
        nombre += ".pk3"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", nombre):
        raise ValueError("nombre de fichero no valido: usa letras, numeros, . _ -")
    destino = ruta_segura(os.path.join("pk3", nombre))
    if os.path.exists(destino) and not p.get("sobrescribir"):
        raise ValueError("ya existe %s. Marca 'sobrescribir' o cambia el nombre."
                         % os.path.relpath(destino, RAIZ))

    make_pk3.generar(destino, **kw)          # valida con frlgsim y escribe
    devolver_al_usuario(destino)
    info = read_pk3.analizar(destino)
    info["relativa"] = os.path.relpath(destino, RAIZ)
    info["semilla"] = semilla
    return info


def api_borrar(p):
    """Borra un .pk3. Solo dentro de pk3/ y nunca los ejemplos versionados."""
    destino = ruta_segura(p.get("ruta", ""))
    if not destino.startswith(DIR_PK3 + os.sep):
        raise ValueError("solo se pueden borrar ficheros de pk3/")
    if os.path.join(DIR_PK3, "ejemplos") in destino:
        raise ValueError("los ejemplos estan versionados en el repo; borralos con git si quieres")
    if not destino.endswith((".pk3", ".ek3")):
        raise ValueError("solo ficheros .pk3/.ek3")
    os.remove(destino)
    return {"borrado": os.path.relpath(destino, RAIZ)}


# ---------------------------------------------------------------------------
# Radio y sistema  ("el poder": lo que enciende, suelta y apaga la maquina)
# ---------------------------------------------------------------------------

def api_radio(p):
    """Suelta o devuelve la tarjeta Wi-Fi. Seccion 7.3 del runbook.

    LDN necesita la radio para el solo: mientras NetworkManager la gestione,
    el escaneo no vera a la Switch.
    """
    accion = p.get("accion")
    dev = p.get("dispositivo", "")
    if dev and not re.fullmatch(r"[A-Za-z0-9_.-]+", dev):
        raise ValueError("nombre de interfaz no valido")

    if accion == "liberar_wifi":                      # opcion A: conservas Internet por cable
        rc, salida = ejecutar(con_sudo(["nmcli", "device", "set", dev, "managed", "no"]))
    elif accion == "restaurar_wifi":
        rc, salida = ejecutar(con_sudo(["nmcli", "device", "set", dev, "managed", "yes"]))
    elif accion == "parar_nm":                        # opcion B: a lo bruto
        rc, salida = ejecutar(con_sudo(["systemctl", "stop", "NetworkManager"]), timeout=40)
    elif accion == "arrancar_nm":
        rc, salida = ejecutar(con_sudo(["systemctl", "start", "NetworkManager"]), timeout=40)
    else:
        raise ValueError("accion desconocida: %s" % accion)

    return {"rc": rc, "salida": salida, "estado": estado_sistema()}


def api_sistema(p):
    """sync / apagar / reiniciar, via scripts/apagar.sh.

    El apagado normal de un Ubuntu live se cuelga esperando a que saques el
    pendrive; apagar.sh se salta esa fase y sincroniza antes para no perder la
    persistencia. Por eso aqui no se llama a `poweroff` a secas.
    """
    accion = p.get("accion")
    if accion == "sync":
        rc, salida = ejecutar(["sync"], timeout=60)
        return {"rc": rc, "salida": salida or "discos sincronizados"}
    if accion in ("apagar", "reiniciar"):
        cmd = ["bash", os.path.join(DIR_SCRIPTS, "apagar.sh")]
        if accion == "reiniciar":
            cmd.append("--reiniciar")
        # En segundo plano: la maquina se va a ir y esta peticion no llegaria a
        # contestar nunca si esperasemos al final del script.
        subprocess.Popen(cmd, cwd=RAIZ, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"rc": 0, "salida": "lanzado apagar.sh (%s)" % accion}
    raise ValueError("accion desconocida: %s" % accion)


# ---------------------------------------------------------------------------
# Intercambio
# ---------------------------------------------------------------------------

class Intercambio:
    """Un unico frlgtrade.py en marcha, con su registro en memoria.

    El registro se guarda tambien en salidas/, con la fecha en el nombre: si
    algo falla, la salida completa con --verbose es lo unico que sirve para
    saber en que capa fue (blueprint, seccion 20), y machacar la del intento
    anterior seria justo perder la comparacion.
    """

    def __init__(self):
        self.lock = threading.Lock()
        self.proc = None
        self.lineas = []
        self.comando = []
        self.arrancado = None
        self.terminado = None
        self.rc = None
        self.fichero_log = None
        self.fichero_salida = None
        self.recibido = None

    # -- consulta ---------------------------------------------------------
    def activo(self):
        return self.proc is not None and self.proc.poll() is None

    def instantanea(self, desde=0):
        with self.lock:
            return {
                "activo": self.activo(),
                "rc": self.rc,
                "comando": " ".join(shlex.quote(c) for c in self.comando),
                "arrancado": self.arrancado,
                "terminado": self.terminado,
                "log": self.fichero_log and os.path.relpath(self.fichero_log, RAIZ),
                "salida": self.fichero_salida and os.path.relpath(self.fichero_salida, RAIZ),
                "recibido": self.recibido,
                "desde": desde,
                "total": len(self.lineas),
                "lineas": self.lineas[desde:desde + 2000],
            }

    # -- control ----------------------------------------------------------
    def lanzar(self, p):
        if self.activo():
            raise ValueError("ya hay un intercambio en marcha")

        relleno = ruta_segura(p.get("relleno", ""))
        enviar = ruta_segura(p.get("enviar", ""))
        for r in (relleno, enviar):
            info = read_pk3.analizar(r)
            if not info["ok"]:
                raise ValueError("%s no es valido: %s" %
                                 (os.path.basename(r), "; ".join(info["fallos"])))
        # Marca de tiempo compartida por el registro y el Pokemon recibido: asi
        # se sabe de un vistazo cual salio de cual.
        marca = time.strftime("%Y%m%d-%H%M%S")
        pedida = (p.get("salida") or "").strip()
        if pedida:
            salida = ruta_segura(pedida)
        else:
            # Con un nombre fijo cada intercambio machacaba al anterior: el
            # 2026-09-02 el segundo se llevo por delante al Rattata del primero.
            salida = os.path.join(DIR_PK3, "recibido", "recibido-%s.pk3" % marca)
        os.makedirs(os.path.dirname(salida), exist_ok=True)
        claves = os.path.expanduser(p.get("claves") or CLAVES_POR_DEFECTO)
        if not os.path.isfile(claves):
            raise ValueError("no encuentro el prod.keys en %s" % claves)
        if not os.path.isfile(VENV_PY):
            raise ValueError("falta el venv del vendor. Ejecuta antes: bash scripts/setup_ubuntu.sh")
        phy = p.get("phy") or "phy0"
        if not re.fullmatch(r"phy[0-9]+", phy):
            raise ValueError("phy no valido: %s" % phy)
        version = p.get("version") or "firered"
        if version not in ("firered", "leafgreen"):
            raise ValueError("version no valida")
        ot = (p.get("ot") or "EMU").strip()[:7] or "EMU"
        trades = int(p.get("trades") or 1)
        if not 1 <= trades <= 6:
            raise ValueError("trades fuera de rango 1..6")

        # -u: sin buffer. Con una tuberia de por medio, Python retendria la
        # salida en bloques y el registro en pantalla llegaria a trompicones,
        # justo cuando lo que se quiere es ver en vivo si la Switch responde.
        # --keys con ruta completa: bajo sudo, ~ es /root (runbook, seccion 9).
        cmd = con_sudo([VENV_PY, "-u", "frlgtrade.py", "--live", "--verbose",
                        "--version", version, "--ot", ot, "--phy", phy,
                        "--trades", str(trades), "--keys", claves,
                        "-o", salida, relleno, enviar])

        os.makedirs(DIR_SALIDAS, exist_ok=True)
        fichero_log = os.path.join(DIR_SALIDAS, "intercambio-%s.txt" % marca)

        with self.lock:
            self.lineas = []
            self.comando = cmd
            self.rc = None
            self.recibido = None
            self.arrancado = time.time()
            self.terminado = None
            self.fichero_log = fichero_log
            self.fichero_salida = salida

        self.proc = subprocess.Popen(
            cmd, cwd=VENDOR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", start_new_session=True)
        threading.Thread(target=self._leer, daemon=True).start()
        return self.instantanea()

    def _leer(self):
        """Vuelca la salida del proceso al registro en memoria y al fichero."""
        with open(self.fichero_log, "w") as f:
            for linea in self.proc.stdout:
                linea = censurar(linea.rstrip("\n"))
                f.write(linea + "\n")
                f.flush()
                with self.lock:
                    self.lineas.append(linea)
        rc = self.proc.wait()
        recibido = None
        if os.path.isfile(self.fichero_salida):
            devolver_al_usuario(self.fichero_salida)
            info = read_pk3.analizar(self.fichero_salida)
            info["relativa"] = os.path.relpath(self.fichero_salida, RAIZ)
            recibido = info
        devolver_al_usuario(self.fichero_log)
        with self.lock:
            self.rc = rc
            self.terminado = time.time()
            self.recibido = recibido

    def parar(self):
        if not self.activo():
            return {"salida": "no habia nada en marcha"}
        # El proceso es root (via sudo) y esta en su propio grupo, asi que se
        # le manda la senal al grupo entero: matar solo al sudo dejaria vivo
        # al python de dentro, con la radio cogida.
        pgid = os.getpgid(self.proc.pid)
        ejecutar(con_sudo(["kill", "-INT", "--", "-%d" % pgid]))
        return {"salida": "senal enviada"}


INTERCAMBIO = Intercambio()


def api_intercambio_lanzar(p):
    return INTERCAMBIO.lanzar(p)


def api_intercambio_parar(p):
    return INTERCAMBIO.parar()


# ---------------------------------------------------------------------------
# Servidor HTTP
# ---------------------------------------------------------------------------

RUTAS_GET = {
    "/api/catalogo": lambda p: catalogo(),
    "/api/estado": lambda p: estado_sistema(),
    "/api/pokemon": lambda p: listar_pokemon(),
    "/api/intercambio": lambda p: INTERCAMBIO.instantanea(int(p.get("desde", ["0"])[0])),
}

RUTAS_POST = {
    "/api/vista_previa": api_vista_previa,
    "/api/crear": api_crear,
    "/api/borrar": api_borrar,
    "/api/radio": api_radio,
    "/api/sistema": api_sistema,
    "/api/intercambio/lanzar": api_intercambio_lanzar,
    "/api/intercambio/parar": api_intercambio_parar,
}


class Manejador(http.server.BaseHTTPRequestHandler):
    server_version = "ComunicacionPokemonGUI"
    protocol_version = "HTTP/1.1"

    # -- ayudas -----------------------------------------------------------
    def _responder(self, codigo, cuerpo, tipo="application/json; charset=utf-8"):
        if isinstance(cuerpo, str):
            cuerpo = cuerpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(cuerpo)
        except BrokenPipeError:
            pass

    def _json(self, obj, codigo=200):
        self._responder(codigo, json.dumps(obj, ensure_ascii=False))

    def _api(self, fn, argumento):
        try:
            self._json(fn(argumento))
        except ValueError as e:
            self._json({"error": str(e)}, 400)
        except Exception as e:                                # noqa: BLE001
            self._json({"error": "%s: %s" % (type(e).__name__, e)}, 500)

    def _estatico(self, ruta):
        nombre = "index.html" if ruta == "/" else ruta.lstrip("/")
        completa = os.path.abspath(os.path.join(DIR_WEB, nombre))
        if not completa.startswith(DIR_WEB) or not os.path.isfile(completa):
            self._responder(404, "no encontrado", "text/plain; charset=utf-8")
            return
        tipo = mimetypes.guess_type(completa)[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo.endswith("javascript"):
            tipo += "; charset=utf-8"
        with open(completa, "rb") as f:
            self._responder(200, f.read(), tipo)

    # -- verbos -----------------------------------------------------------
    def do_GET(self):
        from urllib.parse import urlparse, parse_qs
        u = urlparse(self.path)
        if u.path in RUTAS_GET:
            self._api(RUTAS_GET[u.path], parse_qs(u.query))
        else:
            self._estatico(u.path)

    def do_POST(self):
        if self.path not in RUTAS_POST:
            self._json({"error": "ruta desconocida"}, 404)
            return
        largo = int(self.headers.get("Content-Length") or 0)
        crudo = self.rfile.read(largo) if largo else b"{}"
        try:
            cuerpo = json.loads(crudo or b"{}")
        except json.JSONDecodeError:
            self._json({"error": "JSON invalido"}, 400)
            return
        self._api(RUTAS_POST[self.path], cuerpo)

    def log_message(self, formato, *args):
        if VERBOSO:
            sys.stderr.write("  %s\n" % (formato % args))


VERBOSO = False


def main():
    global VERBOSO, CENSURAR
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--puerto", type=int, default=8777)
    ap.add_argument("--sin-navegador", action="store_true")
    ap.add_argument("--verboso", action="store_true", help="registra cada peticion HTTP")
    ap.add_argument("--sin-censura", action="store_true",
                    help="deja las MAC y el SSID en el registro del intercambio "
                         "(por defecto se tapan; no subas ese registro al repo)")
    args = ap.parse_args()
    VERBOSO = args.verboso
    CENSURAR = not args.sin_censura

    url = "http://127.0.0.1:%d/" % args.puerto
    try:
        servidor = http.server.ThreadingHTTPServer(("127.0.0.1", args.puerto), Manejador)
    except OSError as e:
        sys.exit("No puedo escuchar en el puerto %d (%s).\n"
                 "Puede que ya haya una GUI abierta. Prueba con --puerto 8778."
                 % (args.puerto, e))
    servidor.daemon_threads = True

    print("GUI de pokemon-ldn-trade en %s" % url)
    print("  proyecto : %s" % RAIZ)
    print("  claves   : %s%s" % (CLAVES_POR_DEFECTO,
                                 "" if os.path.isfile(CLAVES_POR_DEFECTO) else "  (NO esta)"))
    print("  sudo     : %s" % ("somos root" if os.geteuid() == 0 else
                               "por sudo -n" ))
    print("  registro : %s" % ("MAC y SSID censurados" if CENSURAR else
                               "SIN CENSURAR (no subas el registro al repo)"))
    print("\nCtrl-C para salir.\n")

    if not args.sin_navegador:
        threading.Thread(target=lambda: (time.sleep(0.5), webbrowser.open(url)),
                         daemon=True).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nCerrando.")
        if INTERCAMBIO.activo():
            INTERCAMBIO.parar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
