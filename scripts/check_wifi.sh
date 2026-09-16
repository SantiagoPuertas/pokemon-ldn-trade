#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# check_wifi.sh - Diagnostico de la tarjeta Wi-Fi para LDN (Nintendo Switch)
#
# Ejecutar en Ubuntu (Live USB), no en Windows:
#     bash scripts/check_wifi.sh
#
# Recopila lo que kinnay/LDN y frlg-ldn-trade necesitan del hardware Wi-Fi
# y da un veredicto ORIENTATIVO. La prueba definitiva es conectar de verdad
# con la Switch; esto solo sirve para descartar rapido el hardware que no
# puede funcionar.
# ---------------------------------------------------------------------------
set -uo pipefail

BOLD=$'\e[1m'; RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; DIM=$'\e[2m'; RST=$'\e[0m'

titulo() { printf '\n%s=== %s ===%s\n' "$BOLD" "$1" "$RST"; }
ok()     { printf '  %s[ OK  ]%s %s\n' "$GRN" "$RST" "$1"; }
mal()    { printf '  %s[FALLA]%s %s\n' "$RED" "$RST" "$1"; }
aviso()  { printf '  %s[ ??  ]%s %s\n' "$YEL" "$RST" "$1"; }
info()   { printf '  %s%s%s\n' "$DIM" "$1" "$RST"; }

FALLOS=0
AVISOS=0

# --- Herramientas necesarias ------------------------------------------------
titulo "Herramientas"
for h in iw lspci; do
    if command -v "$h" >/dev/null 2>&1; then
        ok "$h disponible"
    else
        mal "falta '$h'  ->  sudo apt install -y iw pciutils"
        FALLOS=$((FALLOS + 1))
    fi
done
if ! command -v iw >/dev/null 2>&1; then
    printf '\n%sSin "iw" no se puede continuar.%s\n' "$RED" "$RST"
    exit 1
fi

# --- Sistema ----------------------------------------------------------------
titulo "Sistema"
if [ -r /etc/os-release ]; then
    info "$(. /etc/os-release && printf '%s' "$PRETTY_NAME")"
fi
info "Kernel: $(uname -r)"

PYV=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null || printf '0.0')
if [ "$(printf '%s\n3.12\n' "$PYV" | sort -V | head -1)" = "3.12" ]; then
    ok "Python $PYV  (frlg-ldn-trade pide 3.12+)"
else
    mal "Python $PYV  - frlg-ldn-trade necesita 3.12 o superior"
    FALLOS=$((FALLOS + 1))
fi

# --- Hardware ---------------------------------------------------------------
titulo "Tarjetas de red detectadas"
lspci -k 2>/dev/null | grep -A 3 -iE 'network|wireless' | sed 's/^/  /'
if command -v lsusb >/dev/null 2>&1; then
    USBW=$(lsusb 2>/dev/null | grep -iE 'wlan|wireless|802.11|realtek|ralink|mediatek|atheros' || true)
    if [ -n "$USBW" ]; then
        info ""
        info "Adaptadores USB:"
        printf '%s\n' "$USBW" | sed 's/^/  /'
    fi
fi

# --- Bloqueos por rfkill ----------------------------------------------------
if command -v rfkill >/dev/null 2>&1; then
    titulo "rfkill"
    # Capturado a proposito: `comando | grep -q` puede devolver 141 (SIGPIPE)
    # bajo `set -o pipefail` aunque la coincidencia exista.
    RFK=$(rfkill list 2>/dev/null)
    if printf '%s\n' "$RFK" | grep -i 'yes' >/dev/null; then
        mal "hay radios bloqueadas (soft o hard block)"
        printf '%s\n' "$RFK" | sed 's/^/    /'
        info "Desbloquear:  sudo rfkill unblock all"
        FALLOS=$((FALLOS + 1))
    else
        ok "ninguna radio bloqueada"
    fi
fi

