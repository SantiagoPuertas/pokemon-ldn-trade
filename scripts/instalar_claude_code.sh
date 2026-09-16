#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# instalar_claude_code.sh - Deja Claude Code funcionando en el Ubuntu live
#
#     bash scripts/instalar_claude_code.sh
#
# Usa el instalador nativo oficial: NO hace falta Node ni npm, se baja un
# binario y se deja en ~/.local/bin/claude.
#
# Todo queda dentro de $HOME, asi que sobrevive a los reinicios SI la
# persistencia del pendrive aguanta. Si no aguanta, repetir esto cuesta un
# par de minutos: instalar + iniciar sesion en el navegador.
#
# Ojo: Claude Code necesita Internet. Durante el intercambio la Wi-Fi esta
# tomada por LDN, asi que hay dos opciones -- ver seccion 7.3 del runbook:
#   - cable Ethernet + liberar solo la Wi-Fi   -> Claude Code sigue vivo
#   - parar NetworkManager entero              -> te quedas sin Internet
# ---------------------------------------------------------------------------
set -uo pipefail

BOLD=$'\e[1m'; RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; DIM=$'\e[2m'; RST=$'\e[0m'
paso()  { printf '\n%s==> %s%s\n' "$BOLD" "$1" "$RST"; }
ok()    { printf '  %s[ OK ]%s %s\n' "$GRN" "$RST" "$1"; }
aviso() { printf '  %s[ !! ]%s %s\n' "$YEL" "$RST" "$1"; }
morir() { printf '  %s[FALLA]%s %s\n' "$RED" "$RST" "$1"; exit 1; }
info()  { printf '  %s%s%s\n' "$DIM" "$1" "$RST"; }

[ "$(uname -s)" = "Linux" ] || morir "Este script es para el Ubuntu del pendrive."

# --- 1. Requisitos ----------------------------------------------------------
paso "Requisitos"

if ! command -v curl >/dev/null 2>&1; then
    aviso "falta curl; instalandolo"
    sudo apt update && sudo apt install -y curl || morir "no pude instalar curl"
fi
ok "curl disponible"

# El instalador se baja de Internet: si no hay red, mejor decirlo ya.
if ! curl -fsS --max-time 10 -o /dev/null https://claude.ai/install.sh; then
    morir "no llego a claude.ai. Conectate al Wi-Fi normal (o pon el cable) y repite."
fi
ok "hay conexion con claude.ai"

RAM=$(awk '/MemTotal/ {print int($2/1024/1024)}' /proc/meminfo)
if [ "${RAM:-0}" -lt 4 ]; then
    aviso "solo $RAM GB de RAM; Claude Code pide 4 GB o mas"
else
    ok "RAM: $RAM GB"
fi

# --- 2. Instalar ------------------------------------------------------------
paso "Instalando Claude Code"
if command -v claude >/dev/null 2>&1; then
    ok "ya estaba instalado: $(claude --version 2>/dev/null || echo '?')"
else
    curl -fsSL https://claude.ai/install.sh | bash || morir "fallo el instalador"
    ok "instalado en ~/.local/share/claude"
fi

# --- 3. PATH ----------------------------------------------------------------
# El instalador deja el lanzador en ~/.local/bin, que en una sesion live no
# siempre esta en el PATH de la terminal actual.
paso "PATH"
case ":$PATH:" in
    *":$HOME/.local/bin:"*) ok "~/.local/bin ya esta en el PATH" ;;
    *)
        export PATH="$HOME/.local/bin:$PATH"
        if ! grep -qs 'HOME/.local/bin' "$HOME/.bashrc" 2>/dev/null; then
            printf '\nexport PATH="$HOME/.local/bin:$PATH"\n' >> "$HOME/.bashrc"
        fi
        ok "anadido a ~/.bashrc y a esta terminal"
        ;;
esac

# --- 4. Comprobar -----------------------------------------------------------
paso "Comprobando"
VER=$("$HOME/.local/bin/claude" --version 2>&1) || morir "el binario no arranca: $VER"
ok "$VER"

# --- 5. Que hacer ahora -----------------------------------------------------
paso "Siguiente paso: iniciar sesion"
info "Arranca Claude Code dentro del repo:"
info ""
info "    cd ~/pokemon-ldn-trade && claude"
info ""
info "La primera vez abre Firefox para que inicies sesion con tu cuenta."
info "Hace falta plan Pro o Max: el plan gratuito no incluye Claude Code."
info ""
info "La sesion se guarda en ~/.claude. Si la persistencia del pendrive"
info "sobrevive al reinicio, no habra que repetirlo."
info ""
aviso "NUNCA subas ~/.claude/.credentials.json a ningun repositorio."
