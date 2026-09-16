# 03 — `prod.keys`

> **Revisado el 2026-09-01 leyendo el código fuente.** La conclusión anterior
> ("bloqueado porque la consola es Mariko") era **incorrecta**. El proyecto no
> necesita un volcado de *tu* consola. Detalle abajo.

---

## Qué necesita realmente el proyecto

Se puede seguir la cadena entera por el código, sin especular:

```
frlgtrade.py
    --keys  (por defecto ~/.switch/prod.keys)
        ↓
frlgsim/transport.py   →   LiveTransport(keys_path=...)
        ↓
        keys = ldn.load_keys(self.keys_path)
        param = ldn.ConnectNetworkParam(); param.keys = keys
        ↓
kinnay/LDN  →  ldn/__init__.py  →  _derive_key()
```

`ldn.load_keys()` no hace nada mágico: parte cada línea del fichero por `=` y
construye un diccionario. Luego la derivación de claves busca **exactamente
estos nombres**:

| Nombre en `prod.keys` | Cuándo se usa |
|---|---|
| `aes_kek_generation_source` | siempre |
| `aes_key_generation_source` | siempre |
| `master_key_00` | protocolo LDN v1 |
| `master_key_12` | protocolo LDN v3 |

Los dos master keys son alternativos, no acumulativos: `_select_master_key()`
elige uno según la versión del protocolo. **En total: tres valores.**

Si falta alguno, revienta con un `KeyError` durante la derivación — no hay
validación previa ni mensaje amable.

### La derivación, según la wiki de NintendoClients

1. `aes_kek_generation_source` se descifra con el master key de la generación
   correspondiente.
2. La clave de entrada se descifra con el resultado del paso 1.
3. `aes_key_generation_source` se descifra con el resultado del paso 2.
4. Los primeros 16 bytes del SHA-256 del buffer se descifran con el paso 3.

Las claves de entrada fijas del protocolo (frames de datos, frames de anuncio,
HMAC de reto/respuesta) están **publicadas en la propia wiki** y no salen de
ningún volcado.

---

## Por qué el modelo de consola resulta ser irrelevante

Las claves de una Switch se dividen en dos familias:

| Familia | Ejemplos | ¿Única por consola? |
|---|---|---|
| **Comunes** (retail) | `master_key_XX`, `aes_kek_generation_source`, `aes_key_generation_source` | **No** — idénticas en todas las consolas |
| **Únicas del aparato** | `device_key`, `sd_seed`, `bis_key_*`, `secure_boot_key` | Sí |

Los tres valores que pide LDN están **todos en la familia común**. No
identifican tu consola, no salen de tu consola y no cambian entre unidades.

Consecuencia: que tu **HAC-001(-01)** sea Mariko y no permita ejecutar
`Lockpick_RCM` **no bloquea este proyecto**. Un modchip serviría para volcar
las claves, sí, pero volcaría exactamente los mismos valores comunes que tiene
cualquier otra consola. Sería soldar la placa para obtener constantes que no
son específicas de tu máquina.

**No hace falta modchip. No hace falta consola vulnerable.**

---

## Qué queda por resolver

Conseguir un fichero de texto con esas tres líneas, en el formato
`nombre = valor_hex`.

- `master_key_00`, `aes_kek_generation_source` y `aes_key_generation_source`
  son de las constantes más antiguas y documentadas del ecosistema Switch:
  circulan públicamente desde 2018.
- `master_key_12` es posterior y sólo hace falta si la sesión negocia el
  protocolo LDN v3. Empieza probando con `master_key_00`; si falla ahí, ya
  sabrás que necesitas el otro.

De dónde obtienes ese fichero es decisión tuya. Este documento no enlaza
fuentes de descarga: son material de terceros con implicaciones legales que
dependen de tu jurisdicción, y además las recopilaciones que circulan por webs
de emuladores suelen estar incompletas o corruptas, lo que te haría depurar un
fallo que no es tuyo.

---

## Colocarlo

```bash
mkdir -p ~/.switch
cp /ruta/a/prod.keys ~/.switch/prod.keys
chmod 600 ~/.switch/prod.keys
```

Comprobar que están los nombres que hacen falta:

```bash
grep -E '^(master_key_00|master_key_12|aes_kek_generation_source|aes_key_generation_source)' \
    ~/.switch/prod.keys | cut -d= -f1
```

`scripts/setup_ubuntu.sh` comprueba que el fichero existe.

---

## Reglas que siguen en pie

1. **Nunca subir el fichero a este repo.** Ya está en `.gitignore`
   (`prod.keys`, `*.keys`, `.switch/`). Comprueba con `git status` antes de
   cada commit.
2. En un **Live USB sin persistencia se pierde al reiniciar**. Otra razón para
   crear el pendrive con partición persistente, ver
   [`01_ubuntu_live_usb.md`](01_ubuntu_live_usb.md).

---

## Fuentes

- Código: [`kinnay/LDN` → `ldn/__init__.py`](https://github.com/kinnay/LDN/blob/master/ldn/__init__.py) (`load_keys`, `_derive_key`, `_select_master_key`)
- Código: [`tornadus/frlg-ldn-trade` → `frlgsim/transport.py`](https://github.com/tornadus/frlg-ldn-trade/blob/main/frlgsim/transport.py)
- Documentación: [LDN Protocol — kinnay/NintendoClients Wiki](https://github.com/kinnay/NintendoClients/wiki/LDN-Protocol)