# --- Dominio regulatorio ----------------------------------------------------
titulo "Dominio regulatorio"
info "$(iw reg get 2>/dev/null | grep -m1 '^country' || printf 'desconocido')"
info "LDN usa 2.4 GHz (canales 1, 6 y 11)."

# --- Analisis por radio (phy) ----------------------------------------------
PHYS=$(iw dev 2>/dev/null | sed -n 's/^phy#\(.*\)/phy\1/p')
if [ -z "$PHYS" ]; then
    titulo "Radios Wi-Fi"
    mal "No se detecta ninguna radio Wi-Fi (driver no cargado?)"
    exit 1
fi

for PHY in $PHYS; do
    titulo "Radio $PHY"

    IFACES=$(iw dev 2>/dev/null | awk -v p="$PHY" '
        /^phy#/ { cur = "phy" substr($0, 5) }
        $1 == "Interface" { if (cur == p) print $2 }')

    DRV=""
    if [ -n "$IFACES" ]; then
        for I in $IFACES; do
            D=$(basename "$(readlink -f "/sys/class/net/$I/device/driver" 2>/dev/null)" 2>/dev/null)
            if [ -z "$D" ] || [ "$D" = "." ]; then
                # Fallback: sacar el driver de lspci
                D=$(lspci -k 2>/dev/null | grep -A 3 -iE 'network|wireless' \
                    | sed -n 's/.*Kernel driver in use: *//p' | head -1)
            fi
            if [ -n "$D" ]; then DRV="$D"; fi
            info "Interfaz: $I    driver: ${D:-desconocido}"
        done
    else
        info "Sin interfaz asociada actualmente"
    fi

    INFO=$(iw phy "$PHY" info 2>/dev/null)

    # -- Modos soportados --
    MODOS=$(printf '%s\n' "$INFO" | awk '
        /Supported interface modes/ { f = 1; next }
        f && /^[[:space:]]*\*/ { gsub(/[[:space:]*]/, "", $0); print; next }
        f { exit }')
    info ""
    info "Modos soportados: $(printf '%s' "$MODOS" | tr '\n' ' ')"

    if printf '%s\n' "$MODOS" | grep -qix "monitor"; then
        ok "modo monitor soportado"
    else
        mal "SIN modo monitor - LDN no puede funcionar con esta radio"
        FALLOS=$((FALLOS + 1))
    fi

    if printf '%s\n' "$MODOS" | grep -qix "AP"; then
        ok "modo AP soportado"
    else
        aviso "sin modo AP (puede impedir crear/hostear una red LDN)"
        AVISOS=$((AVISOS + 1))
    fi

    # -- Monitor "software" (se puede anadir siempre, sin ocupar combinacion) --
    SWMODOS=$(printf '%s\n' "$INFO" | awk '
        /software interface modes/ { f = 1; next }
        f && /^[[:space:]]*\*/ { gsub(/[[:space:]*]/, "", $0); print; next }
        f { exit }')
    MON_SW=0
    if printf '%s\n' "$SWMODOS" | grep -qix "monitor"; then MON_SW=1; fi

    # -- Combinaciones de interfaces --
    # Se corta en la siguiente cabecera de seccion (indentacion de 1 tabulador),
    # para no arrastrar cosas como "HT Capability overrides:".
    COMB=$(printf '%s\n' "$INFO" | awk '
        tolower($0) ~ /valid interface combinations/ { f = 1; next }
        f {
            n = 0
            while (substr($0, n + 1, 1) == "\t") n++
            if (length($0) > 0 && n <= 1) exit
            print
        }')
    if [ -n "$COMB" ]; then
        info ""
        info "Combinaciones validas de interfaces:"
        printf '%s\n' "$COMB" | sed 's/^/    /'
        if printf '%s\n' "$COMB" | grep -qi 'monitor'; then
            ok "monitor aparece en las combinaciones de interfaces"
        elif [ "$MON_SW" -eq 1 ]; then
            ok "monitor es 'software interface mode': se puede anadir siempre"
        else
            aviso "monitor no aparece ni en combinaciones ni como modo software:"
            info "     quiza no pueda coexistir con la interfaz managed"
            AVISOS=$((AVISOS + 1))
        fi
    elif [ "$MON_SW" -eq 1 ]; then
        ok "monitor es 'software interface mode': se puede anadir siempre"
    else
        aviso "el driver no declara combinaciones de interfaces"
        AVISOS=$((AVISOS + 1))
    fi

    # -- Canales 2.4 GHz y restriccion "no IR" --
    # Ojo: iw imprime "2412 MHz" en versiones antiguas y "2412.0 MHz" en las
    # recientes. El decimal es opcional en el patron.
    CH24=$(printf '%s\n' "$INFO" \
        | grep -E '24[0-9][0-9](\.[0-9]+)? MHz \[(1|6|11)\]' || true)
    if [ -n "$CH24" ]; then
        info ""
        info "Canales 2.4 GHz relevantes para LDN:"
        printf '%s\n' "$CH24" | sed 's/^[[:space:]]*/    /'
        if printf '%s\n' "$CH24" | grep -q 'no IR'; then
            mal "canales marcados 'no IR': la radio NO puede iniciar transmision"
            FALLOS=$((FALLOS + 1))
        elif printf '%s\n' "$CH24" | grep -qi 'disabled'; then
            mal "canales 2.4 GHz deshabilitados por el dominio regulatorio"
            FALLOS=$((FALLOS + 1))
        else
            ok "canales 1/6/11 utilizables, sin restriccion 'no IR'"
        fi
    else
        aviso "no se detectan canales de 2.4 GHz en esta radio (solo 5 GHz?)"
        AVISOS=$((AVISOS + 1))
    fi

    # -- Aviso especifico rtw89 (RTL8852BE) --
    case "$DRV" in
        rtw89*)
            info ""
            aviso "driver rtw89 (RTL8852BE): NO esta en la lista de tarjetas"
            info "     probadas por frlg-ldn-trade. Que declare 'monitor' no"
            info "     garantiza que soporte inyeccion de frames, que es lo que"
            info "     LDN necesita de verdad."
            info "     Fallback conocido y fiable: ALFA AWUS036ACHM (mt76x0u)."
            AVISOS=$((AVISOS + 1))
            ;;
    esac
done

# --- NetworkManager ---------------------------------------------------------
titulo "NetworkManager"
if ! command -v systemctl >/dev/null 2>&1; then
    info "systemctl no disponible; no se puede comprobar"
elif systemctl is-active --quiet NetworkManager 2>/dev/null; then
    aviso "NetworkManager ACTIVO - hay que pararlo antes de usar LDN:"
    info "     sudo systemctl stop NetworkManager     (te quedaras sin Wi-Fi)"
    info "     sudo systemctl start NetworkManager    (para recuperarla)"
else
    ok "NetworkManager parado"
fi

# --- Veredicto --------------------------------------------------------------
titulo "Veredicto"
if [ "$FALLOS" -gt 0 ]; then
    printf '  %sNO VIABLE con esta radio: %d bloqueo(s).%s\n' "$RED" "$FALLOS" "$RST"
    printf '  No pierdas tiempo peleandote con el driver.\n'
    printf '  Fallback: ALFA AWUS036ACHM (blueprint, seccion 17).\n'
elif [ "$AVISOS" -gt 0 ]; then
    printf '  %sPOSIBLEMENTE VIABLE: %d aviso(s), ningun bloqueo.%s\n' "$YEL" "$AVISOS" "$RST"
    printf '  Merece la pena intentar la conexion real con la Switch.\n'
else
    printf '  %sBUENA PINTA: sin bloqueos ni avisos.%s\n' "$GRN" "$RST"
fi
printf '\n  %sEsto es solo un filtro previo. La prueba de verdad es que aparezca\n' "$DIM"
printf '  "EMU" en la pantalla de la Switch.%s\n\n' "$RST"
