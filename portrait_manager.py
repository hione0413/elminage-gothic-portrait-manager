#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Elminage Gothic Portrait Manager
================================
포트레이트 추가/수정 도구 (커스텀 포트레이트 설치 GUI)

작동 원리
---------
이 게임은 게임 실행 파일(Elminage.exe)이 있는 폴더에 다음 형식의 .dds 파일이 존재하면
원본 포트레이트 대신 그것을 사용한다.

  GR10_<번호>.dds   ... 작은 아이콘 (192x192)
  GR11_<번호>.dds   ... 큰 포트레이트 (1088x1088)

번호는 종족/성별 슬롯에 대응하며 201~296 범위이다 (8종족 × 2성별 × 6슬롯).

DDS는 비압축 RGBA8 포맷으로 저장된다 (가이드 권장: Compression none, RGBA8, no mipmaps).
"""

import os
import struct
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk


def _detect_default_game_dir() -> Path:
    """배포 형태에 맞춰 기본 게임 폴더를 추정한다.

    - PyInstaller onefile/onedir(.exe): 실행 파일이 놓인 폴더가 곧 게임 폴더라고 가정
      (사용자는 .exe 를 Elminage Gothic 폴더에 두고 실행하면 됨)
    - 소스 실행: PortraitManager/portrait_manager.py 로부터 한 단계 위(=게임 폴더)
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# 종족 / 성별 / 슬롯 → 포트레이트 ID 매핑
# (각 종족·성별 조합 당 6슬롯, 인간 남자 201~206부터 시작)
# ---------------------------------------------------------------------------
RACE_GENDER_RANGES = [
    ("인간 / Human",         "남 / Male",   201, 206),
    ("인간 / Human",         "여 / Female", 207, 212),
    ("엘프 / Elf",           "남 / Male",   213, 218),
    ("엘프 / Elf",           "여 / Female", 219, 224),
    ("드워프 / Dwarf",       "남 / Male",   225, 230),
    ("드워프 / Dwarf",       "여 / Female", 231, 236),
    ("놈 / Gnome",           "남 / Male",   237, 242),
    ("놈 / Gnome",           "여 / Female", 243, 248),
    ("호빗 / Hobbit",        "남 / Male",   249, 254),
    ("호빗 / Hobbit",        "여 / Female", 255, 260),
    ("페어리 / Faerie",      "남 / Male",   261, 266),
    ("페어리 / Faerie",      "여 / Female", 267, 272),
    ("리자드맨 / Lizardman", "남 / Male",   273, 278),
    ("리자드맨 / Lizardman", "여 / Female", 279, 284),
    ("드라고뉴트 / Dragonewt","남 / Male",   285, 290),
    ("드라고뉴트 / Dragonewt","여 / Female", 291, 296),
]

LARGE_SIZE = 1088
SMALL_SIZE = 192
PREVIEW_LARGE_DISPLAY = 320
PREVIEW_SMALL_DISPLAY = 192


# ---------------------------------------------------------------------------
# DDS writer  (uncompressed RGBA8, byte order R G B A)
# ---------------------------------------------------------------------------
def write_dds_rgba8(path: Path, image: Image.Image) -> None:
    """PIL 이미지를 비압축 RGBA8 .dds 파일로 저장."""
    img = image.convert("RGBA")
    w, h = img.size
    raw = img.tobytes()  # R, G, B, A 순서

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
    header += struct.pack("<I", 124)              # dwSize
    header += struct.pack("<I", flags)
    header += struct.pack("<I", h)
    header += struct.pack("<I", w)
    header += struct.pack("<I", pitch)
    header += struct.pack("<I", 0)                # depth
    header += struct.pack("<I", 0)                # mipMapCount
    header += b"\x00" * (4 * 11)                  # reserved1

    # PIXELFORMAT (32 bytes)
    header += struct.pack("<I", 32)               # dwSize
    header += struct.pack("<I", DDPF_RGB | DDPF_ALPHAPIXELS)
    header += struct.pack("<I", 0)                # fourCC
    header += struct.pack("<I", 32)               # rgbBitCount
    header += struct.pack("<I", 0x000000FF)       # R mask
    header += struct.pack("<I", 0x0000FF00)       # G mask
    header += struct.pack("<I", 0x00FF0000)       # B mask
    header += struct.pack("<I", 0xFF000000)       # A mask

    header += struct.pack("<I", DDSCAPS_TEXTURE)  # dwCaps
    header += struct.pack("<I", 0)                # dwCaps2
    header += struct.pack("<I", 0)                # dwCaps3
    header += struct.pack("<I", 0)                # dwCaps4
    header += struct.pack("<I", 0)                # reserved2

    assert len(header) == 128

    with open(path, "wb") as f:
        f.write(header)
        f.write(raw)


