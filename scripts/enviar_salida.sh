#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# enviar_salida.sh - Sube el contenido de salidas/ al repo
#
#     bash scripts/enviar_salida.sh                 # sube todo lo que haya
#     bash scripts/enviar_salida.sh -m "primer intento de EMU"
#     bash scripts/enviar_salida.sh --capturar wifi -- bash scripts/check_wifi.sh
#
# Es el canal entre Ubuntu y Windows: aqui se escriben las salidas, se suben al
# repositorio, y desde el otro sistema se leen con un git pull.
#
# Con --capturar NOMBRE -- COMANDO..., ejecuta el comando, guarda su salida en
# salidas/NOMBRE-FECHA.txt y la sube. Sin eso, sube lo que ya haya en salidas/.
# ---------------------------------------------------------------------------
set -uo pipefail

RAIZ=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
SALIDAS="$RAIZ/salidas"

BOLD=$'\e[1m'; RED=$'\e[31m'; GRN=$'\e[32m'; YEL=$'\e[33m'; DIM=$'\e[2m'; RST=$'\e[0m'
paso()  { printf '\n%s==> %s%s\n' "$BOLD" "$1" "$RST"; }
ok()    { printf '  %s[ OK ]%s %s\n' "$GRN" "$RST" "$1"; }
aviso() { printf '  %s[ !! ]%s %s\n' "$YEL" "$RST" "$1"; }
morir() { printf '  %s[FALLA]%s %s\n' "$RED" "$RST" "$1"; exit 1; }
info()  { printf '  %s%s%s\n' "$DIM" "$1" "$RST"; }

MENSAJE=""
CAPTURAR=""
while [ $# -gt 0 ]; do
    case "$1" in
        -m|--mensaje)   MENSAJE="${2:-}"; shift 2 ;;
        -c|--capturar)  CAPTURAR="${2:-}"; shift 2 ;;
        --) shift; break ;;
        -h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) morir "opcion desconocida: $1" ;;
    esac
done

mkdir -p "$SALIDAS"

# --- Captura opcional -------------------------------------------------------
if [ -n "$CAPTURAR" ]; then
    [ $# -gt 0 ] || morir "usa: --capturar NOMBRE -- COMANDO..."
    DESTINO="$SALIDAS/${CAPTURAR}-$(date +%Y%m%d-%H%M%S).txt"
    paso "Ejecutando y capturando en $(basename "$DESTINO")"
    {
        printf '$ %s\n' "$*"
        printf 'fecha: %s\n' "$(date -Is)"
        printf 'kernel: %s\n\n' "$(uname -r)"
    } > "$DESTINO"
    # El codigo de salida del comando, no el del tee
    "$@" 2>&1 | tee -a "$DESTINO"
    COD=${PIPESTATUS[0]}
    printf '\n[codigo de salida: %d]\n' "$COD" >> "$DESTINO"
    ok "guardado (el comando salio con $COD)"
    [ -n "$MENSAJE" ] || MENSAJE="salida de $CAPTURAR (codigo $COD)"
fi

# --- Que hay que subir ------------------------------------------------------
paso "Ficheros en salidas/"
NUM=$(find "$SALIDAS" -type f ! -name '.gitkeep' 2>/dev/null | wc -l)
if [ "$NUM" -eq 0 ]; then
    aviso "salidas/ esta vacio; no hay nada que enviar"
    exit 0
fi
find "$SALIDAS" -type f ! -name '.gitkeep' -printf '  %f  (%s B)\n' 2>/dev/null | sort

# --- Aviso de seguridad -----------------------------------------------------
# Las salidas pueden llevar rutas o nombres de red, pero lo grave seria colar
# una clave. Se comprueba explicitamente antes de subir nada.
paso "Comprobando que no se cuela ninguna clave"
SOSPECHA=$(grep -rlEi 'master_key_[0-9]|aes_ke[ky]_generation_source|BEGIN [A-Z ]*PRIVATE KEY' \
    "$SALIDAS" 2>/dev/null || true)
if [ -n "$SOSPECHA" ]; then
    printf '\n'
    morir "estos ficheros parecen contener claves; NO se suben:
$(printf '%s\n' "$SOSPECHA" | sed 's/^/       /')

       Revisalos y borra las lineas con claves antes de reintentar."
fi
ok "ninguna clave detectada"

# --- Subir ------------------------------------------------------------------
paso "Subiendo al repositorio"
cd "$RAIZ" || morir "no puedo entrar en $RAIZ"

git add -- salidas/ || morir "fallo git add"
if git diff --cached --quiet -- salidas/; then
    aviso "no hay cambios nuevos que subir"
    exit 0
fi

[ -n "$MENSAJE" ] || MENSAJE="salidas de Ubuntu $(date +%Y-%m-%d\ %H:%M)"
git -c user.name="${GIT_AUTHOR_NAME:-Santiago Puertas}" \
    -c user.email="${GIT_AUTHOR_EMAIL:-46724194+SantiagoPuertas@users.noreply.github.com}" \
    commit -q -m "Salidas: $MENSAJE" || morir "fallo git commit"
ok "commit hecho"

# Integrar antes de empujar, por si se toco el repo desde el otro sistema
if ! git pull --rebase --quiet origin main; then
    aviso "el rebase con origin/main fallo; resuelvelo y repite el push"
    exit 1
fi

if git push -q origin main; then
    ok "subido"
    info ""
    info "Ya se puede leer desde el otro sistema con:  git pull"
else
    printf '\n'
    aviso "el push fallo. Lo mas habitual es la autenticacion:"
    info "  GitHub pide un Personal Access Token con permiso 'repo',"
    info "  no tu contrasena. Se crea en:"
    info "     GitHub -> Settings -> Developer settings -> Personal access tokens"
    info ""
    info "  Para no repetirlo en cada push de esta sesion:"
    info "     git config --global credential.helper 'cache --timeout=10800'"
    info ""
    info "  El commit ya esta hecho en local: basta con reintentar"
    info "     git push origin main"
    exit 1
fi
