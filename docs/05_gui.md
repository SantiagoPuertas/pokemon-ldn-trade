# La interfaz gráfica

```bash
python3 scripts/gui.py
```

Abre el navegador en <http://127.0.0.1:8777> con cuatro pestañas: **Crear**,
**Caja**, **Intercambio** y **Sistema**. Es todo el proyecto sin escribir un
solo comando.

---

## Cómo se abre, con detalle

El comando hace las dos cosas: levanta el servidor y abre el navegador. **Deja
esa terminal abierta** — mientras el proceso siga vivo la ventana funciona, y
con `Ctrl+C` se apaga.

> `127.0.0.1` es **tu propio ordenador**, no un sitio de internet. Ese enlace
> sólo responde si el servidor está arrancado: si lo pulsas desde GitHub sin
> haberlo hecho, el navegador dirá *no se puede conectar*. No está roto, es que
> no hay nadie escuchando. Se arranca primero y se recarga después.

Las banderas, todas en [`scripts/gui.py`](../scripts/gui.py):

| Bandera | Para qué |
|---|---|
| `--sin-navegador` | No abre el navegador. Útil si ya tienes la pestaña puesta, o si lo lanzas desde otro sitio |
| `--puerto 8778` | Cambia el puerto. Si arrancar falla con *no puedo escuchar en el puerto 8777*, casi siempre es que ya tienes otra GUI abierta |
| `--verboso` | Escribe cada petición HTTP en la terminal |
| `--sin-censura` | Deja las MAC y el SSID a la vista en el registro del intercambio. Por defecto se tapan, y ese registro **no se sube al repositorio** |

Para comprobar desde fuera si está levantada, sin abrir el navegador:

```bash
curl -sI http://127.0.0.1:8777/
```

---

## Por qué es una página web y no una ventana

- **No instala nada.** Es `http.server` de la biblioteca estándar de Python.
  En este Ubuntu live no hay `tkinter` (`ModuleNotFoundError`), y gastar
  persistencia del pendrive en `python3-tk` o en PyQt para esto no compensa.
- **Sobrevive al intercambio.** Escucha en `127.0.0.1`, así que sigue
  funcionando aunque se pare NetworkManager y el equipo se quede sin Internet
  — que es exactamente el momento en el que hace falta.
- **Sólo escucha en local.** Importa, porque hay botones que ejecutan cosas
  con `sudo`: soltar la radio, lanzar el intercambio, apagar.

No sustituye a los scripts: los llama. Crear es `make_pk3`, leer es `read_pk3`
e intercambiar es el `frlgtrade.py` del vendor con los argumentos de la
sección 7 del [runbook](04_runbook_ubuntu.md). Si algo falla en la GUI, falla
igual en la consola, y al revés.

---

## Crear

Todo lo que acepta `make_pk3.py`, pero viéndolo: especie, mote, entrenador,
nivel, naturaleza (con lo que sube y lo que baja), habilidad, amistad, shiny,
objeto, hasta cuatro movimientos, IVs, EVs y el bit *fateful*.

Especie, objeto y movimientos son **desplegables** con todo lo que existe en
Rojo Fuego, en español y agrupado para poder encontrarlo:

- los **354 movimientos**, por tipo (Fuego, Agua, Planta…);
- los **310 objetos**, por categoría (Poké Balls, Medicinas, Bayas, Objetos
  equipados, MT, MO, Objetos clave…), y cada MT dice qué enseña:
  *MT26 — Terremoto*;
- los **151 Pokémon** de Kanto, por número de Pokédex.

Cada opción lleva su número interno al lado, que es el valor que se envía. Las
tablas están en `scripts/tablas/` — ver su README.

La **vista previa** de la derecha se recalcula con cada tecla y muestra las
estadísticas reales que tendrá el Pokémon en el juego, calculadas con
`frlgsim.stats.build_party_tail` — el mismo código que usa el simulador. Lo que
se ve ahí es byte a byte lo que se va a guardar: la **semilla** fija el PID, así
que con la misma semilla sale el mismo Pokémon. El botón 🎲 tira otra.

