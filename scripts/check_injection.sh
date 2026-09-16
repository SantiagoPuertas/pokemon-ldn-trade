#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# check_injection.sh - Prueba si la tarjeta Wi-Fi puede INYECTAR frames
#
#     sudo bash scripts/check_injection.sh
#     sudo bash scripts/check_injection.sh --phy phy1 --yes
#
# check_wifi.sh comprueba lo que el driver DECLARA. Este script comprueba lo
# que de verdad HACE, que es la unica pregunta que queda abierta: kinnay/LDN
# exige poder "receive and transmit action frames in monitor mode", y eso
# ningun `iw list` lo puede responder.
#
# No hace falta prod.keys, ni la Switch, ni ficheros .pk3.
#
# TODO lo que toca se deshace solo al terminar, tambien si cancelas con
# Ctrl+C o si algo falla por el camino:
#   - la interfaz monitor que crea se borra
#   - NetworkManager se vuelve a arrancar si lo paró este script
# ---------------------------------------------------------------------------
set -uo pipefail

MONIF="ldntest0"
PHY=""
ASUME_SI=0
CANALES="1 6 11"          # los que usa LDN

BOLD=$'\e[1m'; RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; DIM=$'\e[2m'; RST=$'\e[0m'
titulo() { printf '\n%s=== %s ===%s\n' "$BOLD" "$1" "$RST"; }
ok()     { printf '  %s[ OK  ]%s %s\n' "$GRN" "$RST" "$1"; }
mal()    { printf '  %s[FALLA]%s %s\n' "$RED" "$RST" "$1"; }
aviso()  { printf '  %s[ ??  ]%s %s\n' "$YEL" "$RST" "$1"; }
info()   { printf '  %s%s%s\n' "$DIM" "$1" "$RST"; }

# --- Argumentos -------------------------------------------------------------
while [ $# -gt 0 ]; do
    case "$1" in
        --phy)   PHY="${2:-}"; shift 2 ;;
        --iface) MONIF="${2:-}"; shift 2 ;;
        --yes|-y) ASUME_SI=1; shift ;;
        -h|--help)
            sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        *) mal "opcion desconocida: $1"; exit 1 ;;
    esac
done

[ "$(uname -s)" = "Linux" ] || { mal "Este script es para Linux."; exit 1; }

# --- Necesita root ----------------------------------------------------------
if [ "$(id -u)" -ne 0 ]; then
    info "Hacen falta privilegios de root; relanzando con sudo..."
    exec sudo -- "$0" ${PHY:+--phy "$PHY"} --iface "$MONIF" $([ "$ASUME_SI" -eq 1 ] && echo --yes)
fi

# --- Estado que hay que restaurar ------------------------------------------
NM_PARADO_POR_MI=0
MONIF_CREADA=0
LIMPIEZA_HECHA=0

limpieza() {
    [ "$LIMPIEZA_HECHA" -eq 1 ] && return 0
    LIMPIEZA_HECHA=1
    titulo "Limpieza"
    if [ "$MONIF_CREADA" -eq 1 ]; then
        if iw dev "$MONIF" del 2>/dev/null; then
            ok "interfaz $MONIF eliminada"
        else
            aviso "no se pudo eliminar $MONIF; hazlo a mano:  sudo iw dev $MONIF del"
        fi
    fi
    if [ "$NM_PARADO_POR_MI" -eq 1 ]; then
        if systemctl start NetworkManager 2>/dev/null; then
            ok "NetworkManager arrancado de nuevo (el Wi-Fi tarda unos segundos)"
        else
            aviso "no se pudo arrancar NetworkManager; hazlo a mano:"
            info "     sudo systemctl start NetworkManager"
        fi
    fi
}
trap limpieza EXIT INT TERM

# --- Dependencias: ANTES de tocar la red -----------------------------------
# Importante: al parar NetworkManager te quedas sin Internet, asi que
# cualquier instalacion tiene que ocurrir aqui.
titulo "Dependencias"
if command -v aireplay-ng >/dev/null 2>&1; then
    ok "aireplay-ng disponible"
