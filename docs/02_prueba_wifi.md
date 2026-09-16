# 02 — Probar si la Wi-Fi sirve para LDN

Este es **el paso que decide si el proyecto es viable** con el hardware actual.
Hazlo antes que nada: antes de las `prod.keys`, antes de los `.pk3`, antes de
clonar nada.

## Ejecutar

En Ubuntu, terminal (`Ctrl+Alt+T`):

```bash
bash scripts/check_wifi.sh
```

No necesita `sudo`. Tarda un par de segundos.

---

## Qué está mirando

`kinnay/LDN` no usa la Wi-Fi como un cliente normal: manipula frames 802.11 en
crudo. Eso exige cosas del driver que muchas tarjetas no dan aunque naveguen
por Internet perfectamente.

| Comprobación | Por qué importa |
|---|---|
| **Modo monitor** | Sin él la librería no puede recibir los frames de LDN. Bloqueo absoluto. |
| **Modo AP** | Necesario para emitir beacons / hostear la red. |
| **Combinaciones de interfaces** | Si `monitor` no puede coexistir con `managed`, hay conflictos. Si aparece como *software interface mode*, se puede añadir siempre: buena señal. |
| **Canales 1 / 6 / 11 en 2.4 GHz** | LDN vive ahí. Si salen como `no IR` o `disabled`, la radio no puede iniciar transmisión y no sirve. |
| **`rfkill`** | Un bloqueo por software o por el interruptor físico deja la radio muerta. |
| **Python 3.12+** | Requisito de `frlg-ldn-trade`. |
| **NetworkManager** | Mientras esté controlando la tarjeta, LDN no puede. |

---

## Interpretar el veredicto

- **`NO VIABLE`** — hay un bloqueo real. Según el blueprint (sección 17):
  no perder tiempo peleándose con drivers. Ir al fallback conocido,
  **ALFA AWUS036ACHM**, que el autor de `frlg-ldn-trade` usó en su demo.

- **`POSIBLEMENTE VIABLE`** — nada bloquea, pero hay dudas. Es el resultado
  esperable con la RTL8852BE. Merece la pena intentar la conexión real.

- **`BUENA PINTA`** — todo declarado correctamente.

**Ninguno de los tres es una respuesta definitiva.** Que `iw` declare `monitor`
no garantiza que el driver soporte **inyección** de frames, que es lo que LDN
necesita de verdad. La única prueba concluyente es que aparezca **`EMU`** en la
pantalla de la Switch.

---

## Riesgo conocido de la RTL8852BE

El driver `rtw89` es relativamente joven comparado con `ath9k_htc`, `mt76` o
`rtw88`, que son los que la comunidad de herramientas 802.11 tiene más
rodados. La RTL8852BE **no aparece** entre las tarjetas que el autor de
`frlg-ldn-trade` probó (ver blueprint, sección 8).

Así que hay dos escenarios y conviene tener asumido el segundo:

```
RTL8852BE funciona   ->  perfecto, ahorro de dinero
RTL8852BE no funciona ->  ALFA AWUS036ACHM (~30-40 EUR)
                          + ventaja: Wi-Fi interna para Internet,
                            USB dedicada a LDN, sin pelearse con
                            NetworkManager
```

No compres nada hasta haber ejecutado el script.

---

## Guardar el resultado

Para no perderlo si se reinicia el Live USB:

```bash
bash scripts/check_wifi.sh 2>&1 | tee docs/resultado_wifi.txt
```

Y anótalo en [`ESTADO.md`](ESTADO.md).
