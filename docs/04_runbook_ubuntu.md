# 04 — Runbook de Ubuntu

Todo lo que hay que teclear en Ubuntu, en orden, desde arrancar hasta el
intercambio. Pensado para seguirlo de arriba abajo sin tener que recordar nada.

Al final está [cómo enviarme las salidas](#8-enviarme-las-salidas), que es el
canal entre los dos sistemas: Ubuntu escribe ficheros, los sube al repo, y desde
Windows se leen.

---

## 0. Antes de arrancar (en Windows)

Ten a mano:

- La **Switch** con Rojo Fuego, con el **Direct Corner desbloqueado**.
- El **pendrive** `Doors`.
- Este runbook abierto en el móvil o impreso — en Ubuntu vas a quedarte sin
  Internet a ratos.

---

## 1. Arrancar Ubuntu

1. Reinicia y entra al Boot Menu (`F12` / `F9` / `F11` / `Esc`).
   Alternativa desde Windows: *Configuración → Sistema → Recuperación →
   Inicio avanzado → Reiniciar ahora → Usar un dispositivo*.
2. Elige `UEFI: SanDisk Ultra`.
3. En GRUB: **"Try Ubuntu"**, no "Install Ubuntu".
4. Conéctate al Wi-Fi normal (harán falta descargas).

> Si falla el arranque por Secure Boot: en la BIOS, activa
> **"Microsoft 3rd-party UEFI CA"**. Desactivar Secure Boot entero es el plan B.

Abre una terminal con `Ctrl+Alt+T`.

---

## 2. Traer el repositorio

Funciona tanto si la persistencia sobrevivió como si no:

```bash
sudo apt update && sudo apt install -y git
cd ~ && { git -C ~/pokemon-ldn-trade pull || git clone https://github.com/SantiagoPuertas/pokemon-ldn-trade.git; }
cd ~/pokemon-ldn-trade
```

---

## 3. Montar el entorno

```bash
bash scripts/setup_ubuntu.sh 2>&1 | tee salidas/setup.txt
```

Instala dependencias del sistema, clona `frlg-ldn-trade` en `vendor/`, crea el
`venv`, comprueba que los cuatro módulos importan y valida el `prod.keys`.

**Qué esperar:** todo en `[ OK ]` salvo, quizá, un aviso de que falta
`master_key_12`. Ese aviso no bloquea nada.

Si falla hablando de `gcc`, `cc1` o `Python.h`:

```bash
sudo apt install -y build-essential python3-dev
```

y repite.

---

## 4. Claude Code en Ubuntu

Para no tener que reiniciar a Windows cada vez que algo falle.

```bash
bash scripts/instalar_claude_code.sh
```

Usa el instalador nativo oficial: se baja un binario a `~/.local/bin/claude`,
**sin Node ni npm**. Después:

```bash
cd ~/pokemon-ldn-trade && claude
```

La primera vez abre Firefox para iniciar sesión. Necesita plan Pro o Max —
el gratuito no incluye Claude Code.

Como todo queda en `$HOME`, sobrevive al reinicio **si la persistencia
aguanta**. Si no aguanta, repetirlo cuesta dos minutos.

> **Ojo con la red.** Claude Code necesita Internet, y en el paso 7.3 la Wi-Fi
> se la queda LDN. Para que siga vivo durante el intercambio, enchufa el
> **cable Ethernet** y libera sólo la Wi-Fi (ver 7.3). Sin cable, durante el
> intercambio te quedas sin Claude Code y sin Internet, y hay que volver al
> canal de `salidas/` de la sección 8.

---

## 5. Las `prod.keys`

Sólo si no las tienes ya (o si se perdieron al reiniciar):

```bash
mkdir -p ~/.switch && nano ~/.switch/prod.keys
```

Pega las tres líneas en formato `nombre = valor`, guarda con `Ctrl+O` y sal con
`Ctrl+X`. Después:

```bash
chmod 600 ~/.switch/prod.keys
python3 scripts/check_keys.py 2>&1 | tee salidas/claves.txt
```

**Qué esperar:** `FICHERO CORRECTO` o `SIRVE, con 1 aviso`. Si sale
`NO SIRVE`, el propio validador te dice en qué línea está el problema — lo más
habitual son comentarios o cabeceras de sección, que `ldn.load_keys()` no admite.

---

## 6. Comprobar el hardware *(opcional)*

Ya salió bien el 2026-09-01, así que sáltatelo salvo que algo vaya raro:

```bash
bash scripts/check_wifi.sh 2>&1 | tee salidas/wifi.txt
sudo bash scripts/check_injection.sh 2>&1 | tee salidas/inyeccion.txt
```

`check_injection.sh` para NetworkManager y lo rearranca solo al terminar.
Hazlo **cerca de un router encendido**, o dará falsos negativos.

---

## 7. El intercambio

> **Atajo:** todo lo de esta sección —comprobar los `.pk3`, soltar la radio,
> lanzar y ver el registro— se puede hacer desde la ventana:
> `python3 scripts/gui.py` (ver [`05_gui.md`](05_gui.md)). Lo de abajo es lo
> que hace por dentro, y sigue siendo la vía cuando algo falla y hay que ver
> el comando exacto.


### 7.1 Comprobar los `.pk3`

```bash
python3 scripts/read_pk3.py pk3/ejemplos/*.pk3
```

Los dos deben decir `checksum [ OK ]`.

### 7.2 En la Switch

```
Rojo Fuego → Centro Pokémon → Direct Corner → Trade Center
    → crear la sesión como LEADER
```

Déjala esperando en esa pantalla.

### 7.3 Liberar la tarjeta Wi-Fi

LDN necesita que **nada más** esté tocando la radio. Hay dos formas.

**Opción A — sólo la Wi-Fi, conservando Internet** *(recomendada si tienes
cable Ethernet)*. En vez de parar NetworkManager entero, se le dice que suelte
esa interfaz concreta:

```bash
nmcli device status                      # localiza la Wi-Fi, p. ej. wlp2s0
sudo nmcli device set wlp2s0 managed no
```

NetworkManager sigue gestionando el cable, así que **mantienes Internet** y
Claude Code sigue vivo durante todo el intercambio.

**Opción B — a lo bruto**, si la A no funciona (el escaneo no ve nada, o algo
sigue reclamando la radio):

```bash
sudo systemctl stop NetworkManager
```

> A partir de aquí **te quedas sin Internet** si la Wi-Fi era tu única
> conexión. Todo lo que necesitas ya está descargado.

En cualquiera de los dos casos, comprueba que no queda nadie más agarrado a la
tarjeta:

```bash
systemctl is-active NetworkManager wpa_supplicant iwd
```

### 7.4 Lanzar

```bash
cd ~/pokemon-ldn-trade/vendor/frlg-ldn-trade
sudo -E ./venv/bin/python frlgtrade.py --live --verbose \
    -o ~/pokemon-ldn-trade/pk3/recibido.pk3 \
    ~/pokemon-ldn-trade/pk3/ejemplos/dummy.pk3 \
    ~/pokemon-ldn-trade/pk3/ejemplos/enviar.pk3 2>&1 \
    | tee ~/pokemon-ldn-trade/salidas/intercambio.txt
```

`--verbose` desde el principio: si algo falla, sin él no hay nada que mirar.

**Puede hacer falta más de un intento para conectar.** Lo advierte el propio
README del proyecto. No te alarmes al primer fallo; repite unas cuantas veces
antes de dar por hecho que algo va mal.

Si tuvieras varias radios Wi-Fi, elige la buena con `--phy phy0`.

### 7.5 En la Switch

```
aparece el jugador "EMU"
    → aceptar su entrada
    → entrar a la sala
    → caminar hacia la SILLA IZQUIERDA
    → elegir el Pokémon que entregas
    → aceptar el intercambio
```

### 7.6 Al terminar

Deshaz lo que hicieras en 7.3:

```bash
sudo nmcli device set wlp2s0 managed yes   # si usaste la opción A
sudo systemctl start NetworkManager        # si usaste la opción B
```

El Pokémon que te haya enviado la Switch queda en `pk3/recibido.pk3`.
Compruébalo:

```bash
python3 scripts/read_pk3.py pk3/recibido.pk3
```

---

## 8. Enviarme las salidas

Todos los comandos de arriba guardan su salida en `salidas/` gracias al `tee`.
Para que yo las lea desde Windows hay dos vías.

### Vía A — subirlas al repo *(recomendada)*

```bash
bash scripts/enviar_salida.sh
```

Hace el `add`, `commit` y `push` de `salidas/` con un mensaje automático.

La primera vez te pedirá usuario y contraseña de GitHub. La contraseña **no es
tu contraseña**: es un *Personal Access Token* con permiso `repo`, que se crea
en GitHub → Settings → Developer settings → Personal access tokens.

Para no reintroducirlo en cada push de la sesión:

```bash
git config --global credential.helper 'cache --timeout=10800'
```

Lo guarda **en memoria** durante 3 horas. Existe también `store`, que lo escribe
en texto plano en `~/.git-credentials`; sobrevive a reinicios si tienes
persistencia, pero queda en claro en el disco. Tú eliges.

### Vía B — copiar y pegar

```bash
cat salidas/intercambio.txt
```

Y lo pegas en el chat. Para salidas largas:

```bash
tail -60 salidas/intercambio.txt
```

---

## 9. Apagar sin dejarlo colgado

```bash
bash scripts/apagar.sh
```

**Lo que estabas viendo no era un kernel muerto.** Un Ubuntu live se ejecuta
desde el propio pendrive, así que al final del apagado lo expulsa y se queda
esperando a que pulses ENTER:

```
Please remove the installation medium, then press ENTER
```

Si en esa fase el teclado ya no responde — pasa en bastantes portátiles — el
ordenador se queda ahí indefinidamente y parece colgado. Por eso acababas
sacando el pendrive y cortando la corriente a mano.

`apagar.sh` se salta esa fase: sincroniza los discos y pide el apagado
directamente al kernel, sin desmontar el medio live.

> Y probablemente arregle de paso **la persistencia**. Cortar la corriente sin
> sincronizar deja en caché escrituras que nunca llegan a `casper-rw`: eso
> explicaría que unas veces sobreviva y otras no. El script hace `sync` dos
> veces antes de apagar.

Si algún día quieres hacerlo a mano, es esto:

```bash
sync; sync; sudo systemctl poweroff --force --force
```

Último recurso con el teclado, sin terminal: **Alt+SysRq** (en portátiles,
`Fn`+`ImprPant`) y después `S` para sincronizar y `O` para apagar.

---

## Si algo falla

### `no joinable FRLG network (saw 0, 0 joinable)`

El escaneo no encontró la red de la Switch. Antes de tocar nada, separa si el
problema es del PC o de la consola:

```bash
sudo bash scripts/escuchar_ldn.sh 2>&1 | tee salidas/escucha.txt
```

Escucha en crudo los canales 1/6/11 y 36/40/44/48, sin claves ni Pia, y cuenta
los *action frames* de cada uno. Si no ve ninguno, el problema está en la
Switch (o en un canal no probado); si ve alguno, la radio recibe bien y el
fallo está más arriba: claves, versión del protocolo o `comm-id`.

Repasa además, por orden de "cuesta nada":

1. **Repítelo varias veces.** El escaneo dura ~6 s en total (3 intentos). El
   propio README del proyecto avisa de que puede hacer falta insistir.
2. **`sudo -E` no funciona en esta máquina** — lo dice él mismo al arrancar.
   Bajo `sudo`, `HOME` es `/root`, así que la ruta por defecto
   `~/.switch/prod.keys` **no** es la tuya. Pásala entera:
   `--keys /home/ubuntu/.switch/prod.keys`.
3. **`master_key_12`.** Si la sesión negocia LDN v3 y sólo tienes
   `master_key_00`, el frame de anuncio no se puede descifrar y aparece
   `Failed to parse advertisement frame, ignoring it` — que es justamente
   "oigo a la Switch pero no la entiendo".
4. **Nada más debe tener cogida la radio**: `NetworkManager`, `wpa_supplicant`
   e `iwd`, los tres parados.

| Síntoma | Dónde mirar |
|---|---|
| `EMU` no aparece en la Switch | LDN / Wi-Fi. Repite `check_injection.sh` |
| `KeyError` o `ValueError` al arrancar | el `prod.keys`. `python3 scripts/check_keys.py` |
| `EMU` aparece pero no entra | Pia / protocolo. Guarda la salida con `--verbose` |
| Entra pero el intercambio falla | máquina de estados RFU. Salida completa |
| El `.pk3` sale raro en el juego | `python3 scripts/read_pk3.py` sobre el fichero |

Ese desglose viene de la sección 20 del blueprint: cada capa falla de una forma
distinta, y saber cuál es te ahorra buscar en el sitio equivocado.

---

## Chuleta

```bash
# arranque en frío, todo de una vez
cd ~ && { git -C ~/pokemon-ldn-trade pull || git clone https://github.com/SantiagoPuertas/pokemon-ldn-trade.git; }
cd ~/pokemon-ldn-trade && bash scripts/setup_ubuntu.sh

# el intercambio  (con cable Ethernet: sudo nmcli device set wlp2s0 managed no)
sudo systemctl stop NetworkManager
cd vendor/frlg-ldn-trade && sudo -E ./venv/bin/python frlgtrade.py --live --verbose \
    -o ../../pk3/recibido.pk3 ../../pk3/ejemplos/dummy.pk3 ../../pk3/ejemplos/enviar.pk3 \
    2>&1 | tee ../../salidas/intercambio.txt
sudo systemctl start NetworkManager

# mandarme el resultado
cd ~/pokemon-ldn-trade && bash scripts/enviar_salida.sh

# apagar sin que se cuelgue
bash scripts/apagar.sh
```
