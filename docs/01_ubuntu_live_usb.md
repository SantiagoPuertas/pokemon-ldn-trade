# 01 — Crear el Ubuntu Live USB

## Situación de partida

El pendrive **`Doors` (unidad `D:`)** está **vacío**: 61,5 GB en NTFS, sin nada
dentro salvo la carpeta de sistema de Windows. No es todavía un Linux
arrancable — hay que crearlo.

> ⚠️ **El proceso BORRA el pendrive por completo.** Ahora mismo no hay nada que
> perder, pero confírmalo antes de darle a Start.

---

## Decisión importante: persistencia

Un "Try Ubuntu" normal vive en RAM: **al reiniciar se pierde todo** — el repo
clonado, el `venv`, las dependencias de Python, las `prod.keys`, los `.pk3`.
Tendrías que repetir media hora de preparación en cada arranque.

Con 61 GB de pendrive no tiene sentido. Crea el USB **con partición persistente**:
Ubuntu arranca igual, pero guarda los cambios entre reinicios.

| Opción | Persistencia | Recomendación |
|---|---|---|
| Rufus + partición persistente | ✅ | **Esta** |
| Rufus sin persistencia | ❌ | Sólo para una prueba rápida de hardware |
| Instalar Ubuntu en el pendrive | ✅ (total) | Más lento de crear, pero lo más robusto |

---

## Pasos

### 1. Descargas — ✅ ya hechas (2026-09-01)

Ambas están en tu carpeta de Descargas:

| Fichero | Tamaño | Origen |
|---|---|---|
| `ubuntu-26.04.1-desktop-amd64.iso` | 6 482 409 472 B (6,04 GB) | `releases.ubuntu.com/26.04.1/` |
| `rufus-4.15p.exe` (portable) | 1 989 992 B | release oficial de `pbatard/rufus` |
| `ubuntu-SHA256SUMS.txt` | — | checksums oficiales |

Por qué Ubuntu 26.04.1 y no una más antigua: cuanto más nuevo el kernel, mejor
soporte tiene el driver `rtw89` de la Realtek RTL8852BE — el punto débil del
proyecto. Además cumple de sobra el **Python 3.12+** que pide `frlg-ldn-trade`.

### 2. Verificar la ISO antes de grabarla

Con 6 GB de por medio, una descarga truncada da errores de arranque
desconcertantes. Merece la pena el minuto que cuesta:

```powershell
Get-FileHash "$env:USERPROFILE\Downloads\ubuntu-26.04.1-desktop-amd64.iso" -Algorithm SHA256
```

Debe salir exactamente:

```
601E30FBF5D97759367C632E2C33630665039B7E2158FD068403DA3CCF1BDA1F
```

(`Get-FileHash` lo devuelve en mayúsculas; el fichero oficial lo trae en
minúsculas. Es el mismo valor.)

Si no coincide, borra la ISO y vuelve a descargarla. No sigas.

### 3. Crear el USB

1. Ejecuta `rufus-4.15p.exe` (pedirá permisos de administrador; es portable, no
   instala nada).
2. **Device**: selecciona `Doors (D:)`.
   ⚠️ **Comprueba dos veces que pone D: y 61 GB, no tu SSD de 1 TB.** Rufus
   normalmente sólo lista unidades extraíbles, pero no te fíes: este es el
   único paso del proyecto que es irreversible.
3. **Boot selection**: `Disk or ISO image` → `SELECT` →
   `ubuntu-26.04.1-desktop-amd64.iso`.
4. **Persistent partition size**: súbelo a **~20 GB**. Este es el paso que la
   mayoría se salta y luego lamenta: sin él pierdes el `venv`, las
   dependencias, las claves y los `.pk3` en cada reinicio.
5. **Partition scheme**: `GPT`. **Target system**: `UEFI (non CSM)`.
6. **File system**: deja el que proponga Rufus.
7. `START` → si pregunta, elige **"Write in ISO Image mode"**.
8. Confirma el aviso de que se borrará el contenido del pendrive.
9. Espera. Entre 5 y 20 minutos según el USB.

### 4. Arrancar desde el USB

1. Reinicia el portátil.
2. Pulsa repetidamente la tecla del **Boot Menu** nada más encender.
   Suele ser `F12`, `F9`, `F11` o `Esc` según el fabricante. Si no la sabes:
   en Windows, `Configuración → Sistema → Recuperación → Inicio avanzado →
   Reiniciar ahora → Usar un dispositivo`.
3. Elige el pendrive (aparecerá como `UEFI: <marca del USB>`).
4. En el menú de GRUB: **"Try Ubuntu"** / "Probar Ubuntu".
   **No** elijas "Install Ubuntu" — no queremos tocar el disco de Windows.

### Si no arranca

- **Secure Boot**: Ubuntu está firmado y normalmente arranca sin desactivarlo.
  Si aun así falla, desactívalo en la BIOS y vuelve a activarlo al terminar.
- **Fast Boot / Fast Startup**: desactívalo en la BIOS si el Boot Menu ni
  aparece.
- El USB no sale en la lista: prueba otro puerto USB, preferiblemente uno
  directo de la placa (no de un hub).

---

## Al llegar al escritorio de Ubuntu

Lo primero, antes que nada: **probar la tarjeta Wi-Fi**. Si la RTL8852BE no
sirve para LDN, todo lo demás sobra.

Abre una terminal (`Ctrl+Alt+T`) y sigue con
[`02_prueba_wifi.md`](02_prueba_wifi.md).

Para tener los scripts de este repo a mano en Ubuntu, lo más cómodo:

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/SantiagoPuertas/pokemon-ldn-trade.git
cd pokemon-ldn-trade
bash scripts/check_wifi.sh
```

(Necesitarás Internet en Ubuntu. Si sólo tienes la Wi-Fi interna, conéctate
normalmente por ahora — el conflicto con NetworkManager sólo aparece más
adelante, al usar LDN de verdad.)
