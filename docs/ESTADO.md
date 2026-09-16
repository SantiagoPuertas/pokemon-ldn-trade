______________________________
next step desde sesion claude:

**HITO ALCANZADO (2026-09-01): primer intercambio real completado.** Fase A cerrada
y Fase B esencialmente hecha. Ya no hay "next step" de arranque; ver más abajo lo
que queda (guardar el recibido con nombre propio, y decidir si se pasa a Fase C).

Lo que faltaba era `master_key_12`: la sesión LDN de la Switch va por protocolo v3
(advertisement AES-GCM) y sin esa clave el scan no descifraba nada ("saw 0"). Añadida
a `~/.switch/prod.keys` (constante común de retail), el intercambio
funcionó al 2º intento.

______________________________________

# ESTADO — bitácora del proyecto

Checklist vivo. Se actualiza a mano según se avanza.
Última actualización: **2026-09-02** — *Fase C: la GUI ya intercambia de verdad*

---

## Riesgos que pueden matar el proyecto

Se identificaron dos. **Los dos están descartados.** Ninguno bloquea ya.

| # | Riesgo | Estado | Cómo se resuelve |
|---|---|---|---|
| 1 | La **RTL8852BE** puede no servir para LDN (driver `rtw89`, no probado por el autor) | ✅ **descartado** — inyecta | `check_wifi.sh` + `check_injection.sh`, ambos superados |
| 2 | Sin `prod.keys` no hay comunicación LDN | ✅ **descartado** | Ver `03_prod_keys.md` |

### Riesgo 2 — descartado (2026-09-01)

Primero se dio por bloqueado porque la consola es **HAC-001(-01)** (Mariko, sin
RCM explotable). **Esa conclusión era incorrecta** y se corrigió leyendo el
código.

`ldn.load_keys()` sólo necesita tres valores: `aes_kek_generation_source`,
`aes_key_generation_source` y un master key (`master_key_00` para el protocolo
LDN v1, `master_key_12` para el v3). **Los tres son claves comunes a todas las
consolas de retail**, no únicas del aparato. No identifican tu consola ni salen
de ella.

Por tanto el modelo de consola **no importa** para este proyecto, y un modchip
no aportaría nada: volcaría exactamente las mismas constantes que tiene
cualquier otra unidad. Queda pendiente conseguir el fichero, que es un problema
distinto y mucho menor. Detalle y trazabilidad en `03_prod_keys.md`.

### Riesgo 1 — descartado (2026-09-01)

La RTL8852BE **inyecta**. Detalle en "Resultados de las pruebas".

**Ya no queda ningún riesgo de nivel proyecto identificado.** Lo que falta es
trabajo: conseguir el `prod.keys`, dos `.pk3` y montar `frlg-ldn-trade`.

---

## FASE A — hacer funcionar `frlg-ldn-trade` sin modificar

- [x] Blueprint técnico escrito → `00_BLUEPRINT.md`
- [x] Repo inicializado y enlazado a GitHub
- [x] Script de diagnóstico Wi-Fi → `scripts/check_wifi.sh`
- [x] Script de preparación → `scripts/setup_ubuntu.sh`
- [x] Descargar Ubuntu 26.04.1 LTS + Rufus 4.15 portable → `~/Downloads`
- [x] Verificar SHA256 de la ISO → `601e30fb…f1bda1f`, **correcto**
- [x] **Live USB grabado** — SanDisk Ultra 57,3 GB, GPT: 37,3 GB FAT32 + 20 GB ext3
      de persistencia. Rufus usó el "método tipo Ubuntu" para la persistencia.
      Aviso del log: `bootx64.efi` va firmado por *Microsoft UEFI CA 2011*; si
      falla el arranque, activar "Microsoft 3rd-party UEFI CA" en la BIOS
      antes de desactivar Secure Boot.
- [x] **Arrancado desde el USB** — Ubuntu 26.04.1 en vivo, sin tocar Windows
- [x] Ejecutado `check_wifi.sh` → sin bloqueos
- [x] **Ejecutar `check_injection.sh`** → **la tarjeta inyecta**, no hay que comprar nada
- [x] Averiguar qué claves hace falta de verdad → 3 constantes comunes, no un volcado
- [x] Conseguir un `prod.keys` → **4 claves**: las 3 comunes + `master_key_12`
      (la sesión negoció **v3**, ver «Conexión LDN real»)
- [x] Clonar y preparar `frlg-ldn-trade` → `setup_ubuntu.sh`, salida en `salidas/setup.txt`
- [x] Conseguir al menos 2 archivos `.pk3` → `pk3/ejemplos/`, generados con
      `scripts/make_pk3.py` y validados con el propio parser del proyecto
- [x] **`EMU` aparece y se sienta en la Switch** ✅ ← hito de la fase A, **logrado**

