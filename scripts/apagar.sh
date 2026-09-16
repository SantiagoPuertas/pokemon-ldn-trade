#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# apagar.sh - Apaga el Ubuntu live sin quedarse colgado
#
#     bash scripts/apagar.sh                # apagar
#     bash scripts/apagar.sh --reiniciar    # reiniciar
#
# El cuelgue al apagar NO es un fallo del sistema: un Ubuntu live se esta
# ejecutando desde el propio pendrive, asi que al final del apagado lo expulsa
# y se queda esperando a que pulses ENTER ("Please remove the installation
# medium, then press ENTER"). Si en esa fase el teclado ya no responde --
# pasa en bastantes portatiles -- el ordenador se queda ahi para siempre y
# parece que el kernel ha muerto.
#
# Este script se salta esa fase: sincroniza los discos a mano y despues pide
# un apagado inmediato al kernel, sin desmontar el medio live.
#
# Cortar la corriente a lo bruto SIN sincronizar antes es probablemente lo que
# se estaba comiendo la persistencia del pendrive: lo que aun estaba en cache
# no llegaba a escribirse. De ahi los dos `sync` de abajo.
# ---------------------------------------------------------------------------
set -uo pipefail

ACCION="poweroff"
[ "${1:-}" = "--reiniciar" ] && ACCION="reboot"

BOLD=$'\e[1m'; GRN=$'\e[32m'; YEL=$'\e[33m'; DIM=$'\e[2m'; RST=$'\e[0m'
paso()  { printf '\n%s==> %s%s\n' "$BOLD" "$1" "$RST"; }
ok()    { printf '  %s[ OK ]%s %s\n' "$GRN" "$RST" "$1"; }
aviso() { printf '  %s[ !! ]%s %s\n' "$YEL" "$RST" "$1"; }
info()  { printf '  %s%s%s\n' "$DIM" "$1" "$RST"; }

# --- 1. Dejar la radio como estaba ------------------------------------------
# Si vienes de un intercambio, NetworkManager puede estar parado y la Wi-Fi
# sin gestionar. No afecta al apagado, pero deja el sistema coherente.
if command -v nmcli >/dev/null 2>&1; then
    for DEV in $(nmcli -t -f DEVICE,STATE device 2>/dev/null | awk -F: '$2=="unmanaged"{print $1}'); do
        case "$DEV" in
            wl*) sudo nmcli device set "$DEV" managed yes 2>/dev/null && info "$DEV devuelto a NetworkManager" ;;
        esac
    done
fi

# --- 2. Sincronizar ---------------------------------------------------------
paso "Sincronizando escrituras pendientes"
sync; sync
sleep 2
ok "cache volcada al pendrive"

# --- 3. Apagar --------------------------------------------------------------
paso "Apagando"
info "Se salta la fase de 'expulsa el pendrive y pulsa ENTER'."
info "Puedes sacar el pendrive cuando la pantalla se apague."
info ""
printf '  Ctrl+C para cancelar. '
for N in 5 4 3 2 1; do printf '%s ' "$N"; sleep 1; done
printf '\n'

# --force --force = se lo pide directamente al kernel, sin scripts de apagado
sudo systemctl "$ACCION" --force --force 2>/dev/null

# Si systemd no respondio, ultimo recurso: magic SysRq.
# Ubuntu trae kernel.sysrq=176, que ya incluye el bit de apagado (128).
sleep 5
aviso "systemd no respondio; probando magic SysRq"
[ "$ACCION" = "reboot" ] && LETRA=b || LETRA=o
printf 's' | sudo tee /proc/sysrq-trigger >/dev/null 2>&1
sleep 1
printf '%s' "$LETRA" | sudo tee /proc/sysrq-trigger >/dev/null 2>&1

sleep 5
aviso "tampoco. A mano: Alt+SysRq (Fn+ImprPant) y despues la tecla O."
