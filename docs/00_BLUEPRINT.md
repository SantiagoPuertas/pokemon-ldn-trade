# BLUEPRINT — Intercambio Pokémon Rojo Fuego oficial de Switch ↔ PC mediante LDN

## 1. Objetivo del proyecto

Quiero conseguir que un ordenador se conecte por comunicación inalámbrica local a **Pokémon Rojo Fuego oficial para Nintendo Switch**, descargado de Nintendo eShop, y que el juego de Switch vea al ordenador como otro participante válido.

Objetivo final:

```text
PC
│
├── elegir/generar Pokémon
│   ├── especie
│   ├── nivel
│   ├── naturaleza
│   ├── shiny
│   ├── IV/EV
│   ├── movimientos
│   └── objeto
│
├── crear/cargar Pokémon Gen III (.pk3/.ek3)
│
├── simulador de intercambio FireRed/LeafGreen
│
├── protocolo Nintendo Pia
│
├── Nintendo Switch LDN
│
└── Wi-Fi
     │
     ▼
Nintendo Switch
Pokémon Rojo Fuego oficial
│
└── Centro Pokémon / Direct Corner
     │
     └── intercambio real dentro del juego
```

La intención NO es modificar directamente el save de la Switch.

La idea es realizar un **intercambio legítimo desde el punto de vista del juego**, haciendo que el PC simule al segundo jugador.

---

# 2. Descubrimiento principal

Ya existe un proyecto que hace prácticamente exactamente esto:

**Repositorio: `tornadus/frlg-ldn-trade`**

Es una prueba de concepto que permite que un PC se comunique mediante LDN con Pokémon FireRed/LeafGreen ejecutándose en una **Switch/Switch 2 real**.

Tiene actualmente:

- intercambio extremo a extremo con una consola real;
- entrada `.pk3/.ek3`;
- salida `.pk3`;
- simulación del segundo jugador;
- comunicación Nintendo LDN;
- comunicación Pia;
- simulación del protocolo RFU / Gen III;
- posibilidad de hacer de 1 a 6 intercambios consecutivos.

El programa aparece ante el jugador de Switch como:

```text
EMU
```

El proyecto confirma explícitamente que puede realizar intercambios completos contra un juego real ejecutándose en Switch.

**Conclusión importante: NO hace falta implementar el protocolo completo desde cero.**

El proyecto futuro debería construirse encima de `frlg-ldn-trade`.

---

# 3. Por qué esto funciona con la versión oficial de Switch

Nintendo confirma que Pokémon FireRed/LeafGreen para Switch conserva las funciones de comunicación de los juegos originales.

En GBA se utilizaban:

```text
Game Boy Advance Link Cable
o
Game Boy Advance Wireless Adapter
```

En Switch esas funciones se transportan mediante:

```text
Nintendo Switch Local Wireless
            ↓
           LDN
```

Nintendo indica además que los intercambios y combates funcionan localmente y que la Sala Unión puede conectar hasta cinco jugadores en total.

No utiliza Nintendo Switch Online para realizar esos intercambios.

---

# 4. Arquitectura descubierta

El stack aproximado utilizado por `frlg-ldn-trade` es:

```text
Pokémon FireRed/LeafGreen
            │
            │ lógica Gen III
            ▼
       protocolo RFU
            │
       frames GBA
            │
       Nintendo Pia
            │
      Reliable protocol
            │
         AES-GCM
            │
           UDP
            │
           LDN
            │
         802.11
            │
          Wi-Fi
```

En el lado PC el proyecto simula concretamente al jugador secundario/follower de FireRed.

Internamente utiliza aproximadamente:

```text
RFU command slot
      ↓
GBA emulator frame
      ↓
Pia Reliable
      ↓
Pia message
      ↓
compresión opcional
      ↓
AES-GCM
      ↓
UDP
      ↓
LDN
```

El propio código del proyecto documenta este stack y la máquina de estados del intercambio.

---

# 5. Librería LDN utilizada