## FASE B — primer intercambio

- [x] Entrar al Trade Center con el jugador simulado ✅
- [x] Completar un intercambio de un `.pk3` preparado a mano ✅ (2026-09-01)
- [x] Guardar el Pokémon recibido en `recibido.pk3` ✅ CATERPIE, checksum OK

## FASE C en adelante

**Desbloqueadas: la Fase B ya ha funcionado.** Ver secciones 18–20 del blueprint.
Generador de `.pk3`, automatización, GUI, biblioteca de presets.

### En marcha (2026-09-01): generar → intercambiar, end-to-end ✅

El flujo completo *«definir un Pokémon a medida → generarlo → intercambiarlo a la
Switch»* funciona. Ya no hay incógnitas de protocolo; a partir de aquí es código.

- [x] `scripts/make_pk3.py` genera `.pk3` a medida (especie, nivel, naturaleza,
      IVs/EVs, movimientos, objeto, shiny) y los valida con `frlgsim.mon.Mon`.
- [x] **Legendario entregado**: Mew (#151) lv30 con Hiperrayo/Llamarada/
      Ventisca/Trueno y Pepita; requirio `modernFatefulEncounter` (ver nota).
      Recibido de vuelta Metapod (#11). Enlace al 1er intento.
- [x] **Primer Pokémon generado y entregado en la partida**: Venusaur (#3) lv50,
      Modesta, **shiny**, objeto **Repartir Exp** (ID 182), movimientos
      Rayo Solar/Bomba Lodo/Somnífero/Drenadoras (76/188/79/73). Intercambio real
      OK (enganchó al 3er intento); recibido de vuelta Kakuna (#14). El objeto
      viaja con el Pokémon en el trade.

Notas para el futuro generador/GUI:
- **Tablas de objetos y movimientos** ya incrustadas en `scripts/tablas/`
  (autogeneradas de `pokefirered`: EN↔ID completo + alias ES curados). `make_pk3.py`
  acepta `--objeto` y `--movimientos` por nombre (EN o ES), y `read_pk3.py` los
  muestra con nombre. Ej.: `--objeto pepita --movimientos "hiperrayo,llamarada"`.
- El generador fuerza un PID que cumpla shiny **y** naturaleza a la vez; por eso
  el PID/OT-ID cambian al pedir shiny. Coherente y con checksum válido.
- **Legendarios (Mew/Deoxys) necesitan `modernFatefulEncounter`.** FRLG rechaza
  un Mew/Deoxys sin ese bit al intercambiar ("el otro entrenador no ha podido
  enviar su Pokemon"). `make_pk3.py` ya lo pone automatico para 151/410
  (flag `--fateful/--no-fateful`); `read_pk3.py` lo muestra y avisa si falta.
- Falta por decidir: **legalidad** (movimientos aprendibles por nivel/TM, EVs
  legales, etc.). Ahora mismo el generador no la comprueba.

Pendiente Fase C: automatización y biblioteca de presets.

### GUI (2026-09-02): `scripts/gui.py`

Interfaz gráfica para todo el flujo: crear Pokémon (características, objeto,
movimientos, IVs/EVs, shiny, fateful) con vista previa de las estadísticas
reales, caja de `.pk3`, lanzamiento del intercambio con el registro en vivo, y
control de la radio y del apagado. Documentada en `05_gui.md`.

Decisiones:

- **Página web local en vez de ventana de escritorio.** No hay `tkinter` en
  este Ubuntu live y no compensa gastar persistencia en instalarlo; con
  `http.server` no se instala nada. Además sigue funcionando por `127.0.0.1`
  cuando el intercambio deja el equipo sin Internet.
- **Escucha sólo en local.** Hay botones que ejecutan `sudo`.
- **No reimplementa nada.** Crear es `make_pk3`, leer es `read_pk3`,
  intercambiar es `frlgtrade.py` con los argumentos del runbook. Para no tener
  dos versiones del mismo informe, la lectura de un `.pk3` se movió a
  `read_pk3.analizar()`, que devuelve un dict y no imprime; la salida de
  consola es byte a byte la de antes.
- **Registro con fecha en el nombre** (`salidas/intercambio-FECHA.txt`) en vez
  de machacar `intercambio.txt`: comparar intentos es justo lo que hace falta
  cuando el enganche falla y hay que repetir.
- *Parar* manda `SIGINT` al grupo de procesos: matar sólo al `sudo` dejaría
  vivo al Python de dentro con la radio cogida.

#### Desplegables con todo el juego (2026-09-02)

Objetos, movimientos y especies se eligen en desplegables, no escribiendo el
nombre. Para eso hacía falta el **nombre en español de los 310 objetos y los
354 movimientos**, que antes sólo estaba para un centenar de casos comunes
(`ALIAS_ES`, curado a mano).

Se sacan de PokeAPI con `scripts/tablas/generar_nombres_es.py`. Lo que hace
que sea fiable y no un emparejamiento a ojo: **PokeAPI publica el `game_index`
de la 3ª generación de cada objeto, que es el índice interno de FireRed**; y en
movimientos el id nacional 1..354 ya coincide con el índice interno. Los ids
siguen viniendo de la decompilación, que es la fuente autoritativa; PokeAPI sólo
pone los nombres, el tipo de cada movimiento (para agrupar) y qué enseña cada MT.

Dos cosas que salieron de comprobarlo contra la fuente en vez de fiarse de la
memoria:

- El alias curado decía que **«Cabezazo» era Headbutt. Es Skull Bash** (130);
  Headbutt es «Golpe Cabeza» (29). Corregido.
- PokeAPI cuelga dos objetos del índice 261 y gana la Llave Sótano; en FireRed
  el 261 es el **Buscaobjetos**. Se fuerza a mano en el generador.

#### Estrenada: dos intercambios reales desde la ventana (2026-09-02) ✅

| Hora | Entregado | Recibido | Registro |
|---|---|---|---|
| 08:51 | **Jolteon** (#135) lv40 shiny, Fuerte, IV 31×6, Rayo/Onda Trueno/Mordisco/Poder Oculto, **Repartir Exp** | Rattata lv5 | `salidas/intercambio-20260902-085146.txt` |
| 09:05 | **Gengar** (#94) lv40 shiny, Fuerte, IV 31×6, Rayo/Psíquico/Puño Hielo/Bola Sombra, **Huevo Suerte** | Spearow lv7 | `salidas/intercambio-20260902-090550.txt` |

Los dos **engancharon al primer intento** (Pia establecido a los 3,2 s y 5,0 s;
ningún `Failed` en los registros), y el ciclo entero —crear en la pestaña Crear,
elegir en la Caja, lanzar y ver el registro— funcionó sin tocar la consola.

Una pega vista al revisarlo, **ya corregida**: la salida por defecto era
siempre `pk3/recibido.pk3`, así que el segundo intercambio **machacó el Rattata
del primero** (sólo queda en su registro). Ahora el recibido va a
`pk3/recibido/recibido-FECHA.pk3`, con la misma marca de tiempo que su registro,
y el campo «Recibido en» de la ventana sólo hace falta si se quiere otro nombre.

---

## Resultados de las pruebas

### Wi-Fi (RTL8852BE) — 2026-09-01, Ubuntu 26.04.1 live

Kernel 7.0.0-30-generic, Python 3.14, `rtw89_8852be` cargado, interfaz `wlp8s0`
(phy0). Portátil Lenovo, dominio regulatorio `ES: DFS-ETSI`.

| Comprobación | Resultado |
|---|---|
| Modo monitor | ✅ soportado |
| Modo AP | ✅ soportado |
| `monitor` como *software interface mode* | ✅ se puede añadir siempre |
| rfkill | ✅ ninguna radio bloqueada |
| Python 3.12+ | ✅ 3.14 |
| Canales 2,4 GHz | ✅ (el primer aviso fue un fallo del script, ya corregido) |

Combinaciones declaradas por el driver:

```
* #{ managed } <= 1, #{ AP, P2P-client, P2P-GO } <= 1, total <= 2, #channels <= 1
* #{ managed } <= 1, #{ P2P-client, P2P-GO } <= 1,     total <= 2, #channels <= 2
```

**Ningún bloqueo.** La tarjeta declara todo lo necesario. Queda sin resolver lo
único que `iw` no puede decir: si `rtw89` soporta **inyección de frames**.

#### Fallos del script detectados en esta primera ejecución

- Los `iw` recientes imprimen `2412.0 MHz` en vez de `2412 MHz`; la regex no
  contemplaba el decimal y daba un falso "no hay 2,4 GHz". Corregido.
- El listado de combinaciones arrastraba la sección siguiente
  (`HT Capability overrides`) por usar `grep -A 6`. Ahora corta en la
  siguiente cabecera. Cosmético.

### Inyección de frames — 2026-09-01

`sudo bash scripts/check_injection.sh` sobre `phy0` / `ldntest0`:

| Prueba | Resultado |
|---|---|
| Crear interfaz monitor | ✅ `ldntest0` creada y levantada |
| Fijar canales 1, 6 y 11 | ✅ los tres |
| `aireplay-ng --test` (canal 1) | ✅ **`Injection is working!`** — 23 AP encontrados |
| Calidad de la inyección | varios AP respondiendo 30/30 (100%), pings de 1-50 ms |
| Action frame crudo por `AF_PACKET` | ✅ aceptado por el camino de transmisión |

**Veredicto: LA TARJETA INYECTA.** No hace falta comprar la ALFA AWUS036ACHM.
La RTL8852BE interna con `rtw89_8852be` sirve, pese a no estar en la lista de
tarjetas probadas por `frlg-ldn-trade`.

La limpieza automática del script funcionó: interfaz eliminada y NetworkManager
rearrancado.

### Conexión LDN real — 2026-09-01 ✅ PRIMER INTERCAMBIO

Comando: `frlgtrade.py --live --verbose --version firered` con los dos `.pk3` de
`pk3/ejemplos/`. `prod.keys` con las 4 claves.

| Etapa | Resultado |
|---|---|
| Descifrado de la advertisement | ✅ `beacon decoded: host name='SANTI' TID=0xc16f tradeSpecies=16` |
| Scan ve la red | ✅ `comm_id=0x01006fa0233f8000 scene=22287 1/6` |
| Join LDN | ✅ al 2º intento (el 1º: `Failed to obtain IP address`, transitorio) |
| Handshake Pia/RFU/NI/LinkPlayer | ✅ `Pia connection ESTABLISHED`, EMU sentado (silla derecha) |
| Intercambio | ✅ enviado Bulbasaur, **recibido CATERPIE #10 OT='SANTI' lv3, checksum OK** |
| Salida | ✅ cancel → walk-out → link cerrado por el host, sin colgarse |

Recibido guardado en `pk3/recibido.pk3` y validado con `read_pk3.py`.

**La clave del desbloqueo fue `master_key_12`.** La sesión de la Switch negocia el
protocolo **LDN v3**, cuya advertisement va en **AES-GCM**; con sólo `master_key_00`
(v1, AES-CTR) el `decode` fallaba en todas las tramas y el scan devolvía `saw 0`
pese a que la radio SÍ recibía las tramas (se veían 3 `Failed to parse advertisement
frame`). Añadida `master_key_12` (constante común de retail),
descifra y conecta. Trazabilidad en `03_prod_keys.md`.

---

## Decisiones tomadas

### ¿Por qué Live USB y no una máquina virtual? (2026-09-01)

Porque una VM **no puede dar acceso a la Wi-Fi interna**. El hipervisor expone
una NIC virtual tipo Ethernet, sin radio 802.11: dentro de la VM `iw list` no
devuelve nada, y `kinnay/LDN` exige poder *"receive and transmit action frames
in monitor mode"*.

Passthrough de la RTL8852BE tampoco: es PCIe, necesitaría VT-d/IOMMU, y eso no
lo ofrecen VirtualBox ni VMware Workstation sobre host Windows. WSL2, igual.

Para responder a la pregunta abierta —*¿sirve la RTL8852BE?*— el arranque
nativo era la única vía.

**Matiz para más adelante:** si hay que comprar la **ALFA AWUS036ACHM**, al ser
USB sí admite passthrough en VirtualBox/VMware, y una VM sería más cómoda que
reiniciar. Reserva: LDN/Pia son sensibles a los tiempos y el passthrough USB
añade latencia, así que podría rendir peor que nativo. Habría que probarlo, con
el arranque nativo como plan B.

---

## Correcciones al blueprint

Cosas que se han visto al revisarlo. El blueprint original se deja intacto como
documento de diseño; las correcciones viven aquí.

- **§6 y §9 — Live USB sin persistencia.** El blueprint plantea "Probar Ubuntu"
  a secas. Eso pierde todo al reiniciar: repo, `venv`, dependencias, claves,
  `.pk3`. Con un pendrive de 61 GB conviene crearlo **con partición persistente**.
  Detallado en `01_ubuntu_live_usb.md`.

- **§1 — origen del juego.** El blueprint dice "descargado de Nintendo eShop".
  Es correcto: FireRed/LeafGreen en Switch se compran sueltos en la eShop y no
  requieren Nintendo Switch Online.

- **§12 — `prod.keys`.** El blueprint lo deja como "tarea para otra sesión" sin
  concretar. Leyendo el código resulta que sólo hacen falta **tres constantes
  comunes** a todas las consolas, no un volcado del propio aparato. Es bastante
  menos grave de lo que parecía, y el modelo de consola es irrelevante.
  Ver `03_prod_keys.md`.

- **§8 — tarjetas probadas.** El README actual de `frlg-ldn-trade` sólo lista
  tres adaptadores (AMD RZ616 / mt7921e, ALFA AWUS036ACHM / mt76x0u, Realtek
  RTL8821CE / rtw88_8821ce). Los casos "problemáticos" que cita el blueprint
  (Intel AX200, Atheros AR9271) no están en el README; vendrán de issues o
  discusiones. La recomendación de fallback no cambia.

- **§7 — estado de la RTL8852BE.** Sigue siendo correcto: driver sí,
  compatibilidad LDN sin confirmar. `check_wifi.sh` existe justo para cerrar
  esa duda rápido.
