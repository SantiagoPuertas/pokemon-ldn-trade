#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# escuchar_ldn.sh - ¿Esta la Switch emitiendo algo, y en que canal?
#
#     sudo bash scripts/escuchar_ldn.sh 2>&1 | tee salidas/escucha.txt
#     sudo bash scripts/escuchar_ldn.sh --seg 10 --canales "1 6 11"
#
# frlgtrade.py --live dice "saw 0" y no aclara si el problema es del PC o de
# la Switch. Este script separa las dos cosas: escucha en crudo, sin claves,
# sin Pia y sin frlgsim, y cuenta los action frames de cada canal.
#
#   - Si aqui NO se ve nada:  la Switch no esta emitiendo (o no en estos
#                             canales) -> el problema esta en la consola.
#   - Si aqui SI se ve algo:  la radio recibe bien -> el problema esta mas
#                             arriba: claves, comm-id o parseo.
#
# Deja la captura completa en salidas/captura_ldn/ para poder analizarla.
# La interfaz monitor se borra y NetworkManager se rearranca al terminar,
# tambien si cancelas con Ctrl+C.
# ---------------------------------------------------------------------------
set -uo pipefail

MONIF="ldnsniff0"
PHY=""
SEG=8
# LDN usa 1/6/11 en 2,4 GHz y 36/40/44/48 en 5 GHz. Se prueban todos porque
# no sabemos cual ha elegido la consola.
CANALES="1 6 11 36 40 44 48"

RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DESTINO="$RAIZ/salidas/captura_ldn"

BOLD=$'\e[1m'; RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; DIM=$'\e[2m'; RST=$'\e[0m'
titulo() { printf '\n%s=== %s ===%s\n' "$BOLD" "$1" "$RST"; }
ok()     { printf '  %s[ OK  ]%s %s\n' "$GRN" "$RST" "$1"; }
mal()    { printf '  %s[FALLA]%s %s\n' "$RED" "$RST" "$1"; }
aviso()  { printf '  %s[ ??  ]%s %s\n' "$YEL" "$RST" "$1"; }
info()   { printf '  %s%s%s\n' "$DIM" "$1" "$RST"; }

while [ $# -gt 0 ]; do
    case "$1" in
        --phy)     PHY="${2:-}"; shift 2 ;;
        --iface)   MONIF="${2:-}"; shift 2 ;;
        --seg)     SEG="${2:-8}"; shift 2 ;;
        --canales) CANALES="${2:-}"; shift 2 ;;
        -h|--help) sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) mal "opcion desconocida: $1"; exit 1 ;;
    esac
done

[ "$(uname -s)" = "Linux" ] || { mal "Este script es para Linux."; exit 1; }

if [ "$(id -u)" -ne 0 ]; then
    info "Hacen falta privilegios de root; relanzando con sudo..."
    exec sudo -- "$0" ${PHY:+--phy "$PHY"} --iface "$MONIF" --seg "$SEG" --canales "$CANALES"
fi

NM_PARADO_POR_MI=0
MONIF_CREADA=0
LIMPIEZA_HECHA=0

limpieza() {
    [ "$LIMPIEZA_HECHA" -eq 1 ] && return 0
    LIMPIEZA_HECHA=1
    titulo "Limpieza"
    if [ "$MONIF_CREADA" -eq 1 ]; then
        iw dev "$MONIF" del 2>/dev/null && ok "interfaz $MONIF eliminada" \
            || aviso "borrala a mano:  sudo iw dev $MONIF del"
    fi
    if [ "$NM_PARADO_POR_MI" -eq 1 ]; then
        systemctl start NetworkManager 2>/dev/null && ok "NetworkManager arrancado de nuevo" \
            || aviso "arrancalo a mano:  sudo systemctl start NetworkManager"
    fi
}
trap limpieza EXIT INT TERM

# --- 1. Quien tiene cogida la radio ----------------------------------------
titulo "Quien puede estar robando la radio"
for SRV in NetworkManager wpa_supplicant iwd; do
    if systemctl is-active --quiet "$SRV" 2>/dev/null; then
        aviso "$SRV esta ACTIVO"
    else
        ok "$SRV parado o inexistente"
    fi
done
info "Cualquiera de los tres puede sacar la tarjeta del canal en mitad del"
info "escaneo y hacer que frlgtrade no vea nada."

# --- 2. prod.keys: donde estan y que contienen ------------------------------
# sudo ignora -E en esta maquina, asi que HOME pasa a ser /root y la ruta por
# defecto ~/.switch/prod.keys NO es la del usuario. Importa saberlo.
titulo "prod.keys"
USUARIO="${SUDO_USER:-}"
for CLAVES in ${USUARIO:+/home/$USUARIO/.switch/prod.keys} /root/.switch/prod.keys; do
    if [ -f "$CLAVES" ]; then
        ok "existe $CLAVES"
        for K in aes_kek_generation_source aes_key_generation_source master_key_00 master_key_12; do
            if grep -qE "^[[:space:]]*$K[[:space:]]*=" "$CLAVES"; then
                info "    tiene $K"
            else
                info "    NO tiene $K"
            fi
        done
    else
        aviso "no existe $CLAVES"
    fi