else
    aviso "falta aireplay-ng (paquete aircrack-ng)"
    info "Hay que instalarlo AHORA: despues de parar NetworkManager te quedas"
    info "sin Internet y ya no se podria."
    RESP="s"
    if [ "$ASUME_SI" -eq 0 ]; then
        printf '  ¿Instalar aircrack-ng con apt? [S/n] '
        read -r RESP </dev/tty || RESP="s"
    fi
    case "${RESP:-s}" in
        [nN]*) mal "sin aireplay-ng no se puede hacer la prueba de inyeccion"; exit 1 ;;
        *)
            apt update && apt install -y aircrack-ng || {
                mal "fallo la instalacion de aircrack-ng"; exit 1; }
            ok "aircrack-ng instalado"
            ;;
    esac
fi

# --- Elegir la radio --------------------------------------------------------
titulo "Radio"
if [ -z "$PHY" ]; then
    PHY=$(iw dev 2>/dev/null | sed -n 's/^phy#\(.*\)/phy\1/p' | head -1)
fi
if [ -z "$PHY" ]; then
    mal "no se detecta ninguna radio Wi-Fi"
    exit 1
fi
info "Usando $PHY  (cambialo con --phy phyN si tienes varias)"

# Ojo: aqui NO se puede usar `iw ... | grep -q`. Con `set -o pipefail`, el
# `grep -q` sale al primer acierto, `iw` recibe SIGPIPE y la tuberia devuelve
# 141 aunque la coincidencia SI se haya producido. Se compara la cadena en
# bash, sin tuberias de por medio.
PHYINFO=$(iw phy "$PHY" info 2>/dev/null)
case "$PHYINFO" in
    *[Mm]onitor*) ok "$PHY declara modo monitor" ;;
    *)
        mal "$PHY no declara modo monitor; no tiene sentido seguir"
        exit 1
        ;;
esac

# --- Parar NetworkManager ---------------------------------------------------
titulo "NetworkManager"
if systemctl is-active --quiet NetworkManager 2>/dev/null; then
    info "Parandolo. Te quedaras temporalmente sin Wi-Fi."
    if systemctl stop NetworkManager 2>/dev/null; then
        NM_PARADO_POR_MI=1
        ok "NetworkManager parado (se rearranca solo al terminar)"
    else
        aviso "no se pudo parar; la prueba puede dar falsos negativos"
    fi
else
    ok "ya estaba parado"
fi

# --- Crear la interfaz monitor ---------------------------------------------
titulo "Interfaz monitor"
iw dev "$MONIF" del 2>/dev/null && info "habia un $MONIF anterior; eliminado"

if ! iw phy "$PHY" interface add "$MONIF" type monitor 2>/dev/null; then
    mal "no se pudo crear una interfaz monitor sobre $PHY"
    info "Esto ya es un bloqueo: LDN necesita modo monitor."
    exit 1
fi
MONIF_CREADA=1
ok "creada $MONIF en modo monitor"

if ! ip link set "$MONIF" up 2>/dev/null; then
    mal "no se pudo levantar $MONIF"
    exit 1
fi
ok "$MONIF levantada"

# --- Prueba 1: fijar los canales de LDN ------------------------------------
titulo "Canales de LDN (2,4 GHz)"
CANALES_OK=""
for CH in $CANALES; do
    if iw dev "$MONIF" set channel "$CH" 2>/dev/null; then
        ok "canal $CH fijado"
        CANALES_OK="$CANALES_OK $CH"
    else
        mal "no se pudo fijar el canal $CH"
    fi
done
if [ -z "$CANALES_OK" ]; then
    mal "no se pudo fijar ningun canal de 2,4 GHz. Bloqueo."
    exit 1
fi

# --- Prueba 2: inyeccion con aireplay-ng -----------------------------------
titulo "Inyeccion de frames"
info "aireplay-ng --test emite probe requests de difusion y cuenta las"
info "respuestas de los AP cercanos. No ataca nada."
info ""
info "IMPORTANTE: hazlo cerca de un router Wi-Fi encendido. Si no hay ningun"
info "AP al alcance dira 'No Answer' aunque la inyeccion funcione."