El proyecto anterior está construido sobre:

**Repositorio: `kinnay/LDN`**

Es una librería Python para comunicación inalámbrica local con Nintendo Switch.

Puede:

```text
buscar redes LDN
unirse a una red LDN
crear una red LDN
comunicarse con Switch reales
```

LDN es el protocolo que Nintendo Switch utiliza normalmente para multijugador local.

La consola anfitriona genera una red inalámbrica especial/oculta y anuncia la sesión mediante frames 802.11 específicos.

Una vez establecida la conexión, los participantes pueden comunicarse mediante una red IP/UDP.

---

# 6. Sistema operativo necesario

Mi ordenador normalmente utiliza:

```text
Windows
```

Pero `kinnay/LDN` requiere:

```text
Linux
Python 3.12+
```

porque necesita acceso de bajo nivel al hardware Wi-Fi mediante las interfaces Linux correspondientes.

Por tanto NO hace falta borrar Windows ni instalar Linux permanentemente.

Plan recomendado:

```text
Windows
   │
   ├── crear USB arrancable de Ubuntu
   │
   └── reiniciar
          ↓
    "Probar Ubuntu"
          ↓
     Ubuntu Live
          ↓
    ejecutar proyecto
```

Se puede utilizar Ubuntu desde un pendrive sin modificar inicialmente la instalación de Windows.

Ubuntu 24.04 o una versión actual que incluya Python 3.12+ sería una opción razonable.

---

# 7. Hardware Wi-Fi encontrado en mi portátil

En Windows, Administrador de dispositivos muestra:

```text
Bluetooth Device

Realtek PCIe GbE Family Controller

Realtek RTL8852BE
WiFi 6 802.11ax PCIe Adapter
```

La tarjeta que importa es:

```text
Realtek RTL8852BE
```

Es una tarjeta Wi-Fi interna PCIe.

Linux tiene soporte en el kernel para RTL8852BE mediante:

```text
rtw89_8852be
```

El soporte del chipset está presente en el driver `rtw89` del kernel Linux.

IMPORTANTE:

**Todavía NO sabemos si esta RTL8852BE funcionará correctamente con LDN.**

No aparece entre las tarjetas probadas oficialmente por `frlg-ldn-trade`.

LDN necesita que el hardware/driver pueda realizar las operaciones 802.11 que necesita el proyecto, incluyendo transmisión/recepción de frames utilizados por LDN.

Por tanto el estado es:

```text
RTL8852BE
driver Linux:       SÍ
LDN confirmado:     NO
pendiente de prueba
```

NO comprar ningún adaptador todavía.

Primero probar la tarjeta interna.

---

# 8. Tarjetas Wi-Fi que el desarrollador sí ha probado

Según `frlg-ldn-trade`:

```text
AMD RZ616 / mt7921e
→ funciona
→ fiabilidad baja

ALFA AWUS036ACHM / mt76x0u
→ funciona
→ fiabilidad alta

Realtek RTL8821CE / rtw88_8821ce
→ funciona
→ fiabilidad alta

Intel AX200 / iwlwifi
→ problemática
→ no consigue asignación IP

Atheros AR9271 / ath9k_htc
→ problemática
→ suele fallar al asignar IP
```



Si la RTL8852BE interna falla, la opción de referencia sería:

```text
ALFA AWUS036ACHM
```

porque el propio creador de `frlg-ldn-trade` la utilizó para su demostración y la clasifica con fiabilidad alta.

---

# 9. Primera fase — preparar Ubuntu Live USB

Desde Windows:

```text
1. Descargar una ISO actual de Ubuntu.
2. Crear un pendrive USB arrancable.
3. Reiniciar el portátil.
4. Abrir el Boot Menu del ordenador.
5. Arrancar desde USB.
6. Elegir "Try Ubuntu / Probar Ubuntu".
```

No instalar Ubuntu todavía.

La primera meta es simplemente comprobar:

```text
Ubuntu
  ↓
detecta RTL8852BE
  ↓
driver correcto
  ↓
capacidades Wi-Fi apropiadas
```