# ---------------------------------------------------------------------------
# 이미지 가공 유틸
# ---------------------------------------------------------------------------
def fit_to_square(img: Image.Image, target: int) -> Image.Image:
    """비율 유지하며 target×target 정사각형 캔버스에 맞추고 투명 패딩."""
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
    """소형 포트레이트용 자동 크롭: 상단 중앙 정사각형."""
    img = img.convert("RGBA")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = 0  # 머리 부분은 보통 상단
    return img.crop((left, top, left + side, top + side))


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class PortraitManagerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Elminage Gothic 포트레이트 매니저")
        self.geometry("900x720")
        self.minsize(820, 640)

        self.game_dir_var = tk.StringVar(value=str(_detect_default_game_dir()))

        self.large_source: Image.Image | None = None
        self.small_source: Image.Image | None = None  # 비어 있으면 large 에서 자동 생성
        self.large_preview_img: ImageTk.PhotoImage | None = None
        self.small_preview_img: ImageTk.PhotoImage | None = None

        self._build_ui()
        self._refresh_installed_list()
        self._refresh_preview()

    # ---- UI ----------------------------------------------------------------
    def _build_ui(self) -> None:
        pad = {"padx": 8, "pady": 4}

        # 게임 폴더
        top = ttk.LabelFrame(self, text="게임 폴더 (Elminage.exe 위치)")
        top.pack(fill="x", **pad)
        e = ttk.Entry(top, textvariable=self.game_dir_var)
        e.pack(side="left", fill="x", expand=True, padx=6, pady=6)
        ttk.Button(top, text="찾아보기...", command=self._browse_game_dir)\
            .pack(side="left", padx=6, pady=6)

        # 슬롯 선택
        slot = ttk.LabelFrame(self, text="포트레이트 슬롯")
        slot.pack(fill="x", **pad)

        ttk.Label(slot, text="종족 / 성별:").grid(row=0, column=0, sticky="w", padx=6, pady=4)
        self.race_gender_var = tk.StringVar()
        labels = [f"{r}  ·  {g}  ({lo}-{hi})" for r, g, lo, hi in RACE_GENDER_RANGES]
        self.race_gender_combo = ttk.Combobox(
            slot, textvariable=self.race_gender_var, values=labels, state="readonly", width=46
        )
        self.race_gender_combo.current(0)
        self.race_gender_combo.bind("<<ComboboxSelected>>", lambda _e: self._on_race_change())
        self.race_gender_combo.grid(row=0, column=1, sticky="w", padx=6, pady=4)

        ttk.Label(slot, text="슬롯 번호:").grid(row=0, column=2, sticky="w", padx=6, pady=4)
        self.slot_var = tk.StringVar()
        self.slot_combo = ttk.Combobox(
            slot, textvariable=self.slot_var, values=[], state="readonly", width=12
        )
        self.slot_combo.bind("<<ComboboxSelected>>", lambda _e: self._update_id_label())
        self.slot_combo.grid(row=0, column=3, sticky="w", padx=6, pady=4)

        self.id_label_var = tk.StringVar(value="ID: -")
        ttk.Label(slot, textvariable=self.id_label_var, font=("Segoe UI", 10, "bold"))\
            .grid(row=0, column=4, sticky="w", padx=12, pady=4)

        self._on_race_change()

        # 이미지 영역
        img_frame = ttk.LabelFrame(self, text="이미지")
        img_frame.pack(fill="both", expand=True, **pad)

        btns = ttk.Frame(img_frame)
        btns.pack(fill="x", padx=6, pady=4)
        ttk.Button(btns, text="큰 포트레이트용 이미지 불러오기 (1088×1088)",
                   command=self._load_large).pack(side="left", padx=4)
        ttk.Button(btns, text="작은 포트레이트용 이미지 불러오기 (선택, 192×192)",
                   command=self._load_small).pack(side="left", padx=4)
        ttk.Button(btns, text="이미지 비우기", command=self._clear_images)\
            .pack(side="left", padx=4)

        previews = ttk.Frame(img_frame)
        previews.pack(fill="both", expand=True, padx=6, pady=8)

        large_box = ttk.LabelFrame(previews, text=f"GR11_XXX.dds (큰 포트레이트, {LARGE_SIZE}×{LARGE_SIZE})")
        large_box.pack(side="left", fill="both", expand=True, padx=4)
        self.large_canvas = tk.Canvas(large_box, width=PREVIEW_LARGE_DISPLAY,
                                      height=PREVIEW_LARGE_DISPLAY, bg="#222")
        self.large_canvas.pack(padx=6, pady=6)

        small_box = ttk.LabelFrame(previews, text=f"GR10_XXX.dds (작은 포트레이트, {SMALL_SIZE}×{SMALL_SIZE})")
        small_box.pack(side="left", fill="both", expand=False, padx=4)
        self.small_canvas = tk.Canvas(small_box, width=PREVIEW_SMALL_DISPLAY,
                                      height=PREVIEW_SMALL_DISPLAY, bg="#222")
        self.small_canvas.pack(padx=6, pady=6)
        self.small_source_label_var = tk.StringVar(value="(자동: 큰 이미지 상단 중앙 크롭)")
        ttk.Label(small_box, textvariable=self.small_source_label_var,
                  foreground="#666").pack(padx=6, pady=2)

        # 액션 버튼
        action = ttk.Frame(self)
        action.pack(fill="x", **pad)
        ttk.Button(action, text="설치 / 적용",
                   command=self._install).pack(side="left", padx=4, pady=4)
        ttk.Button(action, text="이 슬롯의 커스텀 포트레이트 제거",
                   command=self._remove_current_slot).pack(side="left", padx=4, pady=4)
        self.status_var = tk.StringVar(value="준비됨.")
        ttk.Label(action, textvariable=self.status_var, foreground="#0a0")\
            .pack(side="left", padx=12)

        # 설치된 목록
        listf = ttk.LabelFrame(self, text="설치된 커스텀 포트레이트")
        listf.pack(fill="both", expand=True, **pad)
        self.installed_list = tk.Listbox(listf, height=8)
        self.installed_list.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        sb = ttk.Scrollbar(listf, orient="vertical", command=self.installed_list.yview)
        sb.pack(side="left", fill="y")
        self.installed_list.config(yscrollcommand=sb.set)

        rbtns = ttk.Frame(listf)
        rbtns.pack(side="left", fill="y", padx=6, pady=6)
        ttk.Button(rbtns, text="목록 새로고침", command=self._refresh_installed_list)\
            .pack(fill="x", pady=2)
        ttk.Button(rbtns, text="선택 항목 제거", command=self._remove_selected)\
            .pack(fill="x", pady=2)
        ttk.Button(rbtns, text="게임 폴더 열기", command=self._open_game_dir)\
            .pack(fill="x", pady=2)

    # ---- helpers -----------------------------------------------------------
    def _browse_game_dir(self) -> None:
        d = filedialog.askdirectory(title="Elminage Gothic 폴더 선택",
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
        if pid is None:
            self.id_label_var.set("ID: -")
        else:
            self.id_label_var.set(f"ID: {pid}   →   GR10_{pid}.dds, GR11_{pid}.dds")

    def _load_large(self) -> None:
        path = filedialog.askopenfilename(
            title="큰 포트레이트용 이미지 선택",
            filetypes=[("이미지", "*.png *.jpg *.jpeg *.bmp *.tga *.webp *.tiff"),
                       ("모든 파일", "*.*")],
        )
        if not path:
            return
        try:
            self.large_source = Image.open(path)
            self._set_status(f"큰 이미지 로드: {Path(path).name}", ok=True)
        except Exception as exc:
            messagebox.showerror("오류", f"이미지를 열 수 없습니다:\n{exc}")
            return
        self._refresh_preview()

    def _load_small(self) -> None:
        path = filedialog.askopenfilename(
            title="작은 포트레이트용 이미지 선택 (얼굴/머리 부분)",
            filetypes=[("이미지", "*.png *.jpg *.jpeg *.bmp *.tga *.webp *.tiff"),
                       ("모든 파일", "*.*")],
        )
        if not path:
            return
        try:
            self.small_source = Image.open(path)
            self.small_source_label_var.set(f"수동: {Path(path).name}")
            self._set_status(f"작은 이미지 로드: {Path(path).name}", ok=True)
        except Exception as exc:
            messagebox.showerror("오류", f"이미지를 열 수 없습니다:\n{exc}")
            return
        self._refresh_preview()

    def _clear_images(self) -> None:
        self.large_source = None
        self.small_source = None
        self.small_source_label_var.set("(자동: 큰 이미지 상단 중앙 크롭)")
        self._set_status("이미지를 비웠습니다.")
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
                                          fill="#888",
                                          text="이미지 없음")
        else:
            shown = large.resize((PREVIEW_LARGE_DISPLAY, PREVIEW_LARGE_DISPLAY),
                                 Image.LANCZOS)
            self.large_preview_img = ImageTk.PhotoImage(shown)
            self.large_canvas.create_image(0, 0, anchor="nw", image=self.large_preview_img)

        small = self._build_small_processed()
        self.small_canvas.delete("all")
        if small is None:
            self.small_canvas.create_text(PREVIEW_SMALL_DISPLAY // 2,
                                          PREVIEW_SMALL_DISPLAY // 2,
                                          fill="#888",
                                          text="이미지 없음")
        else:
            self.small_preview_img = ImageTk.PhotoImage(small)
            self.small_canvas.create_image(0, 0, anchor="nw", image=self.small_preview_img)

    # ---- install / remove --------------------------------------------------
    def _install(self) -> None:
        pid = self._current_id()
        if pid is None:
            messagebox.showwarning("주의", "슬롯 번호를 선택하세요.")
            return
        if self.large_source is None:
            messagebox.showwarning("주의", "큰 포트레이트용 이미지를 먼저 불러오세요.")
            return

        game_dir = Path(self.game_dir_var.get())
        if not game_dir.exists():
            messagebox.showerror("오류", f"게임 폴더가 존재하지 않습니다:\n{game_dir}")
            return

        large = self._build_large_processed()
        small = self._build_small_processed()
        assert large is not None and small is not None

        gr11 = game_dir / f"GR11_{pid}.dds"
        gr10 = game_dir / f"GR10_{pid}.dds"

        if gr11.exists() or gr10.exists():
            ok = messagebox.askyesno(
                "덮어쓰기 확인",
                f"이미 슬롯 {pid}의 커스텀 파일이 있습니다.\n덮어쓸까요?\n\n"
                f"- {gr11.name}\n- {gr10.name}",
            )
            if not ok:
                return

        try:
            write_dds_rgba8(gr11, large)
            write_dds_rgba8(gr10, small)
        except Exception as exc:
            messagebox.showerror("저장 실패", str(exc))
            return

        self._set_status(f"설치 완료: {gr11.name}, {gr10.name}", ok=True)
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
        # line is "201   GR10/GR11"
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
            messagebox.showinfo("정보", f"슬롯 {pid} 의 커스텀 파일이 없습니다.")
            return
        ok = messagebox.askyesno(
            "삭제 확인",
            f"슬롯 {pid} 의 커스텀 포트레이트 파일을 삭제할까요?\n\n"
            f"- {gr10.name} {'(있음)' if gr10.exists() else '(없음)'}\n"
            f"- {gr11.name} {'(있음)' if gr11.exists() else '(없음)'}",
        )
        if not ok:
            return
        for p in (gr10, gr11):
            try:
                if p.exists():
                    p.unlink()
            except Exception as exc:
                messagebox.showerror("삭제 실패", f"{p.name}: {exc}")
                return
        self._set_status(f"슬롯 {pid} 제거됨.", ok=True)
        self._refresh_installed_list()

    def _refresh_installed_list(self) -> None:
        self.installed_list.delete(0, "end")
        game_dir = Path(self.game_dir_var.get())
        if not game_dir.exists():
            return
        # 슬롯별로 GR10/GR11 존재 여부 표시
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

    @staticmethod
    def _race_label_for(pid: int) -> str:
        for r, g, lo, hi in RACE_GENDER_RANGES:
            if lo <= pid <= hi:
                return f"{r} · {g}"
        return "(범위 외)"

    def _open_game_dir(self) -> None:
        d = self.game_dir_var.get()
        if not d:
            return
        try:
            os.startfile(d)  # type: ignore[attr-defined]  # Windows
        except Exception:
            messagebox.showinfo("폴더", d)

    def _set_status(self, msg: str, ok: bool = False) -> None:
        self.status_var.set(msg)


def main() -> None:
    app = PortraitManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