done
info "Bajo sudo, HOME es /root: si el fichero solo esta en tu home, hay que"
info "pasar --keys con la ruta completa."

# --- 3. Dependencias --------------------------------------------------------
titulo "Dependencias"
if command -v tcpdump >/dev/null 2>&1; then
    ok "tcpdump disponible"
else
    aviso "falta tcpdump; hay que instalarlo AHORA (luego no habra Internet)"
    apt update && apt install -y tcpdump || { mal "no se pudo instalar tcpdump"; exit 1; }
    ok "tcpdump instalado"
fi

# --- 4. Radio e interfaz monitor -------------------------------------------
titulo "Radio"
[ -n "$PHY" ] || PHY=$(iw dev 2>/dev/null | sed -n 's/^phy#\(.*\)/phy\1/p' | head -1)
[ -n "$PHY" ] || { mal "no se detecta ninguna radio Wi-Fi"; exit 1; }
info "Usando $PHY  (cambialo con --phy phyN)"

if systemctl is-active --quiet NetworkManager 2>/dev/null; then
    if systemctl stop NetworkManager 2>/dev/null; then
        NM_PARADO_POR_MI=1
        ok "NetworkManager parado"
    else
        aviso "no se pudo parar NetworkManager"
    fi
fi

titulo "Interfaz monitor"
iw dev "$MONIF" del 2>/dev/null && info "habia un $MONIF anterior; eliminado"
iw phy "$PHY" interface add "$MONIF" type monitor 2>/dev/null \
    || { mal "no se pudo crear la interfaz monitor sobre $PHY"; exit 1; }
MONIF_CREADA=1
ip link set "$MONIF" up 2>/dev/null || { mal "no se pudo levantar $MONIF"; exit 1; }
ok "$MONIF creada y levantada"

# --- 5. Escuchar canal por canal -------------------------------------------
mkdir -p "$DESTINO"
rm -f "$DESTINO"/ch_*.txt

titulo "Escucha ($SEG s por canal)"
info "Deja la Switch en la pantalla de espera del Trade Center TODO el rato."
printf '\n'
printf '  %-8s %-10s %-10s %-10s\n' canal frames beacons action
printf '  %-8s %-10s %-10s %-10s\n' ----- ------ ------- ------
TOTAL_ACTION=0
CANALES_CON_ACTION=""
for CH in $CANALES; do
    if ! iw dev "$MONIF" set channel "$CH" 2>/dev/null; then
        printf '  %-8s %s\n' "$CH" "(no se pudo fijar el canal)"
        continue
    fi
    FICH="$DESTINO/ch_$CH.txt"
    # Solo frames de gestion: los de datos son ruido y engordan la captura.
    # -e cabecera 802.11, -x volcado hexadecimal (para reconocer el OUI de
    # Nintendo), -c tope por si el canal esta saturado.
    timeout "$SEG" tcpdump -i "$MONIF" -e -n -s 300 -x -c 250 'type mgt' \
        >"$FICH" 2>/dev/null
    N_TOT=$(grep -cE '^[0-9]{2}:[0-9]{2}:[0-9]{2}' "$FICH" 2>/dev/null || true)
    N_BEA=$(grep -c 'Beacon' "$FICH" 2>/dev/null || true)
    N_ACT=$(grep -c 'Action' "$FICH" 2>/dev/null || true)
    printf '  %-8s %-10s %-10s %-10s\n' "$CH" "${N_TOT:-0}" "${N_BEA:-0}" "${N_ACT:-0}"
    TOTAL_ACTION=$((TOTAL_ACTION + ${N_ACT:-0}))
    [ "${N_ACT:-0}" -gt 0 ] && CANALES_CON_ACTION="$CANALES_CON_ACTION $CH"
done

# --- 6. Veredicto -----------------------------------------------------------
titulo "Veredicto"
if [ "$TOTAL_ACTION" -gt 0 ]; then
    printf '  %sSE RECIBEN ACTION FRAMES%s en el/los canal(es):%s\n' "$GRN" "$RST" "$CANALES_CON_ACTION"
    printf '  La radio recibe. Si frlgtrade sigue diciendo "saw 0", el fallo\n'
    printf '  esta mas arriba: claves, version del protocolo o comm-id.\n'
else
    printf '  %sNINGUN ACTION FRAME.%s\n' "$YEL" "$RST"
    printf '  O la Switch no esta emitiendo, o lo hace en un canal no probado.\n'
    printf '  Comprueba en la consola que sigue en la pantalla de espera del\n'
    printf '  Trade Center, y repite sin moverla de ahi.\n'
fi
printf '\n'
info "Capturas completas en: $DESTINO"
info "Subelas con:  bash scripts/enviar_salida.sh"