---

# 10. Primera prueba en Ubuntu

Abrir Terminal.

Identificar tarjeta y driver:

```bash
lspci -k | grep -A 4 -i network
```

Esperamos algo parecido a:

```text
Realtek Semiconductor ...
RTL8852BE

Kernel driver in use:
rtw89_8852be
```

Después:

```bash
iw list
```

Hay que estudiar especialmente:

```text
Supported interface modes
```

y las capacidades relacionadas con monitor/AP y combinaciones de interfaces.

También:

```bash
iw dev
```

para conocer el nombre de la interfaz, probablemente algo como:

```text
wlp2s0
```

La prueba definitiva NO será simplemente que aparezca la palabra `monitor`.

La prueba definitiva será conseguir realmente:

```text
PC
 ↓
LDN
 ↓
detectar sesión FireRed
 ↓
unirse
 ↓
recibir IP
 ↓
comunicar con Switch
```

---

# 11. Preparar `frlg-ldn-trade`

Repositorio principal:

```text
tornadus/frlg-ldn-trade
```

Requisitos publicados actualmente:

```text
Linux
Python 3.12+
virtualenv / venv
requirements.txt
Wi-Fi compatible
Switch o Switch 2
FireRed/LeafGreen
Direct Corner desbloqueado
mínimo 2 archivos .pk3/.ek3
prod.keys
root
```



Proceso general:

```bash
sudo apt update

sudo apt install git python3 python3-venv python3-pip iw
```

Después clonar:

```text
tornadus/frlg-ldn-trade
```

Entrar al directorio:

```bash
cd frlg-ldn-trade
```

Crear entorno:

```bash
python3 -m venv venv
```

Instalar dependencias:

```bash
./venv/bin/pip install -r requirements.txt
```

---

# 12. `prod.keys`

El proyecto requiere actualmente:

```text
~/.switch/prod.keys
```

o especificar otro fichero mediante:

```text
--keys
```

Estas claves forman parte de los requisitos de la comunicación LDN utilizada por el proyecto.

Usar únicamente claves obtenidas legítimamente de hardware/software propio.

No descargar `prod.keys` aleatorias de Internet.

La obtención/configuración concreta de las claves queda como tarea separada para una siguiente sesión.

---

# 13. NetworkManager

La librería LDN necesita controlar directamente la interfaz inalámbrica.

El proyecto recomienda que la tarjeta utilizada para LDN no esté siendo controlada por NetworkManager.

Antes de usarla puede ser necesario:

```bash
sudo systemctl stop NetworkManager
```

o:

```bash
sudo service NetworkManager stop
```

Cuando se termine:

```bash
sudo systemctl start NetworkManager
```

o equivalente.

Esto puede dejar temporalmente el portátil sin Internet si la misma tarjeta Wi-Fi estaba dando conexión.

La propia librería LDN advierte de este comportamiento.

Por eso una configuración futura cómoda podría ser:

```text
Ethernet/internet
       +
Wi-Fi dedicado a LDN
```

o:

```text
Wi-Fi interno → Internet

Wi-Fi USB → Nintendo LDN
```

Pero para la primera prueba usaremos únicamente la RTL8852BE.

---

# 14. Preparación de Pokémon

`frlg-ldn-trade` acepta:

```text
.pk3
.ek3
```

Los `.pk3` son compatibles con el formato utilizado por herramientas como PKHeX.

Necesitamos como mínimo dos Pokémon simulados para la party del jugador PC.

Ejemplo conceptual:

```text
dummy.pk3
mew.pk3
```

El segundo sería el Pokémon que queremos intercambiar a la Switch.

Primera prueba: NO implementar todavía un generador propio.

Utilizar simplemente archivos `.pk3` ya preparados/correctos.

Cuando el intercambio básico funcione, entonces desarrollar el generador.

---

# 15. Primer intercambio real

En Switch:

```text
Pokémon Rojo Fuego
      ↓
Centro Pokémon
      ↓
Direct Corner
      ↓
Trade Center
      ↓
crear la sesión como LEADER
```

Después en PC ejecutar aproximadamente:

```bash
sudo -E ./venv/bin/python frlgtrade.py --live \
    -o recibido.pk3 \
    dummy.pk3 \
    pokemon_a_enviar.pk3
```

El script intentará conectarse mediante LDN.

En Switch debería aparecer un jugador:

```text
EMU
```

Aceptar su entrada.

Después:

```text
Switch:
entrar a la sala

↓
caminar hacia la SILLA IZQUIERDA

↓
seleccionar el Pokémon que quiero entregar

↓
aceptar intercambio
```

El PC simula al otro participante.

La Switch debería recibir:

```text
pokemon_a_enviar.pk3
```

El Pokémon enviado desde Switch quedará guardado en PC como:

```text
recibido.pk3
```

El README actual indica que puede necesitarse más de un intento para conectar dependiendo del hardware Wi-Fi.

---

# 16. Criterio de éxito del MVP

El primer objetivo NO es hacer todavía una aplicación bonita.

Éxito fase 1:

```text
Switch crea sesión
        ↓
PC encuentra sesión LDN
        ↓
PC se conecta
        ↓
Switch muestra "EMU"
```

Éxito fase 2:

```text
EMU entra
 ↓
se abre Trade Center
 ↓
intercambio finaliza correctamente
```

Éxito fase 3:

```text
Switch recibe Pokémon .pk3 elegido
        +
PC guarda Pokémon recibido
```

En ese momento estaría resuelta prácticamente toda la parte difícil.

---

# 17. Si la RTL8852BE NO funciona

No perder mucho tiempo modificando drivers sin antes probar una tarjeta conocida.

Fallback recomendado:

```text
ALFA AWUS036ACHM
```

Arquitectura:

```text
Portátil
│
├── RTL8852BE
│      └── Internet
│
└── ALFA AWUS036ACHM
       └── LDN
            ↓
          Switch
```

El script permite seleccionar explícitamente una radio Wi-Fi mediante opciones como:

```text
--phy phy1
```



---

# 18. Fase siguiente — convertirlo en un "Pokémon dispenser"

Una vez demostrado el intercambio, NO reimplementar LDN.

Construir encima de:

```text
frlg-ldn-trade
```

Objetivo:

```text
┌────────────────────────────┐
│ Pokémon Trade Bot          │
│                            │
│ Pokémon: Mew               │
│ Nivel: 5                   │
│ Naturaleza: Modesta        │
│ Shiny: Sí / No             │
│ IVs                        │
│ EVs                        │
│ Movimientos                │
│ Objeto                     │
│                            │
│ [ Intercambiar ]           │
└─────────────┬──────────────┘
              │
            .pk3
              │
        frlg-ldn-trade
              │
             LDN
              │
          Nintendo Switch
```

---

# 19. Desarrollo futuro del programa

Orden recomendado:

```text
FASE A
Hacer funcionar frlg-ldn-trade sin modificar.

FASE B
Intercambiar un .pk3 preparado manualmente.

FASE C
Crear generador programático de Pokémon Gen III.

FASE D
Automatizar generación del .pk3 y lanzamiento de frlgtrade.py.

FASE E
Crear una interfaz gráfica.

FASE F
Añadir biblioteca de Pokémon / presets.

FASE G
Permitir varios intercambios consecutivos.

FASE H
Opcional: validación de legalidad/compatibilidad.

FASE I
Opcional: automatizar aún más el flujo del jugador simulado.
```

---

# 20. El generador de Pokémon NO debe modificar el protocolo LDN

Separar claramente:

```text
CAPA 1
Generación Pokémon

create_mon(...)
 ↓
pokemon.pk3
```

```text
CAPA 2
Intercambio FireRed

frlg-ldn-trade
```

```text
CAPA 3
Networking Nintendo

Pia + LDN
```

Así cualquier fallo se puede aislar.

