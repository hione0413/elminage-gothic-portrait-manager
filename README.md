# Elminage Gothic Portrait Manager

A small GUI tool that installs custom character portraits for **Elminage Gothic** without the
manual GIMP / DDS export workflow described in the Steam community guides.

Pick a race / gender / slot, load any image (PNG, JPG, etc.), click **Install**. The tool
generates correctly-named, correctly-sized `.dds` files and drops them into your game folder.
The game then uses them in place of the originals.

UI is available in **English** and **한국어** — pick the one you want from the **Language**
selector in the top-right corner. The default is English; everything switches live, no
restart needed.

---

## Quick Start (end users)

1. Download **`ElminagePortraitManager.exe`**.
2. Place it in your **Elminage Gothic** folder — the one that contains `Elminage.exe`.
   (A typical path is something like
   `…\SteamLibrary\steamapps\common\Elminage Gothic\`.)
3. Double-click the `.exe`.
4. (Optional) Switch the **Language** selector in the top-right corner to *English*.
5. Choose **Race / Gender** and a **Slot** number.
6. Click **Load image for large portrait** and pick any image.
   - Optionally also load a separate image for the small head icon. If you skip this, the
     tool auto-crops the upper-center square of the large image.
7. Click **Install / Apply**.
8. Launch the game and create a character of that race / gender — your portrait will appear
   in the matching slot.

No Python, no Pillow, no extra installation needed. The `.exe` is fully self-contained
(~30 MB) and stores nothing outside the game folder you point it at.

### Removing a portrait

- Pick the same race / gender / slot and click **Remove custom portrait for this slot**, **or**
- Select an entry in the *Installed custom portraits* list at the bottom and click
  **Remove selected**.

The tool only ever touches files matching `GR10_<id>.dds` / `GR11_<id>.dds`; the original
game archives (`S00.bra` … `S03.bra`) are never modified.

---

## How it works

When the game looks up a portrait, it first checks the game folder for two files:

| File              | Size        | Purpose                          |
|-------------------|-------------|----------------------------------|
| `GR10_<id>.dds`   | 192 × 192   | Small icon (party screen, etc.) |
| `GR11_<id>.dds`   | 1088 × 1088 | Large portrait                   |

`<id>` encodes race + gender + slot. The tool generates both files, scales the input image
(preserving aspect ratio, padded with transparent pixels), and writes them as
**uncompressed RGBA8 DDS** — the format recommended by the community guide.

### Portrait ID ranges

8 races × 2 genders × 6 slots = 96 IDs (`201`–`296`).

| Race          | Male      | Female    |
|---------------|-----------|-----------|
| Human         | 201 – 206 | 207 – 212 |
| Elf           | 213 – 218 | 219 – 224 |
| Dwarf         | 225 – 230 | 231 – 236 |
| Gnome         | 237 – 242 | 243 – 248 |
| Hobbit        | 249 – 254 | 255 – 260 |
| Faerie        | 261 – 266 | 267 – 272 |
| Lizardman     | 273 – 278 | 279 – 284 |
| Dragonewt     | 285 – 290 | 291 – 296 |

The tool fills these in for you — you never need to memorise an ID.

---

## Troubleshooting

**The game crashes when it tries to display my portrait.**
The Steam guide notes that the engine occasionally chokes on uncompressed DDS files for
specific slots. The recommended workaround is to re-export that single portrait with
**BC2 / DXT3** compression in GIMP and overwrite the file the tool produced. This case is
rare; it has only been reported for a handful of slots.

**Windows SmartScreen / antivirus warns about an "unknown publisher".**
The `.exe` is built with PyInstaller and not code-signed. If you trust the source you got it
from, click *More info → Run anyway*. If you'd rather not, run from source instead — see
*"Running from source"* below.

**The image looks stretched / off-center.**
Both portraits are square. The tool preserves your image's aspect ratio and pads the rest
with transparency, so a non-square input shows up as a smaller image on a transparent
background. Pre-crop your source to roughly square for best results.

**My image is fine but the head doesn't look right in the small icon.**
The auto-crop just takes the upper-center square. If the head isn't there, click **"작은
포트레이트용 이미지 불러오기"** and load a separately-cropped face image — the tool will
use it for the 192×192 icon only.

---

## Running from source (developers)

If you'd rather not run the prebuilt `.exe`:

```bash
pip install pillow
python portrait_manager.py
```

Python 3.10+ recommended. Tkinter is part of the standard library on Windows / macOS;
on most Linux distros you'll need to `apt install python3-tk` (or equivalent).

### Rebuilding the `.exe`

```bash
pip install pyinstaller pillow
python -m PyInstaller --noconfirm --onefile --windowed \
    --name "ElminagePortraitManager" \
    --distpath ./dist --workpath ./build --specpath ./build \
    portrait_manager.py
```

The result is `dist/ElminagePortraitManager.exe`. Smaller / faster-starting builds are
possible with `--onedir` (folder-style distribution) or `--upx-dir=...` (UPX compression).

### Files in this folder

| File                 | Purpose                                          |
|----------------------|--------------------------------------------------|
| `portrait_manager.py`| Main GUI + DDS writer (no external native deps). |
| `run.bat`            | Windows launcher for the source script.          |
| `_smoketest.py`      | Headless self-test that verifies DDS output.     |
| `dist/…exe`          | The standalone build, generated by PyInstaller.  |

---

## Credits

This tool implements the workflows documented in two Steam community guides:

- *Guide to Customizing Portraits in Elminage Gothic*
  https://steamcommunity.com/sharedfiles/filedetails/?id=3099525010
- *Guide to Custom Portraits in Elminage Gothic*
  https://steamcommunity.com/sharedfiles/filedetails/?id=318535516

All credit for the file-format reverse-engineering goes to those guide authors and to the
`.bra` extractor's author (credited in guide #2 as "Darke"). This tool just automates the
edit / export / rename steps so you don't have to repeat them by hand.

The portrait images themselves are subject to whatever license the artist released them
under — please respect those terms when distributing modded portrait packs.