El fichero se escribe en `pk3/` sólo al pulsar *Generar*, y antes pasa por la
validación de siempre (checksum, ida y vuelta cifrar/descifrar, `frlgsim` lo
lee). Si ya existe uno con ese nombre, hay que marcar *Sobrescribir*.

## Caja

Todos los `.pk3`/`.ek3` del proyecto, analizados con `read_pk3.analizar`. Cada
ficha dice si el fichero es válido y permite marcarlo como **el que se entrega**
o como **relleno**, copiarlo al editor para hacer una variante, o borrarlo.

Sólo se pueden borrar ficheros dentro de `pk3/`, y nunca los de
`pk3/ejemplos/`, que están versionados en el repo.

## Intercambio

Antes de lanzar, la lista de comprobación mira lo que suele fallar: el vendor
preparado, el `prod.keys`, `sudo` sin contraseña, la radio suelta y los dos
`.pk3` elegidos.

El botón lanza:

```
sudo -n vendor/frlg-ldn-trade/venv/bin/python -u frlgtrade.py --live --verbose \
    --version firered --ot EMU --phy phy0 --trades 1 \
    --keys /home/USUARIO/.switch/prod.keys \
    -o pk3/recibido/recibido-FECHA.pk3 RELLENO ENTREGA
```

Dos detalles heredados del runbook: `--keys` va con la ruta completa porque
bajo `sudo` el `~` es el de root, y `-u` quita el búfer de Python para que el
registro se vea en vivo y no a trompicones.

El registro aparece en pantalla y se guarda en
`salidas/intercambio-FECHA-HORA.txt`. El Pokémon recibido va a
`pk3/recibido/recibido-FECHA-HORA.pk3`, **con la misma marca de tiempo que su
registro**: los dos llevan la fecha en el nombre para poder comparar un intento
con el anterior en vez de machacarlo. Con un nombre fijo no era teórico — el
2026-09-02 el segundo intercambio se llevó por delante al Pokémon del primero.
Si quieres decidir tú el nombre, escríbelo en «Recibido en»; vacío es
automático.

Al guardarlo, la GUI **censura la MAC del PC, la de la Switch y el SSID** de la
sesión (`ssid=SSID-CENSURADO us=…/MAC-PC-CENSURADA`). El resto —tiempos, IPs
`169.254.x`, estado de Pia, contenido de los `.pk3`— queda intacto, que es lo
que sirve para depurar. Así el registro se puede subir al repo sin pensarlo;
acordarse a mano costó una reescritura del historial el 2026-09-02. Si de
verdad necesitas los identificadores, `python3 scripts/gui.py --sin-censura`
—y entonces no subas ese registro. *Parar* manda `SIGINT`
al grupo de procesos entero: matar sólo al `sudo` dejaría vivo al Python de
dentro, con la radio cogida.

Cuando termina, si ha llegado algo, la ficha del Pokémon recibido sale sola.
El fichero se devuelve a tu usuario (lo escribe root).

## Sistema

El estado del equipo y **el poder**: soltar y devolver la radio, y apagar o
reiniciar.

- **Opción A — soltar la Wi-Fi** (`nmcli device set DEV managed no`): con cable
  Ethernet conservas Internet durante el intercambio.
- **Opción B — parar NetworkManager**: a lo bruto, si la A no basta.
- **Apagar / Reiniciar** llaman a `scripts/apagar.sh`, que sincroniza los discos
  antes y se salta la pantalla de «retira el medio de instalación». Apagar un
  live USB a lo bruto se come la persistencia del pendrive.

---

## Cosas que conviene saber

| Situación | Qué pasa |
|---|---|
| `sudo` pide contraseña | Los botones con `sudo -n` fallan en vez de colgarse esperando. Lanza la GUI con `sudo python3 scripts/gui.py`. |
| La GUI corre como root | Los `.pk3` que escriba se devuelven a tu usuario con `chown`. |
| Otro puerto | `python3 scripts/gui.py --puerto 9000` |
| Sin navegador automático | `--sin-navegador` |
| Ver cada petición HTTP | `--verboso` |
| Registro con las MAC sin tapar | `--sin-censura` (no lo subas al repo) |