Por ejemplo:

```text
¿.pk3 incorrecto?
→ problema del generador

¿EMU no aparece?
→ problema LDN/Wi-Fi

¿EMU aparece pero no entra?
→ Pia / protocolo

¿entra pero intercambio falla?
→ estado RFU/trade

¿todo funciona manualmente?
→ problema solamente de la GUI/automatización
```

---

# 21. Repositorios importantes

### Principal

```text
tornadus/frlg-ldn-trade
```

Es el proyecto que debemos probar primero.

### LDN

```text
kinnay/LDN
```

Implementación Python del protocolo local inalámbrico de Nintendo Switch.

### Documentación

```text
kinnay/NintendoClients Wiki
```

Especialmente:

```text
LDN Protocol
Local Wireless Communication on PC
Pia Overview
```

---

# 22. Información conocida actualmente

```text
CONSOLA:
Nintendo Switch
sin necesidad de modificar el juego para este proyecto

JUEGO:
Pokémon Rojo Fuego oficial de Switch

MODO:
comunicación local inalámbrica

PROTOCOLO:
Nintendo LDN + Pia

PC:
portátil Windows

LINUX:
usar inicialmente Ubuntu Live USB

WIFI:
Realtek RTL8852BE WiFi 6 PCIe

DRIVER LINUX:
rtw89_8852be

COMPATIBILIDAD LDN RTL8852BE:
PENDIENTE DE PROBAR

PROYECTO:
tornadus/frlg-ldn-trade

LIBRERÍA:
kinnay/LDN

FORMATO POKÉMON:
.pk3 / .ek3

OBJETIVO INMEDIATO:
conseguir que "EMU" aparezca en la Switch
```

---

# 23. Próxima acción exacta

La próxima sesión debería empezar por:

```text
1. Crear Ubuntu Live USB.

2. Arrancar "Probar Ubuntu".

3. Ejecutar:

   lspci -k | grep -A 4 -i network

4. Ejecutar:

   iw list

5. Ejecutar:

   iw dev

6. Confirmar que aparece RTL8852BE /
   rtw89_8852be.

7. Preparar tornadus/frlg-ldn-trade.

8. Preparar dependencias Python.

9. Resolver/configurar prod.keys propias.

10. Probar primero detección/conexión LDN.

11. Intentar que aparezca "EMU".

12. Hacer primer intercambio .pk3.
```

NO empezar desarrollando una GUI ni un generador hasta completar el primer intercambio real.

---

# 24. Mensaje para continuar en una nueva sesión

Estoy continuando un proyecto para conectar un PC a Pokémon Rojo Fuego oficial de Nintendo Switch mediante comunicación local LDN y realizar intercambios de Pokémon.

Ya hemos descubierto que existe `tornadus/frlg-ldn-trade`, que realiza intercambios end-to-end con FireRed/LeafGreen real en Switch mediante LDN y archivos `.pk3/.ek3`. Está basado en `kinnay/LDN`.

Mi portátil tiene una tarjeta Wi-Fi interna **Realtek RTL8852BE WiFi 6 PCIe**, que Linux soporta mediante `rtw89_8852be`, pero todavía NO hemos confirmado que funcione correctamente con LDN.

Quiero utilizar inicialmente **Ubuntu desde un Live USB**, sin borrar Windows ni instalar Linux permanentemente.

El objetivo inmediato es probar la RTL8852BE y conseguir que `frlg-ldn-trade` se conecte al Rojo Fuego de Switch y que en la consola aparezca el jugador `EMU`.

Después quiero hacer un intercambio real usando `.pk3`.

Una vez eso funcione, el objetivo final es crear una aplicación de PC tipo "Pokémon dispenser" donde pueda elegir/generar un Pokémon y enviarlo automáticamente a la Switch mediante un intercambio dentro del juego.

Continuar a partir de la creación del Ubuntu Live USB y las pruebas de la RTL8852BE. No volver a investigar desde cero salvo que sea necesario verificar algún detalle actualizado.