#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Elminage Gothic Portrait Manager
================================
Custom portrait installer for Elminage Gothic. Supports Korean / English UI.

How the game uses these files
-----------------------------
The engine looks for these files in the same folder as `Elminage.exe`:

    GR10_<id>.dds   ... small icon         (192x192)
    GR11_<id>.dds   ... large portrait     (1088x1088)

`<id>` encodes race/gender/slot. Range: 201..296 (8 races * 2 genders * 6 slots).
DDS is written as uncompressed RGBA8 (no mipmaps), per the community guide.
"""

import os
import struct
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

LARGE_SIZE = 1088
SMALL_SIZE = 192
PREVIEW_LARGE_DISPLAY = 320
PREVIEW_SMALL_DISPLAY = 192


# ---------------------------------------------------------------------------
# Race / gender slot table  (data only; display names are localized below)
# ---------------------------------------------------------------------------
RACE_GENDER_RANGES = [
    ("human",     "male",   201, 206),
    ("human",     "female", 207, 212),
    ("elf",       "male",   213, 218),
    ("elf",       "female", 219, 224),
    ("dwarf",     "male",   225, 230),
    ("dwarf",     "female", 231, 236),
    ("gnome",     "male",   237, 242),
    ("gnome",     "female", 243, 248),
    ("hobbit",    "male",   249, 254),
    ("hobbit",    "female", 255, 260),
    ("faerie",    "male",   261, 266),
    ("faerie",    "female", 267, 272),
    ("lizardman", "male",   273, 278),
    ("lizardman", "female", 279, 284),
    ("dragonewt", "male",   285, 290),
    ("dragonewt", "female", 291, 296),
]


# ---------------------------------------------------------------------------
# i18n strings
# ---------------------------------------------------------------------------
LANGUAGES = [("ko", "한국어"), ("en", "English")]

RACE_NAMES = {
    "ko": {"human": "인간", "elf": "엘프", "dwarf": "드워프", "gnome": "놈",
           "hobbit": "호빗", "faerie": "페어리", "lizardman": "리자드맨",
           "dragonewt": "드라고뉴트"},
    "en": {"human": "Human", "elf": "Elf", "dwarf": "Dwarf", "gnome": "Gnome",
           "hobbit": "Hobbit", "faerie": "Faerie", "lizardman": "Lizardman",
           "dragonewt": "Dragonewt"},
}
GENDER_NAMES = {
    "ko": {"male": "남", "female": "여"},
    "en": {"male": "Male", "female": "Female"},
}

STR = {
    "ko": {
        "title":              "Elminage Gothic 포트레이트 매니저",
        "language":           "언어:",
        "game_folder_frame":  "게임 폴더 (Elminage.exe 위치)",
        "browse":             "찾아보기...",
        "slot_frame":         "포트레이트 슬롯",
        "race_gender_label":  "종족 / 성별:",
        "slot_label":         "슬롯 번호:",
        "id_empty":           "ID: -",
        "id_fmt":             "ID: {pid}   →   GR10_{pid}.dds, GR11_{pid}.dds",
        "image_frame":        "이미지",
        "load_large":         "큰 포트레이트용 이미지 불러오기 (1088×1088)",
        "load_small":         "작은 포트레이트용 이미지 불러오기 (선택, 192×192)",
        "clear_image":        "이미지 비우기",
        "large_box":          "GR11_XXX.dds (큰 포트레이트, 1088×1088)",
        "small_box":          "GR10_XXX.dds (작은 포트레이트, 192×192)",
        "auto_crop_label":    "(자동: 큰 이미지 상단 중앙 크롭)",
        "manual_small_fmt":   "수동: {name}",
        "no_image":           "이미지 없음",
        "install":            "설치 / 적용",
        "remove_current":     "이 슬롯의 커스텀 포트레이트 제거",
        "ready":              "준비됨.",
        "installed_frame":    "설치된 커스텀 포트레이트",
        "refresh_list":       "목록 새로고침",
        "remove_selected":    "선택 항목 제거",
        "open_game_dir":      "게임 폴더 열기",
        "out_of_range":       "(범위 외)",
        "dlg_pick_game_dir":  "Elminage Gothic 폴더 선택",
        "dlg_pick_large":     "큰 포트레이트용 이미지 선택",
        "dlg_pick_small":     "작은 포트레이트용 이미지 선택 (얼굴/머리 부분)",
        "filetype_image":     "이미지",
        "filetype_all":       "모든 파일",
        "warn_pick_slot":     "슬롯 번호를 선택하세요.",
        "warn_pick_image":    "큰 포트레이트용 이미지를 먼저 불러오세요.",
        "err_no_game_dir":    "게임 폴더가 존재하지 않습니다:\n{path}",
        "err_open_image":     "이미지를 열 수 없습니다:\n{exc}",
        "err_save":           "저장 실패",
        "err_delete_fmt":     "{name}: {exc}",
        "title_overwrite":    "덮어쓰기 확인",
        "msg_overwrite_fmt":  ("이미 슬롯 {pid}의 커스텀 파일이 있습니다.\n덮어쓸까요?\n\n"
                              "- {gr11}\n- {gr10}"),
        "title_delete":       "삭제 확인",
        "msg_delete_fmt":     ("슬롯 {pid} 의 커스텀 포트레이트 파일을 삭제할까요?\n\n"
                              "- {gr10} {gr10_state}\n- {gr11} {gr11_state}"),
        "state_present":      "(있음)",
        "state_absent":       "(없음)",
        "title_info":         "정보",
        "msg_no_custom_fmt":  "슬롯 {pid} 의 커스텀 파일이 없습니다.",
        "title_warn":         "주의",
        "title_err":          "오류",
        "status_loaded_large":"큰 이미지 로드: {name}",
        "status_loaded_small":"작은 이미지 로드: {name}",
        "status_cleared":     "이미지를 비웠습니다.",
        "status_installed":   "설치 완료: {gr11}, {gr10}",
        "status_removed":     "슬롯 {pid} 제거됨.",
        "title_folder":       "폴더",
    },
    "en": {
        "title":              "Elminage Gothic Portrait Manager",
        "language":           "Language:",
        "game_folder_frame":  "Game folder (location of Elminage.exe)",
        "browse":             "Browse...",
        "slot_frame":         "Portrait slot",
        "race_gender_label":  "Race / Gender:",
        "slot_label":         "Slot number:",
        "id_empty":           "ID: -",
        "id_fmt":             "ID: {pid}   →   GR10_{pid}.dds, GR11_{pid}.dds",
        "image_frame":        "Image",
        "load_large":         "Load image for large portrait (1088×1088)",
        "load_small":         "Load image for small portrait (optional, 192×192)",
        "clear_image":        "Clear images",
        "large_box":          "GR11_XXX.dds (large portrait, 1088×1088)",
        "small_box":          "GR10_XXX.dds (small portrait, 192×192)",
        "auto_crop_label":    "(auto: top-center crop of large image)",
        "manual_small_fmt":   "manual: {name}",
        "no_image":           "no image",
        "install":            "Install / Apply",
        "remove_current":     "Remove custom portrait for this slot",
        "ready":              "Ready.",
        "installed_frame":    "Installed custom portraits",
        "refresh_list":       "Refresh list",
        "remove_selected":    "Remove selected",
        "open_game_dir":      "Open game folder",
        "out_of_range":       "(out of range)",
        "dlg_pick_game_dir":  "Pick the Elminage Gothic folder",
        "dlg_pick_large":     "Pick image for large portrait",
        "dlg_pick_small":     "Pick image for small portrait (face / head)",
        "filetype_image":     "Images",
        "filetype_all":       "All files",
        "warn_pick_slot":     "Please pick a slot number.",
        "warn_pick_image":    "Load an image for the large portrait first.",
        "err_no_game_dir":    "Game folder does not exist:\n{path}",
        "err_open_image":     "Could not open image:\n{exc}",
        "err_save":           "Save failed",
        "err_delete_fmt":     "{name}: {exc}",
        "title_overwrite":    "Overwrite?",
        "msg_overwrite_fmt":  ("Custom files for slot {pid} already exist.\nOverwrite?\n\n"
                              "- {gr11}\n- {gr10}"),
        "title_delete":       "Delete?",
        "msg_delete_fmt":     ("Delete the custom portrait files for slot {pid}?\n\n"
                              "- {gr10} {gr10_state}\n- {gr11} {gr11_state}"),
        "state_present":      "(present)",
        "state_absent":       "(missing)",
        "title_info":         "Info",
        "msg_no_custom_fmt":  "No custom files exist for slot {pid}.",
        "title_warn":         "Warning",
        "title_err":          "Error",
        "status_loaded_large":"Loaded large image: {name}",
        "status_loaded_small":"Loaded small image: {name}",
        "status_cleared":     "Images cleared.",
        "status_installed":   "Installed: {gr11}, {gr10}",
        "status_removed":     "Slot {pid} removed.",
        "title_folder":       "Folder",
    },
}


def _detect_default_game_dir() -> Path:
    """Best-effort guess at the game folder.

    - Frozen build (.exe): folder where the .exe lives. Drop the .exe next to
      Elminage.exe and the field is pre-filled correctly.
    - Source run: parent of the PortraitManager folder.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# DDS writer  (uncompressed RGBA8, byte order R G B A)