INY_OK=0
INY_SALIDA=""
for CH in $CANALES_OK; do
    info ""
    info "--- canal $CH ---"
    iw dev "$MONIF" set channel "$CH" 2>/dev/null
    SALIDA=$(timeout 40 aireplay-ng --test "$MONIF" 2>&1)
    printf '%s\n' "$SALIDA" | sed 's/^/      /'
    INY_SALIDA="$INY_SALIDA$SALIDA"$'\n'
    case "$SALIDA" in
        *[Ii]njection\ is\ working*)
            INY_OK=1
            ok "inyeccion CONFIRMADA en el canal $CH"
            break
            ;;
    esac
done

# --- Prueba 3: el driver acepta un action frame -----------------------------
# LDN usa action frames concretamente. Esto comprueba que el camino de
# transmision no los rechaza de plano. Que salga bien NO prueba que llegaran
# al aire (mac80211 puede aceptarlo y el driver descartarlo en silencio),
# pero que salga mal SI es una mala senal clara.
titulo "El driver acepta action frames"
AF_RES=$(python3 - "$MONIF" <<'PY' 2>&1
import socket, sys, struct
iface = sys.argv[1]
# Radiotap minimo: version, pad, len=8, present=0
radiotap = struct.pack("<BBHI", 0, 0, 8, 0)
bcast = b"\xff" * 6
src   = bytes.fromhex("020011223344")      # MAC administrada localmente
# Frame control: type=management(0), subtype=action(13) -> 0xD0
frame = struct.pack("<HH", 0x00D0, 0) + bcast + src + bcast + struct.pack("<H", 0)
frame += bytes([0x04, 0x09])               # categoria Public, Vendor Specific
frame += b"\x00\x1f\x32" + b"LDNTEST"      # OUI ficticio + carga
try:
    s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, 0)
    s.bind((iface, 0))
    s.send(radiotap + frame)
    s.close()
    print("OK")
except PermissionError as e:
    print("ERROR permisos: %s" % e)
except OSError as e:
    print("ERROR %s: %s" % (e.errno, e.strerror))
except Exception as e:
    print("ERROR %s" % e)
PY
)
AF_OK=0
if [ "$AF_RES" = "OK" ]; then
    ok "el action frame fue aceptado por el camino de transmision"
    AF_OK=1
else
    mal "el action frame fue rechazado: $AF_RES"
fi

# --- Veredicto --------------------------------------------------------------
titulo "Veredicto"
if [ "$INY_OK" -eq 1 ] && [ "$AF_OK" -eq 1 ]; then
    printf '  %sLA TARJETA INYECTA.%s\n' "$GRN" "$RST"
    printf '  Monitor, canales 2,4 GHz y action frames: todo correcto.\n'
    printf '  No compres nada: sigue con la RTL8852BE interna.\n'
elif [ "$INY_OK" -eq 1 ]; then
    printf '  %sINYECTA, pero el action frame dio problemas.%s\n' "$YEL" "$RST"
    printf '  Raro. Merece la pena intentar LDN igualmente.\n'
elif [ "$AF_OK" -eq 1 ]; then
    printf '  %sNO CONCLUYENTE.%s\n' "$YEL" "$RST"
    printf '  El driver acepta action frames pero aireplay-ng no vio respuestas.\n'
    printf '  Antes de dar nada por perdido, repitelo AL LADO de un router\n'
    printf '  encendido: sin AP cerca esta prueba da falsos negativos.\n'
else
    printf '  %sNO INYECTA.%s\n' "$RED" "$RST"
    printf '  Repitelo una vez junto a un router encendido para descartar que\n'
    printf '  sea falta de senal. Si vuelve a fallar, es el driver rtw89 y toca\n'
    printf '  el fallback: ALFA AWUS036ACHM (blueprint, seccion 17).\n'
fi
printf '\n  %sNi siquiera esto es la prueba definitiva. La definitiva sigue siendo\n' "$DIM"
printf '  que aparezca "EMU" en la pantalla de la Switch.%s\n' "$RST"

# La limpieza la hace el trap.
