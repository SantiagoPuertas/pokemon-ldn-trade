#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# setup_ubuntu.sh - Prepara frlg-ldn-trade en Ubuntu
#
#     bash scripts/setup_ubuntu.sh
#
# Instala dependencias del sistema, clona frlg-ldn-trade en vendor/ y crea
# su entorno virtual de Python. NO ejecuta ningun intercambio: solo deja
# todo listo.
#
# Ejecutar DESPUES de que check_wifi.sh no de bloqueos.
# ---------------------------------------------------------------------------
set -euo pipefail

RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VENDOR="$RAIZ/vendor"
TRADE="$VENDOR/frlg-ldn-trade"
UPSTREAM="https://github.com/tornadus/frlg-ldn-trade.git"

BOLD=$'\e[1m'; RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; RST=$'\e[0m'
paso()  { printf '\n%s==> %s%s\n' "$BOLD" "$1" "$RST"; }
ok()    { printf '  %s[ OK ]%s %s\n' "$GRN" "$RST" "$1"; }
aviso() { printf '  %s[ !! ]%s %s\n' "$YEL" "$RST" "$1"; }
morir() { printf '  %s[FALLA]%s %s\n' "$RED" "$RST" "$1"; exit 1; }

[ "$(uname -s)" = "Linux" ] || morir "Este script es para Linux. En Windows no sirve."

# --- 1. Dependencias del sistema -------------------------------------------
paso "Dependencias del sistema"
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip iw pciutils
ok "paquetes instalados"

PYV=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
if [ "$(printf '%s\n3.12\n' "$PYV" | sort -V | head -1)" != "3.12" ]; then
    morir "Python $PYV - frlg-ldn-trade necesita 3.12+. Usa una Ubuntu mas nueva."
fi
ok "Python $PYV"

# --- 2. Clonar frlg-ldn-trade ----------------------------------------------
paso "frlg-ldn-trade"
mkdir -p "$VENDOR"
if [ -d "$TRADE/.git" ]; then
    git -C "$TRADE" pull --ff-only
    ok "actualizado en $TRADE"
else
    git clone "$UPSTREAM" "$TRADE"
    ok "clonado en $TRADE"
fi

# --- 3. Entorno virtual -----------------------------------------------------
paso "Entorno virtual"
if [ ! -d "$TRADE/venv" ]; then
    python3 -m venv "$TRADE/venv"
fi
"$TRADE/venv/bin/pip" install --upgrade pip
if [ -f "$TRADE/requirements.txt" ]; then
    # Comprobado el 2026-09-01 para Python 3.14: no hace falta compilador.
    #   pycryptodome 3.23.0 -> wheel cp37-abi3 (ABI estable, vale para 3.7+)
    #   zstandard 0.25.0    -> wheel cp314 nativa
    #   trio, ldn           -> Python puro
    # Si en el futuro alguna version dejara de traer wheel, pip intentaria
    # compilar y fallaria por falta de cabeceras. De ahi el mensaje de abajo.
    if ! "$TRADE/venv/bin/pip" install -r "$TRADE/requirements.txt"; then
        mal "fallo la instalacion de dependencias"
        printf '\n  Si el error habla de gcc, cc1 o Python.h, pip esta intentando\n'
        printf '  compilar desde fuente. Instala las herramientas y reintenta:\n\n'
        printf '      sudo apt install -y build-essential python3-dev\n\n'
        exit 1
    fi
    ok "dependencias instaladas"
else
    aviso "no hay requirements.txt; revisa el README de frlg-ldn-trade"
fi

# --- Comprobacion real de que los modulos cargan ---------------------------
paso "Comprobando los modulos"
if "$TRADE/venv/bin/python" - <<'PY'
import sys
fallos = []
for m in ("ldn", "Crypto", "trio", "zstandard"):
    try:
        __import__(m)
    except Exception as e:
        fallos.append("%s: %s" % (m, e))
if fallos:
    for f in fallos:
        print("  falta " + f)
    sys.exit(1)
PY
then
    ok "ldn, pycryptodome, trio y zstandard importan correctamente"
else
    mal "alguno de los modulos no carga; mira el error de arriba"
    exit 1
fi

# --- 4. prod.keys -----------------------------------------------------------
paso "prod.keys"
CLAVES="${SUDO_USER:+/home/$SUDO_USER}/.switch/prod.keys"
[ -f "$CLAVES" ] || CLAVES="$HOME/.switch/prod.keys"
if [ -f "$CLAVES" ]; then
    ok "encontradas en $CLAVES"
    # Validarlas de verdad, no solo comprobar que el fichero existe
    if [ -f "$RAIZ/scripts/check_keys.py" ]; then
        python3 "$RAIZ/scripts/check_keys.py" "$CLAVES" || \
            aviso "el prod.keys tiene problemas; arreglalo antes de intentar el intercambio"
    fi
else
    aviso "NO estan en ~/.switch/prod.keys"
    printf '       Ver docs/03_prod_keys.md. Recuerda: en un Live USB sin\n'
    printf '       persistencia se pierden al reiniciar.\n'
fi

# --- 5. Archivos .pk3 -------------------------------------------------------
paso "Archivos .pk3"
NPK=$(find "$RAIZ/pk3" -maxdepth 2 -type f \( -name '*.pk3' -o -name '*.ek3' \) 2>/dev/null | wc -l)
if [ "$NPK" -ge 2 ]; then
    ok "$NPK archivo(s) en pk3/"
else
    aviso "solo $NPK archivo(s) en pk3/ - hacen falta al menos 2"
    printf '       Uno de relleno para la party + el que quieras enviar.\n'
fi

# --- 6. Resumen -------------------------------------------------------------
paso "Listo"
cat <<RESUMEN

  Lee primero el README de frlg-ldn-trade (puede haber cambiado desde que
  se escribio el blueprint):

      less $TRADE/README.md

  Secuencia del primer intercambio:

    1. En la Switch: Rojo Fuego -> Centro Pokemon -> Direct Corner
       -> Trade Center -> crear la sesion como LEADER.

    2. En el PC, liberar la tarjeta Wi-Fi:
         sudo systemctl stop NetworkManager

    3. Lanzar (ajusta las rutas de los .pk3):
         cd $TRADE
         sudo -E ./venv/bin/python frlgtrade.py --live \\
             -o $RAIZ/pk3/recibido.pk3 \\
             $RAIZ/pk3/ejemplos/dummy.pk3 \\
             $RAIZ/pk3/ejemplos/enviar.pk3

       Opciones utiles:
         --verbose            mas detalle, imprescindible si algo falla
         --phy phy1           elegir otra radio si tienes varias
         --keys RUTA          prod.keys fuera de ~/.switch/

    4. En la Switch debe aparecer el jugador "EMU". Acepta su entrada.

    5. Entra a la sala, ve a la SILLA IZQUIERDA, elige el Pokemon y
       acepta el intercambio.

    6. Al terminar:
         sudo systemctl start NetworkManager

  Puede hacer falta mas de un intento para que conecte. El propio README
  del proyecto lo advierte, asi que no te alarmes al primer fallo.

RESUMEN