# ---------------------------------------------------------------------------
def write_dds_rgba8(path: Path, image: Image.Image) -> None:
    img = image.convert("RGBA")
    w, h = img.size
    raw = img.tobytes()  # R, G, B, A

    DDSD_CAPS        = 0x1
    DDSD_HEIGHT      = 0x2
    DDSD_WIDTH       = 0x4
    DDSD_PITCH       = 0x8
    DDSD_PIXELFORMAT = 0x1000
    DDPF_ALPHAPIXELS = 0x1
    DDPF_RGB         = 0x40
    DDSCAPS_TEXTURE  = 0x1000

    flags = DDSD_CAPS | DDSD_HEIGHT | DDSD_WIDTH | DDSD_PITCH | DDSD_PIXELFORMAT
    pitch = w * 4

    header = bytearray()
    header += b"DDS "
    header += struct.pack("<I", 124)
    header += struct.pack("<I", flags)
    header += struct.pack("<I", h)
    header += struct.pack("<I", w)
    header += struct.pack("<I", pitch)
    header += struct.pack("<I", 0)
    header += struct.pack("<I", 0)
    header += b"\x00" * (4 * 11)
    header += struct.pack("<I", 32)
    header += struct.pack("<I", DDPF_RGB | DDPF_ALPHAPIXELS)
    header += struct.pack("<I", 0)
    header += struct.pack("<I", 32)
    header += struct.pack("<I", 0x000000FF)
    header += struct.pack("<I", 0x0000FF00)
    header += struct.pack("<I", 0x00FF0000)
    header += struct.pack("<I", 0xFF000000)
    header += struct.pack("<I", DDSCAPS_TEXTURE)
    header += struct.pack("<I", 0)
    header += struct.pack("<I", 0)
    header += struct.pack("<I", 0)
    header += struct.pack("<I", 0)
    assert len(header) == 128

    with open(path, "wb") as f:
        f.write(header)
        f.write(raw)


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------
def fit_to_square(img: Image.Image, target: int) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    scale = target / max(w, h)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    resized = img.resize((new_w, new_h), Image.LANCZOS)
    canvas = Image.new("RGBA", (target, target), (0, 0, 0, 0))
    canvas.paste(resized, ((target - new_w) // 2, (target - new_h) // 2), resized)
    return canvas


def auto_crop_head(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    return img.crop((left, 0, left + side, side))


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class PortraitManagerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.lang = "ko"
        self.title(self.t("title"))
        self.geometry("900x720")
        self.minsize(820, 640)

        self.game_dir_var = tk.StringVar(value=str(_detect_default_game_dir()))
        self.large_source: Image.Image | None = None
        self.small_source: Image.Image | None = None
        self.small_source_filename: str | None = None
        self.large_preview_img: ImageTk.PhotoImage | None = None
        self.small_preview_img: ImageTk.PhotoImage | None = None

        # Widgets that need .config(text=...) on language switch
        self._frames: dict[str, tk.Widget] = {}    # key -> LabelFrame
        self._labels: dict[str, tk.Widget] = {}    # key -> Label/Button using direct text
        self._buttons: dict[str, tk.Widget] = {}   # key -> Button using direct text
        # Dynamic StringVars (formatted; refreshed on language switch)
        self._dyn_status_key = "ready"
        self._dyn_status_kw: dict = {}
        self._dyn_id_pid: int | None = None

        self.status_var = tk.StringVar()
        self.id_label_var = tk.StringVar()
        self.small_source_label_var = tk.StringVar()

        self._build_ui()
        self._refresh_installed_list()
        self._refresh_preview()
        self._apply_language()  # populate all text now that widgets exist

    # ---- i18n --------------------------------------------------------------
    def t(self, key: str, **kw) -> str:
        s = STR[self.lang].get(key, key)
        return s.format(**kw) if kw else s

    def _race_label(self, race_key: str) -> str:
        return RACE_NAMES[self.lang][race_key]

    def _gender_label(self, gender_key: str) -> str:
        return GENDER_NAMES[self.lang][gender_key]

    def _race_gender_combo_values(self) -> list[str]:
        return [
            f"{self._race_label(r)} · {self._gender_label(g)} ({lo}-{hi})"
            for r, g, lo, hi in RACE_GENDER_RANGES
        ]

    def _on_language_change(self, _evt=None) -> None:
        for code, display in LANGUAGES:
            if display == self.language_var.get():
                self.lang = code
                break
        self._apply_language()

    def _apply_language(self) -> None:
        # Window title
        self.title(self.t("title"))
        # LabelFrames
        for key, w in self._frames.items():
            w.config(text=self.t(key))
        # Static labels / buttons
        for key, w in self._labels.items():
            w.config(text=self.t(key))
        for key, w in self._buttons.items():
            w.config(text=self.t(key))
        # Race/gender combo: preserve selection by index
        idx = self.race_gender_combo.current()
        self.race_gender_combo["values"] = self._race_gender_combo_values()
        if 0 <= idx < len(RACE_GENDER_RANGES):
            self.race_gender_combo.current(idx)
        # Dynamic strings
        self._update_id_label()
        self._update_small_source_label()
        self.status_var.set(self.t(self._dyn_status_key, **self._dyn_status_kw))
        # Refresh list (race labels inside lines change with language)
        self._refresh_installed_list()
        # Re-render previews so the "no image" placeholder follows language
        self._refresh_preview()

    # ---- UI ----------------------------------------------------------------
    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        # Top: language switcher
        bar = ttk.Frame(self)
        bar.pack(fill="x", **pad)
        lang_lbl = ttk.Label(bar)
        lang_lbl.pack(side="right", padx=(0, 4))
        self._labels["language"] = lang_lbl

        self.language_var = tk.StringVar(value=LANGUAGES[0][1])
        lang_combo = ttk.Combobox(
            bar, textvariable=self.language_var,
            values=[disp for _c, disp in LANGUAGES],
            state="readonly", width=12,
        )
        lang_combo.pack(side="right")
        lang_combo.bind("<<ComboboxSelected>>", self._on_language_change)

        # Game folder
        gf = ttk.LabelFrame(self)
        gf.pack(fill="x", **pad)
        self._frames["game_folder_frame"] = gf
        ttk.Entry(gf, textvariable=self.game_dir_var)\
            .pack(side="left", fill="x", expand=True, padx=6, pady=6)
        b_browse = ttk.Button(gf, command=self._browse_game_dir)
        b_browse.pack(side="left", padx=6, pady=6)
        self._buttons["browse"] = b_browse

        # Slot picker
        sf = ttk.LabelFrame(self)
        sf.pack(fill="x", **pad)
        self._frames["slot_frame"] = sf

        l1 = ttk.Label(sf)
        l1.grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self._labels["race_gender_label"] = l1

        self.race_gender_var = tk.StringVar()
        self.race_gender_combo = ttk.Combobox(
            sf, textvariable=self.race_gender_var,
            values=self._race_gender_combo_values(),
            state="readonly", width=46,
        )
        self.race_gender_combo.current(0)
        self.race_gender_combo.bind("<<ComboboxSelected>>",
                                    lambda _e: self._on_race_change())
        self.race_gender_combo.grid(row=0, column=1, sticky="w", padx=6, pady=4)

        l2 = ttk.Label(sf)
        l2.grid(row=0, column=2, sticky="w", padx=6, pady=4)
        self._labels["slot_label"] = l2

        self.slot_var = tk.StringVar()
        self.slot_combo = ttk.Combobox(
            sf, textvariable=self.slot_var, values=[], state="readonly", width=12,
        )
        self.slot_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_id_label())
        self.slot_combo.grid(row=0, column=3, sticky="w", padx=6, pady=4)

        ttk.Label(sf, textvariable=self.id_label_var,
                  font=("Segoe UI", 10, "bold"))\
            .grid(row=0, column=4, sticky="w", padx=12, pady=4)

        self._on_race_change()

        # Image area
        img_frame = ttk.LabelFrame(self)
        img_frame.pack(fill="both", expand=True, **pad)
        self._frames["image_frame"] = img_frame

        btns = ttk.Frame(img_frame)
        btns.pack(fill="x", padx=6, pady=4)
        for key, cmd in [("load_large", self._load_large),
                         ("load_small", self._load_small),
                         ("clear_image", self._clear_images)]:
            b = ttk.Button(btns, command=cmd)
            b.pack(side="left", padx=4)
            self._buttons[key] = b

        previews = ttk.Frame(img_frame)
        previews.pack(fill="both", expand=True, padx=6, pady=8)

        large_box = ttk.LabelFrame(previews)
        large_box.pack(side="left", fill="both", expand=True, padx=4)
        self._frames["large_box"] = large_box
        self.large_canvas = tk.Canvas(large_box, width=PREVIEW_LARGE_DISPLAY,
                                      height=PREVIEW_LARGE_DISPLAY, bg="#222")
        self.large_canvas.pack(padx=6, pady=6)

        small_box = ttk.LabelFrame(previews)
        small_box.pack(side="left", fill="both", expand=False, padx=4)
        self._frames["small_box"] = small_box
        self.small_canvas = tk.Canvas(small_box, width=PREVIEW_SMALL_DISPLAY,
                                      height=PREVIEW_SMALL_DISPLAY, bg="#222")
        self.small_canvas.pack(padx=6, pady=6)
        ttk.Label(small_box, textvariable=self.small_source_label_var,
                  foreground="#666").pack(padx=6, pady=2)

        # Action row
        action = ttk.Frame(self)
        action.pack(fill="x", **pad)
        b_install = ttk.Button(action, command=self._install)
        b_install.pack(side="left", padx=4, pady=4)
        self._buttons["install"] = b_install
        b_remove = ttk.Button(action, command=self._remove_current_slot)
        b_remove.pack(side="left", padx=4, pady=4)
        self._buttons["remove_current"] = b_remove
        ttk.Label(action, textvariable=self.status_var, foreground="#0a0")\
            .pack(side="left", padx=12)

        # Installed list
        listf = ttk.LabelFrame(self)
        listf.pack(fill="both", expand=True, **pad)
        self._frames["installed_frame"] = listf
        self.installed_list = tk.Listbox(listf, height=8)
        self.installed_list.pack(side="left", fill="both", expand=True,
                                 padx=6, pady=6)
        sb = ttk.Scrollbar(listf, orient="vertical",
                           command=self.installed_list.yview)
        sb.pack(side="left", fill="y")
        self.installed_list.config(yscrollcommand=sb.set)

        rbtns = ttk.Frame(listf)
        rbtns.pack(side="left", fill="y", padx=6, pady=6)
        for key, cmd in [("refresh_list", self._refresh_installed_list),
                         ("remove_selected", self._remove_selected),
                         ("open_game_dir", self._open_game_dir)]:
            b = ttk.Button(rbtns, command=cmd)
            b.pack(fill="x", pady=2)
            self._buttons[key] = b

    # ---- helpers -----------------------------------------------------------
    def _browse_game_dir(self) -> None:
        d = filedialog.askdirectory(title=self.t("dlg_pick_game_dir"),
                                    initialdir=self.game_dir_var.get())
        if d:
            self.game_dir_var.set(d)
            self._refresh_installed_list()

    def _on_race_change(self) -> None:
        idx = self.race_gender_combo.current()
        if idx < 0:
            return
        _r, _g, lo, hi = RACE_GENDER_RANGES[idx]
        self.slot_combo["values"] = [str(n) for n in range(lo, hi + 1)]
        self.slot_combo.current(0)
        self._update_id_label()

    def _current_id(self) -> int | None:
        try:
            return int(self.slot_var.get())
        except ValueError:
            return None

    def _update_id_label(self) -> None:
        pid = self._current_id()
        self._dyn_id_pid = pid
        if pid is None:
            self.id_label_var.set(self.t("id_empty"))
        else:
            self.id_label_var.set(self.t("id_fmt", pid=pid))

    def _update_small_source_label(self) -> None:
        if self.small_source_filename:
            self.small_source_label_var.set(
                self.t("manual_small_fmt", name=self.small_source_filename))
        else:
            self.small_source_label_var.set(self.t("auto_crop_label"))

    def _image_filetypes(self):
        return [(self.t("filetype_image"),
                 "*.png *.jpg *.jpeg *.bmp *.tga *.webp *.tiff"),
                (self.t("filetype_all"), "*.*")]

    def _load_large(self) -> None:
        path = filedialog.askopenfilename(
            title=self.t("dlg_pick_large"), filetypes=self._image_filetypes())
        if not path:
            return
        try:
            self.large_source = Image.open(path)
            self._set_status("status_loaded_large", name=Path(path).name)
        except Exception as exc:
            messagebox.showerror(self.t("title_err"),
                                 self.t("err_open_image", exc=exc))
            return
        self._refresh_preview()

    def _load_small(self) -> None:
        path = filedialog.askopenfilename(
            title=self.t("dlg_pick_small"), filetypes=self._image_filetypes())
        if not path:
            return
        try:
            self.small_source = Image.open(path)
            self.small_source_filename = Path(path).name
            self._update_small_source_label()
            self._set_status("status_loaded_small", name=Path(path).name)
        except Exception as exc:
            messagebox.showerror(self.t("title_err"),
                                 self.t("err_open_image", exc=exc))
            return
        self._refresh_preview()

    def _clear_images(self) -> None:
        self.large_source = None
        self.small_source = None
        self.small_source_filename = None
        self._update_small_source_label()
        self._set_status("status_cleared")
        self._refresh_preview()

    # ---- preview -----------------------------------------------------------
    def _build_large_processed(self) -> Image.Image | None:
        if self.large_source is None:
            return None
        return fit_to_square(self.large_source, LARGE_SIZE)

    def _build_small_processed(self) -> Image.Image | None:
        if self.small_source is not None:
            return fit_to_square(self.small_source, SMALL_SIZE)
        if self.large_source is not None:
            return fit_to_square(auto_crop_head(self.large_source), SMALL_SIZE)
        return None

    def _refresh_preview(self) -> None:
        large = self._build_large_processed()
        self.large_canvas.delete("all")
        if large is None:
            self.large_canvas.create_text(PREVIEW_LARGE_DISPLAY // 2,
                                          PREVIEW_LARGE_DISPLAY // 2,
                                          fill="#888", text=self.t("no_image"))
        else:
            shown = large.resize((PREVIEW_LARGE_DISPLAY, PREVIEW_LARGE_DISPLAY),
                                 Image.LANCZOS)
            self.large_preview_img = ImageTk.PhotoImage(shown)
            self.large_canvas.create_image(0, 0, anchor="nw",
                                           image=self.large_preview_img)

        small = self._build_small_processed()
        self.small_canvas.delete("all")
        if small is None:
            self.small_canvas.create_text(PREVIEW_SMALL_DISPLAY // 2,
                                          PREVIEW_SMALL_DISPLAY // 2,
                                          fill="#888", text=self.t("no_image"))
        else:
            self.small_preview_img = ImageTk.PhotoImage(small)
            self.small_canvas.create_image(0, 0, anchor="nw",
                                           image=self.small_preview_img)

    # ---- install / remove --------------------------------------------------
    def _install(self) -> None:
        pid = self._current_id()
        if pid is None:
            messagebox.showwarning(self.t("title_warn"), self.t("warn_pick_slot"))
            return
        if self.large_source is None:
            messagebox.showwarning(self.t("title_warn"), self.t("warn_pick_image"))
            return

        game_dir = Path(self.game_dir_var.get())
        if not game_dir.exists():
            messagebox.showerror(self.t("title_err"),
                                 self.t("err_no_game_dir", path=game_dir))
            return

        large = self._build_large_processed()
        small = self._build_small_processed()
        assert large is not None and small is not None

        gr11 = game_dir / f"GR11_{pid}.dds"
        gr10 = game_dir / f"GR10_{pid}.dds"

        if gr11.exists() or gr10.exists():
            ok = messagebox.askyesno(
                self.t("title_overwrite"),
                self.t("msg_overwrite_fmt", pid=pid, gr11=gr11.name, gr10=gr10.name),
            )
            if not ok:
                return

        try:
            write_dds_rgba8(gr11, large)
            write_dds_rgba8(gr10, small)
        except Exception as exc:
            messagebox.showerror(self.t("err_save"), str(exc))
            return

        self._set_status("status_installed", gr11=gr11.name, gr10=gr10.name)
        self._refresh_installed_list()

    def _remove_current_slot(self) -> None:
        pid = self._current_id()
        if pid is None:
            return
        self._remove_pid(pid)

    def _remove_selected(self) -> None:
        sel = self.installed_list.curselection()
        if not sel:
            return
        line = self.installed_list.get(sel[0])
        try:
            pid = int(line.split()[0])
        except ValueError:
            return
        self._remove_pid(pid)

    def _remove_pid(self, pid: int) -> None:
        game_dir = Path(self.game_dir_var.get())
        gr10 = game_dir / f"GR10_{pid}.dds"
        gr11 = game_dir / f"GR11_{pid}.dds"
        if not gr10.exists() and not gr11.exists():
            messagebox.showinfo(self.t("title_info"),
                                self.t("msg_no_custom_fmt", pid=pid))
            return
        ok = messagebox.askyesno(
            self.t("title_delete"),
            self.t("msg_delete_fmt", pid=pid,
                   gr10=gr10.name,
                   gr11=gr11.name,
                   gr10_state=self.t("state_present" if gr10.exists() else "state_absent"),
                   gr11_state=self.t("state_present" if gr11.exists() else "state_absent")),
        )
        if not ok:
            return
        for p in (gr10, gr11):
            try:
                if p.exists():
                    p.unlink()
            except Exception as exc:
                messagebox.showerror(
                    self.t("title_err"),
                    self.t("err_delete_fmt", name=p.name, exc=exc))
                return
        self._set_status("status_removed", pid=pid)
        self._refresh_installed_list()

    def _refresh_installed_list(self) -> None:
        self.installed_list.delete(0, "end")
        game_dir = Path(self.game_dir_var.get())
        if not game_dir.exists():
            return
        present: dict[int, set[str]] = {}
        for f in game_dir.iterdir():
            if not f.is_file() or f.suffix.lower() != ".dds":
                continue
            name = f.stem.upper()
            if name.startswith("GR10_") or name.startswith("GR11_"):
                try:
                    pid = int(name.split("_", 1)[1])
                except ValueError:
                    continue
                present.setdefault(pid, set()).add(name.split("_", 1)[0])
        for pid in sorted(present):
            tags = present[pid]
            both = "GR10+GR11" if {"GR10", "GR11"} <= tags else " · ".join(sorted(tags))
            label = self._race_label_for(pid)
            self.installed_list.insert("end", f"{pid:>4}   {both:<10}   {label}")

    def _race_label_for(self, pid: int) -> str:
        for r, g, lo, hi in RACE_GENDER_RANGES:
            if lo <= pid <= hi:
                return f"{self._race_label(r)} · {self._gender_label(g)}"
        return self.t("out_of_range")

    def _open_game_dir(self) -> None:
        d = self.game_dir_var.get()
        if not d:
            return
        try:
            os.startfile(d)  # type: ignore[attr-defined]
        except Exception:
            messagebox.showinfo(self.t("title_folder"), d)

    def _set_status(self, key: str, **kw) -> None:
        self._dyn_status_key = key
        self._dyn_status_kw = kw
        self.status_var.set(self.t(key, **kw))


def main() -> None:
    PortraitManagerApp().mainloop()


if __name__ == "__main__":
    main()
