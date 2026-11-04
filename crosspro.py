# -*- coding: utf-8 -*-
"""
CrossPro - Ultimate FPS Crosshair System (Crosshair X Style)
- Crosshair X 스타일의 다크 오렌지 프리미엄 게이밍 UI
- 100% 칼사각 & 중심 완전 고정 & 반투명 완벽 차단 (Pure Solid 255)
- 발사 애니메이션 (Firing Animation - 사격 시 반동 확산 효과)
- 프로게이머 프리셋 라이브러리 (TenZ, Yay, Aspas, Demon1 등)
- 커스텀 PNG 이미지 크로스헤어 로더
- 실시간 미니 프리뷰 캔버스
- 전역 단축키 & 시스템 트레이(숨겨진 아이콘) 우클릭 종료 지원
"""
import ctypes
from ctypes import wintypes
import json
import math
import os
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.request
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox, simpledialog, filedialog

from PIL import Image, ImageDraw, ImageTk
import pystray

# ---------------- Win32 DPI & APIs ----------------
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
try:
    dwmapi = ctypes.windll.dwmapi
except Exception:
    dwmapi = None

def apply_dark_titlebar(window):
    """Windows 11 / 10 다크 모드 및 커스텀 캡션바 색상 적용 (하얀색 타이틀바 완전 제거)"""
    if not dwmapi:
        return
    window.update_idletasks()
    try:
        hwnd = user32.GetParent(window.winfo_id()) or window.winfo_id()
    except Exception:
        hwnd = window.winfo_id()

    val = ctypes.c_int(1)
    # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 11 / Windows 10 20H1+), 19 (Windows 10 이전)
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), 4)
    except Exception:
        pass
    try:
        dwmapi.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(val), 4)
    except Exception:
        pass

    # DWMWA_CAPTION_COLOR = 35 (Windows 11 22000+) - 0x00BBGGRR -> #0D0E10 (0x00100E0D)
    try:
        caption_color = ctypes.c_int(0x00100E0D)
        dwmapi.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(caption_color), 4)
    except Exception:
        pass

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOPMOST = 0x00000008
HWND_TOPMOST = -1
SWP_NOMOVE, SWP_NOSIZE, SWP_NOACTIVATE = 0x2, 0x1, 0x10

VK = {
    "F8": 0x77, "F9": 0x78, "F10": 0x79, "F12": 0x7B,
    "CTRL": 0x11, "SHIFT": 0x10, "LBUTTON": 0x01
}


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


user32.GetDC.restype = wintypes.HDC
user32.GetDC.argtypes = [wintypes.HWND]
user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.GetParent.restype = wintypes.HWND
user32.GetParent.argtypes = [wintypes.HWND]
user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_long]
user32.SetWindowPos.argtypes = [
    wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, ctypes.c_uint
]
user32.UpdateLayeredWindow.argtypes = [
    wintypes.HWND, wintypes.HDC, ctypes.POINTER(wintypes.POINT),
    ctypes.POINTER(wintypes.SIZE), wintypes.HDC,
    ctypes.POINTER(wintypes.POINT), wintypes.DWORD,
    ctypes.POINTER(BLENDFUNCTION), wintypes.DWORD
]
gdi32.CreateCompatibleDC.restype = wintypes.HDC
gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC, ctypes.c_void_p, wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD
]
gdi32.SelectObject.restype = wintypes.HGDIOBJ
gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteDC.argtypes = [wintypes.HDC]

APP_DIR = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else sys.argv[0]))
CFG_PATH = os.path.join(APP_DIR, "crosspro_profiles.json")
CANVAS = 361  # 오버레이 캔버스 크기 (px)

CURRENT_VERSION = "v1.0.0"
GITHUB_REPO = "OKHDEV/CrossPro"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

def parse_semver(v_str):
    nums = re.findall(r'\d+', str(v_str))
    return tuple(map(int, nums)) if nums else (0, 0, 0)

def is_newer_version(remote_v, local_v):
    return parse_semver(remote_v) > parse_semver(local_v)

def apply_update_and_restart(update_file_path):
    target_exe = os.path.abspath(sys.executable if getattr(sys, "frozen", False) else sys.argv[0])
    bat_path = os.path.join(APP_DIR, "_apply_update.bat")
    pid = os.getpid()
    
    bat_content = f"""@echo off
setlocal
set OLD_PID={pid}
set TARGET_EXE="{target_exe}"
set NEW_EXE="{update_file_path}"

:wait_loop
timeout /t 1 /nobreak >nul
tasklist /fi "PID eq %OLD_PID%" 2>nul | findstr /i "%OLD_PID%" >nul
if not errorlevel 1 goto wait_loop

copy /y %NEW_EXE% %TARGET_EXE% >nul
del %NEW_EXE% >nul

start "" %TARGET_EXE%

(goto) 2>nul & del "%~f0"
"""
    try:
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0
        
        subprocess.Popen(["cmd.exe", "/c", bat_path], startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW)
    except Exception as e:
        print("Update restart error:", e)
    sys.exit(0)

# ---------------- Crosshair X 테마 팔레트 ----------------
class CXTheme:
    BG_MAIN = "#121316"        # 메인 배경
    BG_SIDEBAR = "#0D0E10"     # 좌측 사이드바
    BG_CARD = "#191A1E"        # 카드 배경
    BG_CARD_BORDER = "#25272F" # 카드 테두리
    BG_INPUT = "#131417"       # 인풋 배경
    
    ACCENT_ORANGE = "#FF6B00"  # 시그니처 앰버 오렌지
    ACCENT_HOVER = "#FF8533"   # 호버 오렌지
    ACCENT_ACTIVE = "#E05E00"  # 클릭 액티브 오렌지
    
    TEXT_MAIN = "#FFFFFF"      # 메인 텍스트
    TEXT_MUTED = "#8E929B"     # 보조 텍스트
    TEXT_DIM = "#565A63"       # 디밍 텍스트


def get_icon_image():
    base_dir = getattr(sys, "_MEIPASS", APP_DIR)
    ico_path = os.path.join(base_dir, "icon.ico")
    if not os.path.exists(ico_path):
        ico_path = os.path.join(APP_DIR, "icon.ico")
    if os.path.exists(ico_path):
        try:
            return Image.open(ico_path), ico_path
        except Exception:
            pass

    # 인메모리 생성 fallback
    img = Image.new("RGBA", (64, 64), (18, 19, 22, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([28, 8, 35, 55], fill=(255, 107, 0, 255))
    draw.rectangle([8, 28, 55, 35], fill=(255, 107, 0, 255))
    return img, None


# ---------------- 기본 프로필 및 프리셋 ----------------
DEFAULT = {
    "name": "기본 녹색",
    "use_image": False,
    "image_path": "",
    "image_scale": 1.0,
    "image_filter": "sharp",  # "sharp" (칼사각 픽셀) or "smooth" (부드러운 사진 스무딩)
    "img_anchor_x": None,
    "img_anchor_y": None,
    
    # 센터 도트
    "dot_on": False,
    "dot_shape": "사각",      # 사각, 마름모, 원, 링
    "dot_size": 2.0,
    "dot_opacity": 1.0,
    "dot_color": "#00FF00",
    
    # 라인 (십자선)
    "line_on": True,
    "line_shape": "기본",
    "line_color": "#00FF00",
    "line_opacity": 1.0,
    "line_len": 6.0,
    "line_thick": 2.0,
    "line_gap": 3.0,
    "line_rot": 0.0,
    "arm_top": True,
    "arm_bottom": True,
    "arm_left": True,
    "arm_right": True,
    
    # 외곽선
    "outline_on": True,
    "outline_thick": 1.0,
    "outline_opacity": 1.0,
    "outline_color": "#000000",
    
    # 레이어 및 위치
    "layer_scale": 1.0,
    "offset_x": 0.0,
    "offset_y": 0.0,
    
    # 발사 애니메이션 (Firing Animation)
    "fire_anim_on": False,
    "fire_spread": 4.0,       # 사격 시 벌어지는 픽셀
    "fire_decay": 0.85,       # 복귀 속도
}

PRO_PRESETS = {
    "TenZ (청록 십자)": {
        **DEFAULT, "name": "TenZ (청록 십자)",
        "line_on": True, "line_color": "#00FFFF", "line_len": 4.0, "line_thick": 2.0, "line_gap": 2.0,
        "outline_on": True, "outline_thick": 1.0, "dot_on": False
    },
    "Yay (녹색 조준점)": {
        **DEFAULT, "name": "Yay (녹색 조준점)",
        "line_on": False, "dot_on": True, "dot_shape": "사각", "dot_size": 2.0, "dot_color": "#00FF00",
        "outline_on": True, "outline_thick": 1.0
    },
    "Demon1 (미니 화이트 도트)": {
        **DEFAULT, "name": "Demon1 (미니 화이트 도트)",
        "line_on": False, "dot_on": True, "dot_shape": "사각", "dot_size": 2.0, "dot_color": "#FFFFFF",
        "outline_on": True, "outline_thick": 1.0
    },
    "Aspas (레드 클래식)": {
        **DEFAULT, "name": "Aspas (레드 클래식)",
        "line_on": True, "line_color": "#FF2B2B", "line_len": 4.0, "line_thick": 2.0, "line_gap": 2.0,
        "outline_on": True, "outline_thick": 1.0, "dot_on": False
    },
    "하트 조준선 (Heart)": {
        **DEFAULT, "name": "하트 조준선 (Heart)",
        "line_on": True, "line_color": "#FF4D88", "line_len": 3.0, "line_thick": 3.0, "line_gap": 1.0,
        "line_rot": 45.0, "outline_on": True, "outline_thick": 1.0, "dot_on": True, "dot_shape": "마름모", "dot_size": 2.0
    },
    "스나이퍼 링 (Circle Ring)": {
        **DEFAULT, "name": "스나이퍼 링 (Circle Ring)",
        "line_on": True, "line_color": "#00FFA3", "line_len": 4.0, "line_thick": 1.0, "line_gap": 5.0,
        "dot_on": True, "dot_shape": "링", "dot_size": 6.0, "dot_color": "#00FFA3", "outline_on": True
    }
}


def hex_rgb(h):
    h = h.lstrip("#")
    if len(h) == 6:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    return (0, 255, 0)


def load_store():
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for p in data.get("profiles", {}).values():
                for k, v in DEFAULT.items():
                    p.setdefault(k, v)
            if data.get("current") not in data.get("profiles", {}):
                data["current"] = next(iter(data["profiles"]))
            return data
        except Exception:
            pass
    store = {
        "current": "TenZ (청록 십자)",
        "profiles": dict(PRO_PRESETS)
    }
    return store


def save_store(store):
    try:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ---------------- Overlay ----------------
class Overlay:
    def __init__(self, root):
        self.root = root
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.geometry(f"{CANVAS}x{CANVAS}+0+0")
        self.visible = True
        self.last = None
        self.current_fire_spread = 0.0
        self.cached_custom_image = None
        self.cached_image_path = ""
        self.win.update_idletasks()
        self.hwnd = user32.GetParent(self.win.winfo_id()) or self.win.winfo_id()
        ex = user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(
            self.hwnd, GWL_EXSTYLE,
            ex | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST
        )

    def keep_on_top(self):
        if self.visible:
            user32.SetWindowPos(
                self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
            )

    def toggle(self):
        self.visible = not self.visible
        if self.visible:
            self.win.deiconify()
            self.win.update_idletasks()
            if self.last:
                self.draw(self.last)
        else:
            self.win.withdraw()

    # ---------- 100% 솔리드 칼사각 렌더링 코어 ----------
    def render(self, c, cx, cy, dynamic_gap_offset=0.0):
        img = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 커스텀 PNG 이미지 모드
        if c.get("use_image", False) and c.get("image_path"):
            p = c.get("image_path")
            if p != self.cached_image_path or not self.cached_custom_image:
                if os.path.exists(p):
                    try:
                        self.cached_custom_image = Image.open(p).convert("RGBA")
                        self.cached_image_path = p
                    except Exception:
                        self.cached_custom_image = None
            if self.cached_custom_image:
                scale = float(c.get("image_scale", 1.0)) * float(c.get("layer_scale", 1.0))
                orig_w, orig_h = self.cached_custom_image.size
                nw, nh = max(1, int(round(orig_w * scale))), max(1, int(round(orig_h * scale)))
                # 렌더링 필터: sharp (NEAREST - 칼사각 픽셀) vs smooth (BILINEAR - 사진급 부드러운 스무딩)
                filt = c.get("image_filter", "sharp")
                resample = Image.Resampling.BILINEAR if filt == "smooth" else Image.Resampling.NEAREST
                resized = self.cached_custom_image.resize((nw, nh), resample)
                
                # 중심점 (Anchor Point): 사용자가 직접 픽셀로 지정한 위치 (기본값: 이미지 정중앙)
                raw_ax = c.get("img_anchor_x")
                raw_ay = c.get("img_anchor_y")
                ax = float(raw_ax) if raw_ax is not None else (orig_w / 2.0)
                ay = float(raw_ay) if raw_ay is not None else (orig_h / 2.0)

                # 화면 중심(cx, cy)에 해당 앵커 픽셀이 일치하도록 시작 좌표(px, py) 계산
                px = int(round(cx - ax * scale))
                py = int(round(cy - ay * scale))
                img.alpha_composite(resized, (px, py))
                return img

        # 색상 및 알파
        col_line = hex_rgb(c.get("line_color", "#00FF00"))
        col_dot = hex_rgb(c.get("dot_color", "#00FF00"))
        col_out = hex_rgb(c.get("outline_color", "#000000"))

        alpha_line = int(255 * float(c.get("line_opacity", 1.0)))
        alpha_dot = int(255 * float(c.get("dot_opacity", 1.0)))
        alpha_out = int(255 * float(c.get("outline_opacity", 1.0)))

        outline_on = c.get("outline_on", True)
        outline_thick = float(c.get("outline_thick", 1.0))
        scale = float(c.get("layer_scale", 1.0))

        def draw_solid_box(center_x, center_y, width, height, thick_out, fill_col, fill_alpha):
            """100% 완전 불투명 솔리드 칼사각 박스 (반투명 0%, 모서리 직각, 중심 대칭)"""
            w_px = max(1, int(round(width * scale)))
            h_px = max(1, int(round(height * scale)))
            o_px = max(1, int(round(thick_out * scale))) if (outline_on and thick_out > 0) else 0

            x1 = int(round(center_x - w_px / 2.0))
            y1 = int(round(center_y - h_px / 2.0))
            x2 = x1 + w_px - 1
            y2 = y1 + h_px - 1

            if o_px > 0:
                draw.rectangle([x1 - o_px, y1 - o_px, x2 + o_px, y2 + o_px], fill=col_out + (alpha_out,))
            draw.rectangle([x1, y1, x2, y2], fill=fill_col + (fill_alpha,))

        # 1. 십자선 (Lines)
        if c.get("line_on", True):
            L = float(c.get("line_len", 6.0))
            T = float(c.get("line_thick", 2.0))
            G = float(c.get("line_gap", 3.0)) + dynamic_gap_offset
            rot = float(c.get("line_rot", 0.0)) % 360.0

            if L > 0 and T > 0:
                if rot == 0.0:
                    L_px = max(1, int(round(L * scale)))
                    T_px = max(1, int(round(T * scale)))
                    G_px = int(round(G * scale))
                    o_px = max(1, int(round(outline_thick * scale))) if (outline_on and outline_thick > 0) else 0

                    cx_int = int(round(cx))
                    cy_int = int(round(cy))

                    if T_px % 2 == 0:
                        ht = T_px // 2
                        x_left = cx_int - ht + 1
                        x_right = cx_int + ht
                        y_top = cy_int - ht + 1
                        y_bot = cy_int + ht
                    else:
                        ht = T_px // 2
                        x_left = cx_int - ht
                        x_right = cx_int + ht
                        y_top = cy_int - ht
                        y_bot = cy_int + ht

                    arms_boxes = []
                    # Right
                    if c.get("arm_right", True):
                        arms_boxes.append((x_right + G_px, y_top, x_right + G_px + L_px - 1, y_bot))
                    # Left
                    if c.get("arm_left", True):
                        arms_boxes.append((x_left - G_px - L_px + 1, y_top, x_left - G_px, y_bot))
                    # Bottom
                    if c.get("arm_bottom", True):
                        arms_boxes.append((x_left, y_bot + G_px, x_right, y_bot + G_px + L_px - 1))
                    # Top
                    if c.get("arm_top", True):
                        arms_boxes.append((x_left, y_top - G_px - L_px + 1, x_right, y_top - G_px))

                    # 1단계: 외곽선 레이어 전체 먼저 렌더링 (어떤 팔도 다른 팔의 본체를 침범/깎아먹지 않음)
                    if o_px > 0:
                        for bx1, by1, bx2, by2 in arms_boxes:
                            draw.rectangle([bx1 - o_px, by1 - o_px, bx2 + o_px, by2 + o_px], fill=col_out + (alpha_out,))
                    # 2단계: 본체 레이어 전체 렌더링 (외곽선 위에 온전하게 안착)
                    for bx1, by1, bx2, by2 in arms_boxes:
                        draw.rectangle([bx1, by1, bx2, by2], fill=col_line + (alpha_line,))
                else:
                    # 회전 모드 (4배 슈퍼샘플링)
                    SS = 4
                    N = CANVAS * SS
                    rot_img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
                    rdraw = ImageDraw.Draw(rot_img)
                    mcx, mcy = cx * SS, cy * SS
                    o_ss = outline_thick * scale * SS if outline_on else 0

                    arms = [("arm_right", 0), ("arm_bottom", 90), ("arm_left", 180), ("arm_top", 270)]
                    rot_polys = []
                    rot_opolys = []
                    for arm_key, base_angle in arms:
                        if not c.get(arm_key, True):
                            continue
                        rad = math.radians(rot + base_angle)
                        dx, dy = math.cos(rad), math.sin(rad)
                        x1 = mcx + dx * (G * scale * SS)
                        y1 = mcy + dy * (G * scale * SS)
                        x2 = mcx + dx * ((G + L) * scale * SS)
                        y2 = mcy + dy * ((G + L) * scale * SS)

                        nx, ny = -dy * (T * scale * SS) / 2.0, dx * (T * scale * SS) / 2.0
                        poly = [
                            (x1 + nx, y1 + ny), (x2 + nx, y2 + ny),
                            (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)
                        ]
                        rot_polys.append(poly)
                        if o_ss > 0:
                            onx, ony = -dy * ((T + 2 * outline_thick) * scale * SS) / 2.0, dx * ((T + 2 * outline_thick) * scale * SS) / 2.0
                            ox1, oy1 = x1 - dx * o_ss, y1 - dy * o_ss
                            ox2, oy2 = x2 + dx * o_ss, y2 + dy * o_ss
                            opoly = [
                                (ox1 + onx, oy1 + ony), (ox2 + onx, oy2 + ony),
                                (ox2 - onx, oy2 - ony), (ox1 - onx, oy1 - ony)
                            ]
                            rot_opolys.append(opoly)

                    if o_ss > 0:
                        for opoly in rot_opolys:
                            rdraw.polygon(opoly, fill=col_out + (alpha_out,))
                    for poly in rot_polys:
                        rdraw.polygon(poly, fill=col_line + (alpha_line,))

                    rot_scaled = rot_img.resize((CANVAS, CANVAS), Image.Resampling.LANCZOS)
                    img.alpha_composite(rot_scaled)

        # 2. 센터 도트 (Center Dot)
        if c.get("dot_on", False):
            s = float(c.get("dot_size", 2.0))
            shape = c.get("dot_shape", "사각")

            if shape == "사각":
                # 100% 완전 불투명 칼사각
                draw_solid_box(cx, cy, s, s, outline_thick, col_dot, alpha_dot)
            elif shape == "마름모":
                SS = 4
                N = CANVAS * SS
                d_img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
                ddraw = ImageDraw.Draw(d_img)
                mcx, mcy = cx * SS, cy * SS
                o_ss = outline_thick * scale * SS if outline_on else 0.0
                hs = (s * scale * SS) / 2.0

                if o_ss > 0:
                    poly_o = [(mcx, mcy - hs - o_ss), (mcx + hs + o_ss, mcy), (mcx, mcy + hs + o_ss), (mcx - hs - o_ss, mcy)]
                    ddraw.polygon(poly_o, fill=col_out + (alpha_out,))
                poly_i = [(mcx, mcy - hs), (mcx + hs, mcy), (mcx, mcy + hs), (mcx - hs, mcy)]
                ddraw.polygon(poly_i, fill=col_dot + (alpha_dot,))

                img.alpha_composite(d_img.resize((CANVAS, CANVAS), Image.Resampling.LANCZOS))
            elif shape == "원":
                SS = 4
                N = CANVAS * SS
                d_img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
                ddraw = ImageDraw.Draw(d_img)
                mcx, mcy = cx * SS, cy * SS
                o_ss = outline_thick * scale * SS if outline_on else 0.0
                rad = (s * scale * SS) / 2.0

                if o_ss > 0:
                    ddraw.ellipse([mcx - rad - o_ss, mcy - rad - o_ss, mcx + rad + o_ss, mcy + rad + o_ss], fill=col_out + (alpha_out,))
                ddraw.ellipse([mcx - rad, mcy - rad, mcx + rad, mcy + rad], fill=col_dot + (alpha_dot,))

                img.alpha_composite(d_img.resize((CANVAS, CANVAS), Image.Resampling.LANCZOS))
            elif shape == "링":
                SS = 4
                N = CANVAS * SS
                d_img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
                ddraw = ImageDraw.Draw(d_img)
                mcx, mcy = cx * SS, cy * SS
                o_ss = outline_thick * scale * SS if outline_on else 0.0
                rad = (s * scale * SS) / 2.0
                t_ss = max(1.0, 1.5 * scale * SS)

                if o_ss > 0:
                    ddraw.ellipse([mcx - rad - o_ss, mcy - rad - o_ss, mcx + rad + o_ss, mcy + rad + o_ss], fill=col_out + (alpha_out,))
                    ddraw.ellipse([mcx - rad + t_ss + o_ss, mcy - rad + t_ss + o_ss, mcx + rad - t_ss - o_ss, mcy + rad - t_ss - o_ss], fill=(0, 0, 0, 0))
                ddraw.ellipse([mcx - rad, mcy - rad, mcx + rad, mcy + rad], fill=col_dot + (alpha_dot,))
                ddraw.ellipse([mcx - rad + t_ss, mcy - rad + t_ss, mcx + rad - t_ss, mcy + rad - t_ss], fill=(0, 0, 0, 0))

                img.alpha_composite(d_img.resize((CANVAS, CANVAS), Image.Resampling.LANCZOS))

        return img

    def draw(self, c):
        self.last = c
        if not self.visible:
            return
        sw = user32.GetSystemMetrics(0)
        sh = user32.GetSystemMetrics(1)

        # 화면 정중앙 픽셀 기준
        tx = sw / 2.0 + float(c.get("offset_x", 0.0))
        ty = sh / 2.0 + float(c.get("offset_y", 0.0))
        wx = int(math.floor(tx)) - CANVAS // 2
        wy = int(math.floor(ty)) - CANVAS // 2

        cx = CANVAS / 2.0
        cy = CANVAS / 2.0

        img = self.render(c, cx, cy, self.current_fire_spread).convert("RGBa")
        self.blit(img.tobytes("raw", "BGRa"), wx, wy)

    def blit(self, data, x, y):
        hdc_screen = user32.GetDC(None)
        memdc = gdi32.CreateCompatibleDC(hdc_screen)
        bmi = BITMAPINFOHEADER()
        bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.biWidth, bmi.biHeight = CANVAS, -CANVAS
        bmi.biPlanes, bmi.biBitCount = 1, 32
        bits = ctypes.c_void_p()
        hbmp = gdi32.CreateDIBSection(memdc, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        ctypes.memmove(bits, data, len(data))
        old = gdi32.SelectObject(memdc, hbmp)
        pt, src = wintypes.POINT(x, y), wintypes.POINT(0, 0)
        size = wintypes.SIZE(CANVAS, CANVAS)
        blend = BLENDFUNCTION(0, 0, 255, 1)
        user32.UpdateLayeredWindow(
            self.hwnd, hdc_screen, ctypes.byref(pt), ctypes.byref(size),
            memdc, ctypes.byref(src), 0, ctypes.byref(blend), 2
        )
        gdi32.SelectObject(memdc, old)
        gdi32.DeleteObject(hbmp)
        gdi32.DeleteDC(memdc)
        user32.ReleaseDC(None, hdc_screen)


# ---------------- Crosshair X 스타일 커스텀 위젯 ----------------
class ModernSlider(tk.Frame):
    """Crosshair X 스타일 오렌지 채움 슬라이더"""
    def __init__(self, parent, label, from_, to, step=0.1, initial=0.0, command=None, width=190):
        super().__init__(parent, bg=CXTheme.BG_CARD)
        self.from_ = from_
        self.to = to
        self.step = step
        self.command = command
        self.val = initial
        
        hdr = tk.Frame(self, bg=CXTheme.BG_CARD)
        hdr.pack(fill="x", pady=(0, 2))
        self.lbl_title = tk.Label(hdr, text=label, bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 9))
        self.lbl_title.pack(side="left")
        
        self.val_entry = tk.Entry(hdr, bg=CXTheme.BG_INPUT, fg=CXTheme.TEXT_MAIN, insertbackground=CXTheme.ACCENT_ORANGE,
                                  relief="flat", width=5, justify="right", font=("Segoe UI", 9))
        self.val_entry.pack(side="right")
        self.val_entry.insert(0, self._fmt(initial))
        self.val_entry.bind("<Return>", self._on_entry)
        self.val_entry.bind("<FocusOut>", self._on_entry)
        
        self.canvas_w = width
        self.canvas_h = 16
        self.cv = tk.Canvas(self, width=self.canvas_w, height=self.canvas_h, bg=CXTheme.BG_CARD, highlightthickness=0)
        self.cv.pack(fill="x")
        self.cv.bind("<B1-Motion>", self._on_drag)
        self.cv.bind("<Button-1>", self._on_drag)
        
        self.draw_slider()

    def _fmt(self, v):
        return f"{v:.2f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))

    def set_value(self, val):
        self.val = max(self.from_, min(self.to, float(val)))
        self.val_entry.delete(0, tk.END)
        self.val_entry.insert(0, self._fmt(self.val))
        self.draw_slider()

    def _on_entry(self, event=None):
        try:
            v = float(self.val_entry.get())
            self.val = max(self.from_, min(self.to, v))
        except Exception:
            pass
        self.set_value(self.val)
        if self.command:
            self.command(self.val)

    def _on_drag(self, event):
        ratio = max(0.0, min(1.0, (event.x - 8) / (self.canvas_w - 16)))
        raw = self.from_ + ratio * (self.to - self.from_)
        if self.step >= 1.0:
            self.val = round(raw)
        else:
            self.val = round(round(raw / self.step) * self.step, 2)
        self.val = max(self.from_, min(self.to, self.val))
        
        self.val_entry.delete(0, tk.END)
        self.val_entry.insert(0, self._fmt(self.val))
        self.draw_slider()
        if self.command:
            self.command(self.val)

    def draw_slider(self):
        self.cv.delete("all")
        cy = self.canvas_h // 2
        x_start = 8
        x_end = self.canvas_w - 8
        total_w = x_end - x_start
        
        ratio = (self.val - self.from_) / (self.to - self.from_) if self.to > self.from_ else 0.0
        knob_x = x_start + ratio * total_w
        
        # 회색 배경 트랙
        self.cv.create_line(x_start, cy, x_end, cy, fill="#2C2E35", width=4, capstyle="round")
        # 채워진 주황 트랙
        if knob_x > x_start:
            self.cv.create_line(x_start, cy, knob_x, cy, fill=CXTheme.ACCENT_ORANGE, width=4, capstyle="round")
        # 노브 (흰색 원형 손잡이 + 주황 테두리)
        r = 5
        self.cv.create_oval(knob_x - r, cy - r, knob_x + r, cy + r, fill="#FFFFFF", outline=CXTheme.ACCENT_ORANGE, width=2)


class ToggleSwitch(tk.Canvas):
    """Crosshair X 스타일 온/오프 슬라이딩 스위치"""
    def __init__(self, parent, initial=False, command=None, width=38, height=20):
        super().__init__(parent, width=width, height=height, bg=CXTheme.BG_CARD, highlightthickness=0, cursor="hand2")
        self.state = initial
        self.command = command
        self.w = width
        self.h = height
        self.bind("<Button-1>", self.toggle)
        self.draw()

    def toggle(self, event=None):
        self.state = not self.state
        self.draw()
        if self.command:
            self.command(self.state)

    def set_state(self, s):
        self.state = bool(s)
        self.draw()

    def draw(self):
        self.delete("all")
        r = self.h // 2
        # 배경 트랙
        bg_col = CXTheme.ACCENT_ORANGE if self.state else "#2A2C34"
        self.create_line(r, r, self.w - r, r, fill=bg_col, width=self.h, capstyle="round")
        # 스위치 노브
        knob_x = (self.w - r) if self.state else r
        self.create_oval(knob_x - r + 2, 2, knob_x + r - 2, self.h - 2, fill="#FFFFFF", outline="")


class SplashScreen:
    """프로그램 시작 시 로고 애니메이션 및 자동 업데이트 확인 스플래시 창"""
    def __init__(self, root, on_ready):
        self.root = root
        self.on_ready = on_ready
        
        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.configure(bg=CXTheme.BG_MAIN)
        
        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()
        w, h = 460, 290
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.win.geometry(f"{w}x{h}+{x}+{y}")
        self.win.attributes("-topmost", True)
        
        card = tk.Frame(self.win, bg=CXTheme.BG_MAIN, highlightthickness=1,
                        highlightbackground=CXTheme.BG_CARD_BORDER, padx=24, pady=24)
        card.pack(fill="both", expand=True)
        
        # CrossPro 로고 캔버스
        self.logo_cv = tk.Canvas(card, width=68, height=68, bg=CXTheme.BG_MAIN, highlightthickness=0)
        self.logo_cv.pack(pady=(4, 8))
        self.draw_logo()
        
        # 타이틀
        t_frame = tk.Frame(card, bg=CXTheme.BG_MAIN)
        t_frame.pack()
        tk.Label(t_frame, text="Cross", fg="#FFFFFF", bg=CXTheme.BG_MAIN, font=("Segoe UI", 20, "bold")).pack(side="left")
        tk.Label(t_frame, text="Pro", fg=CXTheme.ACCENT_ORANGE, bg=CXTheme.BG_MAIN, font=("Segoe UI", 20, "bold")).pack(side="left")
        
        # 서브타이틀
        tk.Label(card, text="ULTIMATE FPS CROSSHAIR SYSTEM", fg=CXTheme.TEXT_MUTED, bg=CXTheme.BG_MAIN,
                 font=("Segoe UI", 8, "bold")).pack(pady=(2, 14))
        
        # 프로그레스 바 캔버스
        self.bar_w = 360
        self.bar_cv = tk.Canvas(card, width=self.bar_w, height=6, bg="#1C1D22", highlightthickness=0)
        self.bar_cv.pack(pady=(0, 10))
        
        # 상태 메시지
        self.status_lbl = tk.Label(card, text="시스템 초기화 및 업데이트 확인 중...",
                                   fg=CXTheme.TEXT_MAIN, bg=CXTheme.BG_MAIN, font=("Segoe UI", 9))
        self.status_lbl.pack(pady=(0, 4))
        
        # 버전 표시
        tk.Label(card, text=f"현재 버전: {CURRENT_VERSION}", fg=CXTheme.TEXT_DIM, bg=CXTheme.BG_MAIN,
                 font=("Segoe UI", 8)).pack(side="bottom")
        
        self.win.update()
        
        # 스레드 안전 메시지 큐 및 폴러
        self.msg_queue = queue.Queue()
        self.win.after(30, self._poll_queue)
        threading.Thread(target=self._check_update_thread, daemon=True).start()

    def _poll_queue(self):
        try:
            while True:
                item = self.msg_queue.get_nowait()
                action = item[0]
                if action == "progress":
                    self.set_progress(item[1])
                elif action == "status":
                    self.set_status(item[1])
                elif action == "done":
                    self._finish_splash()
                    return
        except queue.Empty:
            pass
        if hasattr(self, "win") and self.win.winfo_exists():
            self.win.after(30, self._poll_queue)

    def draw_logo(self):
        cv = self.logo_cv
        cv.delete("all")
        cv.create_oval(6, 6, 62, 62, outline="#2A2C34", width=2)
        cv.create_oval(14, 14, 54, 54, outline="#1E2026", width=1)
        cv.create_line(34, 10, 34, 25, fill=CXTheme.ACCENT_ORANGE, width=3, capstyle="round")
        cv.create_line(34, 43, 34, 58, fill=CXTheme.ACCENT_ORANGE, width=3, capstyle="round")
        cv.create_line(10, 34, 25, 34, fill=CXTheme.ACCENT_ORANGE, width=3, capstyle="round")
        cv.create_line(43, 34, 58, 34, fill=CXTheme.ACCENT_ORANGE, width=3, capstyle="round")
        cv.create_oval(31, 31, 37, 37, fill="#FFFFFF", outline=CXTheme.ACCENT_ORANGE, width=1)

    def set_progress(self, pct):
        self.bar_cv.delete("bar")
        fill_w = max(0, min(self.bar_w, int(self.bar_w * (pct / 100.0))))
        if fill_w > 0:
            self.bar_cv.create_line(0, 3, fill_w, 3, fill=CXTheme.ACCENT_ORANGE, width=6, capstyle="round", tags="bar")
        self.win.update_idletasks()

    def set_status(self, text):
        self.status_lbl.configure(text=text)
        self.win.update_idletasks()

    def _check_update_thread(self):
        self.msg_queue.put(("progress", 25))
        time.sleep(0.3)
        
        req = urllib.request.Request(
            GITHUB_RELEASES_API,
            headers={"User-Agent": "CrossPro-AutoUpdater"}
        )
        
        latest_tag = None
        asset_url = None
        asset_size = 0
        
        try:
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    latest_tag = data.get("tag_name", "")
                    for a in data.get("assets", []):
                        if a.get("name", "").lower().endswith(".exe"):
                            asset_url = a.get("browser_download_url")
                            asset_size = a.get("size", 0)
                            break
        except Exception:
            pass
        
        self.msg_queue.put(("progress", 50))
        
        if latest_tag and is_newer_version(latest_tag, CURRENT_VERSION):
            self.msg_queue.put(("status", f"새 버전 ({latest_tag}) 발견! 다운로드 준비 중..."))
            time.sleep(0.5)
            
            is_frozen = getattr(sys, "frozen", False)
            if asset_url and is_frozen:
                update_dest = os.path.join(APP_DIR, "CrossPro_update.exe")
                try:
                    with urllib.request.urlopen(asset_url, timeout=30.0) as dl_resp, open(update_dest, "wb") as out_file:
                        total_bytes = asset_size or int(dl_resp.headers.get("Content-Length", 0))
                        downloaded = 0
                        chunk_size = 65536
                        while True:
                            chunk = dl_resp.read(chunk_size)
                            if not chunk:
                                break
                            out_file.write(chunk)
                            downloaded += len(chunk)
                            pct = 50.0 + (downloaded / max(1, total_bytes)) * 45.0
                            self.msg_queue.put(("progress", pct))
                            self.msg_queue.put(("status", f"새 버전 다운로드 중... {downloaded/(1024*1024):.1f}MB / {total_bytes/(1024*1024):.1f}MB ({int(pct)}%)"))
                    
                    self.msg_queue.put(("progress", 100))
                    self.msg_queue.put(("status", "업데이트 다운로드 완료! 자동 설치 후 재실행합니다..."))
                    time.sleep(1.0)
                    apply_update_and_restart(update_dest)
                    return
                except Exception as e:
                    self.msg_queue.put(("status", f"다운로드 실패: {e}"))
                    time.sleep(1.0)
            else:
                self.msg_queue.put(("status", f"새 버전 ({latest_tag}) 출시됨 (개발 모드)"))
                time.sleep(1.0)
        elif latest_tag:
            self.msg_queue.put(("progress", 100))
            self.msg_queue.put(("status", f"최신 버전입니다! ({CURRENT_VERSION})"))
            time.sleep(0.6)
        else:
            self.msg_queue.put(("progress", 100))
            self.msg_queue.put(("status", f"CrossPro {CURRENT_VERSION} 시작 중..."))
            time.sleep(0.5)
            
        self.msg_queue.put(("done", None))

    def _finish_splash(self):
        try:
            self.win.destroy()
        except Exception:
            pass
        self.on_ready()


# ---------------- 메인 Crosshair X UI ----------------
class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Crosshair X - Ultimate Crosshair Pro")
        self.root.geometry("1080x740")
        self.root.minsize(980, 680)
        self.root.configure(bg=CXTheme.BG_MAIN)
        self.root.protocol("WM_DELETE_WINDOW", self.hide_settings)
        apply_dark_titlebar(self.root)
        self.root.after(100, lambda: apply_dark_titlebar(self.root))

        self.tray_icon = None
        self.icon_image, self.icon_path = get_icon_image()
        if self.icon_path and os.path.exists(self.icon_path):
            try:
                self.root.iconbitmap(self.icon_path)
            except Exception:
                pass

        self.store = load_store()
        self.sliders = {}
        self.toggles = {}
        self.keystate = {}
        self.settings_visible = True
        self._syncing = False
        self._draw_job = None
        self._save_job = None
        self.current_nav = "designer"  # "designer", "crosshairs", "position", "image", "keybinds"
        
        self.img_nudge_step = 1.0
        self.img_zoom_mode = "fit"
        self.cached_loaded_pil_img = None
        self.cached_loaded_pil_path = ""
        self.img_disp_scale = 1.0
        self.img_disp_ox = 0
        self.img_disp_oy = 0
        self.rendered_img_photo = None
        self.actual_preview_photo = None

        # 픽셀 브러시 스튜디오 상태
        self.pixel_brush_tool = "brush"    # "brush", "eraser", "anchor"
        self.pixel_brush_style = "sharp"   # "sharp" (칼사각 솔리드) vs "smooth" (사진급 스무스 펜)
        self.pixel_brush_size = 1          # 1px, 2px, 3px, 4px
        self.pixel_brush_opacity = 1.0     # 1.0, 0.75, 0.5, 0.25
        self.pixel_brush_color = (0, 255, 0, 255)
        self.pixel_brush_hex = "#00FF00"
        self.show_pixel_grid = True
        self.default_pixel_path = os.path.join(APP_DIR, "custom_pixel_reticle.png")

        # 전역 마우스 휠 스크롤 바인딩
        self.root.bind_all("<MouseWheel>", self._on_global_mousewheel)
        self.root.bind_all("<Button-4>", lambda e: self._scroll_active(-2))
        self.root.bind_all("<Button-5>", lambda e: self._scroll_active(2))

        self.overlay = Overlay(self.root)
        self.build_ui()
        self.load_profile(self.store["current"])
        self.setup_tray()
        
        self.root.after(30, self.poll_keys)
        self.root.after(16, self.fire_anim_loop)
        self.root.after(1000, self.top_loop)

        # 시작 스플래시 창 실행 (로고 + 업데이트 자동 확인)
        self.splash = SplashScreen(self.root, on_ready=self.on_splash_done)

    def on_splash_done(self):
        self.root.deiconify()
        apply_dark_titlebar(self.root)

    def _on_global_mousewheel(self, event):
        delta = event.delta
        if not delta:
            return
        raw_steps = -1.0 * (delta / 120.0)
        steps = int(raw_steps * 2) if abs(raw_steps) >= 1.0 else (2 if raw_steps > 0 else -2)
        self._scroll_active(steps)

    def _scroll_active(self, units):
        cv = None
        if self.current_nav in ("designer", "position") and hasattr(self, "designer_canvas"):
            cv = self.designer_canvas
        elif self.current_nav == "crosshairs" and hasattr(self, "presets_canvas"):
            cv = self.presets_canvas
        elif self.current_nav == "image" and hasattr(self, "image_canvas"):
            cv = self.image_canvas
        elif self.current_nav == "keybinds" and hasattr(self, "keybinds_canvas"):
            cv = self.keybinds_canvas
        if cv and cv.winfo_exists():
            cv.yview_scroll(units, "units")

    @property
    def cfg(self):
        return self.store["profiles"][self.store["current"]]

    def setup_tray(self):
        try:
            menu = pystray.Menu(
                pystray.MenuItem("⚙️ 설정창 열기 / 닫기 (F9)", lambda icon, item: self.root.after(0, self.toggle_settings), default=True),
                pystray.MenuItem("👁️ 크로스헤어 켜기 / 끄기 (F8)", lambda icon, item: self.root.after(0, self.overlay.toggle)),
                pystray.MenuItem("🔄 다음 프로필로 전환 (F10)", lambda icon, item: self.root.after(0, self.next_profile)),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("❌ 프로그램 완전 종료 (Ctrl+F12)", lambda icon, item: self.root.after(0, self.quit))
            )
            self.tray_icon = pystray.Icon("CrossPro", self.icon_image, "Crosshair X Pro", menu)
            self.tray_icon.run_detached()
        except Exception as ex:
            print(f"Tray warning: {ex}")

    # ---------- 레이아웃 빌드 ----------
    def build_ui(self):
        # 상단 헤더 바
        top_bar = tk.Frame(self.root, bg=CXTheme.BG_SIDEBAR, height=44)
        top_bar.pack(fill="x", side="top")
        
        logo_frame = tk.Frame(top_bar, bg=CXTheme.BG_SIDEBAR)
        logo_frame.pack(side="left", padx=16)
        tk.Label(logo_frame, text="Crosshair", bg=CXTheme.BG_SIDEBAR, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 12, "bold")).pack(side="left")
        tk.Label(logo_frame, text=" X", bg=CXTheme.BG_SIDEBAR, fg=CXTheme.ACCENT_ORANGE, font=("Segoe UI", 13, "bold")).pack(side="left")
        
        # 우측 상단 상태 표시 배지
        top_right = tk.Frame(top_bar, bg=CXTheme.BG_SIDEBAR)
        top_right.pack(side="right", padx=16)
        
        self.badge_lbl = tk.Label(top_right, text="● 표시됨", bg=CXTheme.BG_SIDEBAR, fg=CXTheme.ACCENT_ORANGE, font=("Segoe UI", 9, "bold"))
        self.badge_lbl.pack(side="left", padx=8)
        
        btn_min = tk.Button(top_right, text="—", bg=CXTheme.BG_SIDEBAR, fg=CXTheme.TEXT_MUTED, relief="flat", bd=0,
                            cursor="hand2", font=("Segoe UI", 9), command=self.hide_settings)
        btn_min.pack(side="left", padx=4)
        btn_close = tk.Button(top_right, text="✕", bg=CXTheme.BG_SIDEBAR, fg=CXTheme.TEXT_MUTED, relief="flat", bd=0,
                              cursor="hand2", font=("Segoe UI", 10), command=self.hide_settings)
        btn_close.pack(side="left", padx=4)

        # 메인 영역 (사이드바 + 컨텐츠 뷰)
        body = tk.Frame(self.root, bg=CXTheme.BG_MAIN)
        body.pack(fill="both", expand=True)

        # 좌측 사이드바
        self.sidebar = tk.Frame(body, bg=CXTheme.BG_SIDEBAR, width=190)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.build_sidebar()

        # 우측 컨텐츠 영역
        self.content_area = tk.Frame(body, bg=CXTheme.BG_MAIN)
        self.content_area.pack(side="right", fill="both", expand=True, padx=16, pady=12)
        
        self.views = {}
        self.build_designer_view()
        self.build_presets_view()
        self.build_image_view()
        self.build_keybinds_view()
        
        self.switch_nav("designer")

    def build_sidebar(self):
        # 섹션 라벨 & 메뉴 버튼
        def section_label(text):
            tk.Label(self.sidebar, text=text, bg=CXTheme.BG_SIDEBAR, fg=CXTheme.TEXT_DIM,
                     font=("Segoe UI", 8, "bold"), anchor="w").pack(fill="x", padx=16, pady=(12, 4))

        self.nav_btns = {}
        def nav_button(name, key, icon=""):
            btn = tk.Button(self.sidebar, text=f"{icon}  {name}", bg=CXTheme.BG_SIDEBAR, fg=CXTheme.TEXT_MUTED,
                            activebackground="#1E1F24", activeforeground=CXTheme.TEXT_MAIN, relief="flat", bd=0,
                            anchor="w", padx=14, pady=7, font=("Segoe UI", 9, "bold"), cursor="hand2",
                            command=lambda: self.switch_nav(key))
            btn.pack(fill="x", pady=1)
            self.nav_btns[key] = btn

        section_label("골자 (CORE)")
        nav_button("십자선 (프리셋)", "crosshairs", "🎯")
        nav_button("위치 및 크기", "position", "📐")

        section_label("사용자 지정 (CUSTOM)")
        nav_button("디자이너 (메인)", "designer", "🎨")
        nav_button("이미지 오버레이", "image", "🖼️")
        nav_button("키바인드", "keybinds", "⌨️")

        # 하단 단축키 & 버전/업데이트 확인 버튼
        bot_box = tk.Frame(self.sidebar, bg="#131418", padx=10, pady=10)
        bot_box.pack(side="bottom", fill="x", padx=10, pady=12)
        tk.Label(bot_box, text=f"CrossPro {CURRENT_VERSION}",
                 bg="#131418", fg=CXTheme.ACCENT_ORANGE, font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(0, 2))
        tk.Label(bot_box, text="F8: 표시 토글 | F9: 설정창\nCtrl+F12: 프로그램 종료",
                 bg="#131418", fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 7), justify="left").pack(anchor="w", pady=(0, 6))
        
        btn_upd = tk.Button(bot_box, text="🔄 업데이트 확인", bg="#202228", fg=CXTheme.TEXT_MAIN,
                            activebackground=CXTheme.ACCENT_ORANGE, relief="flat", bd=0, padx=6, pady=3,
                            font=("Segoe UI", 8, "bold"), cursor="hand2", command=self.manual_check_update)
        btn_upd.pack(fill="x")

    def manual_check_update(self):
        def _check():
            req = urllib.request.Request(
                GITHUB_RELEASES_API,
                headers={"User-Agent": "CrossPro-AutoUpdater"}
            )
            try:
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        latest_tag = data.get("tag_name", "")
                        if latest_tag and is_newer_version(latest_tag, CURRENT_VERSION):
                            msg = f"새로운 업데이트 ({latest_tag})가 발견되었습니다!\n\n현재 버전: {CURRENT_VERSION}\n최신 버전: {latest_tag}\n\n프로그램을 재실행하시면 시작 로고 화면에서 자동으로 다운로드 및 설치됩니다."
                            self.root.after(0, lambda: messagebox.showinfo("새 버전 알림", msg, parent=self.root))
                        else:
                            self.root.after(0, lambda: messagebox.showinfo("최신 버전", f"현재 최신 버전({CURRENT_VERSION})을 사용하고 있습니다.", parent=self.root))
                    else:
                        self.root.after(0, lambda: messagebox.showwarning("업데이트 확인", "업데이트 서버 응답 오류가 발생했습니다.", parent=self.root))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showwarning("업데이트 확인", f"서버 연결 실패:\n{e}", parent=self.root))
        threading.Thread(target=_check, daemon=True).start()

    def switch_nav(self, key):
        self.current_nav = key
        for k, btn in self.nav_btns.items():
            if k == key:
                btn.configure(bg="#1E1F24", fg=CXTheme.ACCENT_ORANGE)
            else:
                btn.configure(bg=CXTheme.BG_SIDEBAR, fg=CXTheme.TEXT_MUTED)
                
        # 뷰 전환
        for v in self.views.values():
            v.pack_forget()
        if key == "position":
            # 위치 뷰는 디자이너 내 위치 카드로 이동 또는 디자이너 표시
            key = "designer"
        if key in self.views:
            self.views[key].pack(fill="both", expand=True)
            if key == "image":
                self.update_image_canvas()

    # ---------- 디자이너 뷰 (Crosshair X 핵심) ----------
    def build_designer_view(self):
        view = tk.Frame(self.content_area, bg=CXTheme.BG_MAIN)
        self.views["designer"] = view

        # 스크롤 가능한 메인 캔버스
        canvas = tk.Canvas(view, bg=CXTheme.BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(view, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CXTheme.BG_MAIN)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        cw = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.designer_canvas = canvas
        
        # 1. 상단: 레이어 / 실시간 미리보기 카드
        card_layer = self.create_card(scrollable_frame, "레이어 (Layers & Preview)")
        card_layer.pack(fill="x", pady=(0, 10))

        # 미리보기 캔버스 + 프로필 관리 컨트롤
        p_row = tk.Frame(card_layer, bg=CXTheme.BG_CARD)
        p_row.pack(fill="x", padx=12, pady=8)

        # 80x80 크로스헤어 실시간 미니 프리뷰
        self.preview_cv = tk.Canvas(p_row, width=80, height=80, bg="#111215", highlightthickness=1, highlightbackground=CXTheme.BG_CARD_BORDER)
        self.preview_cv.pack(side="left", padx=(0, 16))

        p_ctrl = tk.Frame(p_row, bg=CXTheme.BG_CARD)
        p_ctrl.pack(side="left", fill="both", expand=True)

        tk.Label(p_ctrl, text="현재 활성 프로필:", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        self.profile_cb = ttk.Combobox(p_ctrl, state="readonly", width=18, font=("Segoe UI", 9))
        self.profile_cb.pack(anchor="w", pady=2)
        self.profile_cb.bind("<<ComboboxSelected>>", lambda e: self.load_profile(self.profile_cb.get()))

        b_row = tk.Frame(p_ctrl, bg=CXTheme.BG_CARD)
        b_row.pack(anchor="w", pady=(6, 0))
        self.theme_btn(b_row, "＋ 새로 만들기", self.new_profile).pack(side="left", padx=(0, 4))
        self.theme_btn(b_row, "복제", self.dup_profile).pack(side="left", padx=2)
        self.theme_btn(b_row, "이름 변경", self.rename_profile).pack(side="left", padx=2)
        self.theme_btn(b_row, "삭제", self.del_profile).pack(side="left", padx=2)

        # 2컬럼 레이아웃 프레임
        col_frame = tk.Frame(scrollable_frame, bg=CXTheme.BG_MAIN)
        col_frame.pack(fill="both", expand=True)

        left_col = tk.Frame(col_frame, bg=CXTheme.BG_MAIN)
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 6))

        right_col = tk.Frame(col_frame, bg=CXTheme.BG_MAIN)
        right_col.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # [좌측 컬럼 1] 센터 도트 (Center Dot) 카드
        card_dot = self.create_card_with_toggle(left_col, "센터 도트 (Center Dot)", "dot_on")
        card_dot.pack(fill="x", pady=(0, 10))
        
        # 모양 선택 버튼 (사각, 마름모, 원, 링)
        f_shape = tk.Frame(card_dot, bg=CXTheme.BG_CARD)
        f_shape.pack(fill="x", padx=12, pady=(4, 6))
        tk.Label(f_shape, text="모양", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 9)).pack(side="left")
        
        self.dot_shape_btns = {}
        for s_name, s_icon in [("사각", "■"), ("마름모", "◆"), ("원", "●"), ("링", "○")]:
            b = tk.Button(f_shape, text=f"{s_icon} {s_name}", bg="#25272F", fg=CXTheme.TEXT_MAIN, relief="flat", bd=0,
                          padx=6, pady=2, font=("Segoe UI", 8), cursor="hand2",
                          command=lambda s=s_name: self.set_dot_shape(s))
            b.pack(side="left", padx=3)
            self.dot_shape_btns[s_name] = b

        self.add_slider(card_dot, "불투명도", "dot_opacity", 0.05, 1.0, 0.05)
        self.add_slider(card_dot, "지름 (크기 0.1)", "dot_size", 0.5, 20.0, 0.1)
        self.add_color_picker(card_dot, "도트 색상", "dot_color")

        # [좌측 컬럼 2] 라인 (Lines - 십자선) 카드
        card_line = self.create_card_with_toggle(left_col, "라인 (Lines - 십자선)", "line_on")
        card_line.pack(fill="x", pady=(0, 10))

        # 방향 활성화 버튼 [←] [↑] [→] [↓]
        f_dir = tk.Frame(card_line, bg=CXTheme.BG_CARD)
        f_dir.pack(fill="x", padx=12, pady=(4, 6))
        tk.Label(f_dir, text="표시됨", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 9)).pack(side="left")
        self.dir_btns = {}
        for key, icon in [("arm_left", "←"), ("arm_top", "↑"), ("arm_right", "→"), ("arm_bottom", "↓")]:
            b = tk.Button(f_dir, text=icon, bg=CXTheme.ACCENT_ORANGE, fg="#FFFFFF", relief="flat", bd=0, width=3,
                          cursor="hand2", font=("Segoe UI", 9, "bold"),
                          command=lambda k=key: self.toggle_arm(k))
            b.pack(side="left", padx=2)
            self.dir_btns[key] = b

        self.add_slider(card_line, "불투명도", "line_opacity", 0.05, 1.0, 0.05)
        self.add_slider(card_line, "길이", "line_len", 0.0, 40.0, 0.1)
        self.add_slider(card_line, "두께", "line_thick", 0.5, 15.0, 0.1)
        self.add_slider(card_line, "오프셋 (간격)", "line_gap", -5.0, 40.0, 0.1)
        self.add_slider(card_line, "회전", "line_rot", 0.0, 359.5, 0.5)
        self.add_color_picker(card_line, "선 색상", "line_color")

        # [우측 컬럼 1] 외곽선 (Outlines) 카드
        card_out = self.create_card_with_toggle(right_col, "외곽선 (Outlines)", "outline_on")
        card_out.pack(fill="x", pady=(0, 10))
        self.add_slider(card_out, "불투명도", "outline_opacity", 0.05, 1.0, 0.05)
        self.add_slider(card_out, "두께", "outline_thick", 0.5, 5.0, 0.1)
        self.add_color_picker(card_out, "윤곽선 색상", "outline_color")

        # [우측 컬럼 2] 레이어 설정 (위치 및 크기)
        card_pos = self.create_card(right_col, "레이어 설정 (Position & Scale)")
        card_pos.pack(fill="x", pady=(0, 10))
        self.add_slider(card_pos, "사이즈 (배율)", "layer_scale", 0.2, 3.0, 0.05)
        self.add_slider(card_pos, "X (가로 오프셋)", "offset_x", -150.0, 150.0, 0.1)
        self.add_slider(card_pos, "Y (세로 오프셋)", "offset_y", -150.0, 150.0, 0.1)

        f_nudge = tk.Frame(card_pos, bg=CXTheme.BG_CARD)
        f_nudge.pack(fill="x", padx=12, pady=6)
        for txt, dx, dy in [("◀", -1, 0), ("▲", 0, -1), ("▼", 0, 1), ("▶", 1, 0)]:
            tk.Button(f_nudge, text=txt, bg="#25272F", fg=CXTheme.TEXT_MAIN, relief="flat", bd=0, width=3,
                      cursor="hand2", command=lambda dx=dx, dy=dy: self.nudge(dx, dy)).pack(side="left", padx=2)
        tk.Button(f_nudge, text="중앙 리셋", bg="#25272F", fg=CXTheme.ACCENT_ORANGE, relief="flat", bd=0,
                  padx=6, cursor="hand2", command=self.center).pack(side="right")

        # [우측 컬럼 3] 발사 애니메이션 (Firing Animation - Crosshair X 시그니처!)
        card_fire = self.create_card_with_toggle(right_col, "발사 애니메이션 (Firing Animation)", "fire_anim_on")
        card_fire.pack(fill="x", pady=(0, 10))
        tk.Label(card_fire, text="마우스 좌클릭(사격) 시 크로스헤어가 반동처럼 반응합니다.",
                 bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=12, pady=(0, 4))
        self.add_slider(card_fire, "확산 픽셀 (Spread)", "fire_spread", 1.0, 15.0, 0.5)
        self.add_slider(card_fire, "복귀 속도 (Decay)", "fire_decay", 0.50, 0.95, 0.05)

    # ---------- 십자선 프로 프리셋 뷰 ----------
    def build_presets_view(self):
        view = tk.Frame(self.content_area, bg=CXTheme.BG_MAIN)
        self.views["crosshairs"] = view

        canvas = tk.Canvas(view, bg=CXTheme.BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(view, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CXTheme.BG_MAIN)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        cw = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.presets_canvas = canvas

        hdr = self.create_card(scrollable_frame, "프로게이머 & 인기 십자선 라이브러리")
        hdr.pack(fill="x", pady=(0, 12))
        tk.Label(hdr, text="원클릭으로 세계 최고 프로 선수들의 조준점을 즉시 적용하세요.",
                 bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=6)

        grid = tk.Frame(scrollable_frame, bg=CXTheme.BG_MAIN)
        grid.pack(fill="both", expand=True)

        for i, (pname, pdata) in enumerate(PRO_PRESETS.items()):
            row = i // 2
            col = i % 2
            card = tk.Frame(grid, bg=CXTheme.BG_CARD, highlightthickness=1, highlightbackground=CXTheme.BG_CARD_BORDER, padx=12, pady=10)
            card.grid(row=row, column=col, padx=6, pady=6, sticky="nsew")
            grid.columnconfigure(col, weight=1)

            tk.Label(card, text=pname, bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 10, "bold")).pack(anchor="w")
            tk.Label(card, text="공식 대회 검증 완료 크로스헤어", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(0, 6))

            btn = tk.Button(card, text="적용하기", bg=CXTheme.ACCENT_ORANGE, fg="#FFFFFF", relief="flat", bd=0,
                            padx=10, pady=4, font=("Segoe UI", 9, "bold"), cursor="hand2",
                            command=lambda pn=pname: self.apply_preset(pn))
            btn.pack(anchor="e")

    def apply_preset(self, name):
        if name in PRO_PRESETS:
            self.store["profiles"][name] = dict(PRO_PRESETS[name])
            self.load_profile(name)
            self.switch_nav("designer")

    # ---------- 픽셀 브러시 스튜디오 & 이미지 오버레이 뷰 ----------
    def build_image_view(self):
        view = tk.Frame(self.content_area, bg=CXTheme.BG_MAIN)
        self.views["image"] = view

        # 스크롤 가능한 메인 캔버스
        canvas = tk.Canvas(view, bg=CXTheme.BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(view, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=CXTheme.BG_MAIN)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        cw = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(cw, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.image_canvas = canvas

        # [카드 1] 픽셀 크로스헤어 파일 & 기본 설정
        card_file = self.create_card(scrollable_frame, "커스텀 픽셀 크로스헤어 & 이미지 설정")
        card_file.pack(fill="x", pady=(0, 10))

        tk.Label(card_file, text="내가 직접 붓으로 픽셀을 하나하나 찍어서 만드는 나만의 수제 크로스헤어 스튜디오입니다.",
                 bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w", padx=12, pady=(4, 6))

        row1 = tk.Frame(card_file, bg=CXTheme.BG_CARD)
        row1.pack(fill="x", padx=12, pady=4)
        self.img_toggle = ToggleSwitch(row1, initial=self.cfg.get("use_image", False), command=lambda s: self.set("use_image", s))
        self.img_toggle.pack(side="left", padx=(0, 8))
        tk.Label(row1, text="픽셀 / 이미지 오버레이 활성화", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(side="left")

        row2 = tk.Frame(card_file, bg=CXTheme.BG_CARD)
        row2.pack(fill="x", padx=12, pady=4)
        self.theme_btn(row2, "➕ 32x32", lambda: self.create_new_pixel_canvas(32)).pack(side="left", padx=(0, 4))
        self.theme_btn(row2, "64x64", lambda: self.create_new_pixel_canvas(64)).pack(side="left", padx=2)
        self.theme_btn(row2, "128x128", lambda: self.create_new_pixel_canvas(128)).pack(side="left", padx=2)
        self.theme_btn(row2, "256x256 (초미세)", lambda: self.create_new_pixel_canvas(256)).pack(side="left", padx=2)
        self.theme_btn(row2, "512x512 (사진급)", lambda: self.create_new_pixel_canvas(512)).pack(side="left", padx=2)
        self.theme_btn(row2, "➕ 직접 입력...", self.prompt_custom_pixel_canvas).pack(side="left", padx=2)
        self.theme_btn(row2, "📁 PNG 파일 열기...", self.browse_image).pack(side="left", padx=(8, 4))
        self.theme_btn(row2, "💾 저장", self.save_pixel_image_as).pack(side="left", padx=2)
        self.theme_btn(row2, "🗑️ 전체 지우기", self.clear_pixel_canvas).pack(side="left", padx=2)

        curr_p = self.cfg.get("image_path", "")
        self.img_path_lbl = tk.Label(card_file, text=f"현재 파일: {os.path.basename(curr_p) if curr_p else '기본 픽셀 캔버스 (32x32)'}",
                                     bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 8))
        self.img_path_lbl.pack(anchor="w", padx=12, pady=(2, 6))

        self.add_slider(card_file, "크로스헤어 배율", "image_scale", 0.05, 5.0, 0.05)

        # 화면 렌더링 필터 선택 바 (칼사각 솔리드 vs 부드러운 사진 스무딩)
        filt_row = tk.Frame(card_file, bg=CXTheme.BG_CARD)
        filt_row.pack(fill="x", padx=12, pady=(2, 6))
        tk.Label(filt_row, text="화면 출력 필터:", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))

        self.filter_btns = {}
        for f_key, f_name in [("sharp", "■ 칼사각 솔리드 (도트)"), ("smooth", "🌊 부드러운 사진 모드 (스무딩)")]:
            b = tk.Button(filt_row, text=f_name,
                          bg=CXTheme.ACCENT_ORANGE if self.cfg.get("image_filter", "sharp") == f_key else "#25272F",
                          fg="#FFFFFF" if self.cfg.get("image_filter", "sharp") == f_key else CXTheme.TEXT_MAIN,
                          relief="flat", bd=0, padx=8, pady=3, font=("Segoe UI", 8, "bold"), cursor="hand2",
                          command=lambda fk=f_key: self.set_image_filter(fk))
            b.pack(side="left", padx=3)
            self.filter_btns[f_key] = b

        # [카드 2] 픽셀 붓 그리기 스튜디오 (Pixel Brush Studio)
        card_studio = self.create_card(scrollable_frame, "🎨 픽셀 붓 그리기 스튜디오 (Pixel Brush Studio)")
        card_studio.pack(fill="x", pady=(0, 10))

        tk.Label(card_studio,
                 text="🖌️ 마우스 좌클릭: 픽셀 붓 찍기 | 🧹 우클릭: 픽셀 지우개 | 실시간으로 화면 중앙 조준선에 즉시 그려집니다!",
                 bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 8), justify="left").pack(anchor="w", padx=12, pady=(2, 6))

        # 툴 바 (도구 선택, 붓 모드, 투명도, 굵기, 격자선, 줌)
        tool_bar = tk.Frame(card_studio, bg=CXTheme.BG_CARD)
        tool_bar.pack(fill="x", padx=12, pady=(0, 6))

        tk.Label(tool_bar, text="도구:", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 3))
        self.tool_btns = {}
        for t_key, t_name, t_icon in [("brush", "붓", "🖌️"), ("eraser", "지우개", "🧹"), ("anchor", "중심점", "🎯")]:
            b = tk.Button(tool_bar, text=f"{t_icon} {t_name}",
                          bg=CXTheme.ACCENT_ORANGE if t_key == self.pixel_brush_tool else "#25272F",
                          fg="#FFFFFF" if t_key == self.pixel_brush_tool else CXTheme.TEXT_MAIN,
                          relief="flat", bd=0, padx=6, pady=3, font=("Segoe UI", 8, "bold"), cursor="hand2",
                          command=lambda tk=t_key: self.select_brush_tool(tk))
            b.pack(side="left", padx=1)
            self.tool_btns[t_key] = b

        # 붓 스타일 모드 (솔리드 vs 스무스)
        tk.Label(tool_bar, text="모드:", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(6, 2))
        self.brush_style_btns = {}
        for s_key, s_name in [("sharp", "■ 솔리드"), ("smooth", "● 스무스(사진급)")]:
            b = tk.Button(tool_bar, text=s_name,
                          bg=CXTheme.ACCENT_ORANGE if self.pixel_brush_style == s_key else "#25272F",
                          fg="#FFFFFF" if self.pixel_brush_style == s_key else CXTheme.TEXT_MAIN,
                          relief="flat", bd=0, padx=5, pady=2, font=("Segoe UI", 8), cursor="hand2",
                          command=lambda sk=s_key: self.set_brush_style(sk))
            b.pack(side="left", padx=1)
            self.brush_style_btns[s_key] = b

        # 붓 투명도 (Opacity)
        tk.Label(tool_bar, text="투명도:", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(6, 2))
        self.brush_op_btns = {}
        for op_val, op_name in [(1.0, "100%"), (0.75, "75%"), (0.5, "50%"), (0.25, "25%")]:
            b = tk.Button(tool_bar, text=op_name,
                          bg=CXTheme.ACCENT_ORANGE if self.pixel_brush_opacity == op_val else "#25272F",
                          fg="#FFFFFF" if self.pixel_brush_opacity == op_val else CXTheme.TEXT_MAIN,
                          relief="flat", bd=0, padx=4, pady=2, font=("Segoe UI", 8), cursor="hand2",
                          command=lambda ov=op_val: self.set_brush_opacity(ov))
            b.pack(side="left", padx=1)
            self.brush_op_btns[op_val] = b

        # 붓 굵기 선택 (1px ~ 4px)
        tk.Label(tool_bar, text="굵기:", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 8, "bold")).pack(side="left", padx=(6, 2))
        self.brush_size_btns = {}
        for b_sz, b_lbl in [(1, "1px"), (2, "2px"), (3, "3px"), (4, "4px")]:
            b = tk.Button(tool_bar, text=b_lbl,
                          bg=CXTheme.ACCENT_ORANGE if b_sz == self.pixel_brush_size else "#25272F",
                          fg="#FFFFFF" if b_sz == self.pixel_brush_size else CXTheme.TEXT_MAIN,
                          relief="flat", bd=0, padx=4, pady=2, font=("Segoe UI", 8), cursor="hand2",
                          command=lambda sz=b_sz: self.set_brush_size(sz))
            b.pack(side="left", padx=1)
            self.brush_size_btns[b_sz] = b

        # 격자선 토글
        self.btn_grid_toggle = tk.Button(tool_bar, text="▦ 격자", bg="#25272F", fg=CXTheme.ACCENT_ORANGE,
                                         relief="flat", bd=0, padx=5, pady=2, font=("Segoe UI", 8), cursor="hand2",
                                         command=self.toggle_pixel_grid)
        self.btn_grid_toggle.pack(side="left", padx=(6, 2))

        # 줌 바
        tk.Label(tool_bar, text="줌:", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 8)).pack(side="left", padx=(6, 2))
        self.zoom_btns = {}
        for z_name, z_val in [("1x", 1.0), ("2x", 2.0), ("4x", 4.0), ("8x", 8.0), ("16x", 16.0), ("맞춤", "fit")]:
            b = tk.Button(tool_bar, text=z_name, bg=CXTheme.ACCENT_ORANGE if z_val == self.img_zoom_mode else "#25272F",
                          fg="#FFFFFF" if z_val == self.img_zoom_mode else CXTheme.TEXT_MAIN, relief="flat", bd=0, padx=3, pady=2,
                          font=("Segoe UI", 8), cursor="hand2", command=lambda zv=z_val: self.set_img_zoom(zv))
            b.pack(side="left", padx=1)
            self.zoom_btns[z_val] = b

        # 색상 팔레트 바
        pal_bar = tk.Frame(card_studio, bg=CXTheme.BG_CARD)
        pal_bar.pack(fill="x", padx=12, pady=(0, 8))

        tk.Label(pal_bar, text="붓 색상:", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 6))

        # 현재 선택된 붓 색상 견본
        self.brush_swatch = tk.Label(pal_bar, width=3, height=1, bg=self.pixel_brush_hex, relief="flat", bd=0, cursor="hand2")
        self.brush_swatch.pack(side="left", padx=(0, 8))
        self.brush_swatch.bind("<Button-1>", lambda e: self.pick_brush_color())

        # 퀵 팔레트 색상 버튼들
        quick_colors = [
            ("#00FF00", "녹색"), ("#00FFFF", "청록"), ("#FF2B2B", "빨강"), ("#FFFF00", "노랑"),
            ("#FFFFFF", "흰색"), ("#000000", "검정"), ("#FF6B00", "주황"), ("#FF4D88", "핑크")
        ]
        for c_hex, c_name in quick_colors:
            b = tk.Label(pal_bar, bg=c_hex, width=2, height=1, cursor="hand2", relief="flat")
            b.pack(side="left", padx=2)
            b.bind("<Button-1>", lambda e, c=c_hex: self.set_brush_color(c))

        self.theme_btn(pal_bar, "🎨 색상 선택...", self.pick_brush_color).pack(side="left", padx=(8, 0))

        # 메인 캔버스 + 우측 미세 조정 패널
        align_body = tk.Frame(card_studio, bg=CXTheme.BG_CARD)
        align_body.pack(fill="x", padx=12, pady=4)

        # 좌측: 인터랙티브 픽셀 캔버스 (384x384)
        left_box = tk.Frame(align_body, bg=CXTheme.BG_CARD)
        left_box.pack(side="left", padx=(0, 16))

        self.img_cv = tk.Canvas(left_box, width=384, height=384, bg="#111215", highlightthickness=1,
                                highlightbackground=CXTheme.BG_CARD_BORDER, cursor="pencil")
        self.img_cv.pack()

        # 좌클릭 (붓 그리기 / 지우개 / 중심점)
        self.img_cv.bind("<Button-1>", self._on_pixel_cv_left)
        self.img_cv.bind("<B1-Motion>", self._on_pixel_cv_left)
        # 우클릭 (빠른 지우개)
        self.img_cv.bind("<Button-3>", self._on_pixel_cv_right)
        self.img_cv.bind("<B3-Motion>", self._on_pixel_cv_right)

        # 우측: 모니터 1:1 실물 프리뷰 + 좌표 상태 + D-Pad 패널
        right_box = tk.Frame(align_body, bg=CXTheme.BG_CARD)
        right_box.pack(side="left", fill="both", expand=True)

        # 1:1 모니터 실물 크기 라이브 프리뷰 패널
        pv_frame = tk.Frame(right_box, bg="#141518", highlightthickness=1, highlightbackground=CXTheme.BG_CARD_BORDER, padx=8, pady=6)
        pv_frame.pack(fill="x", pady=(0, 8))

        pv_hdr = tk.Frame(pv_frame, bg="#141518")
        pv_hdr.pack(fill="x")
        tk.Label(pv_hdr, text="👁️ 모니터 1:1 실물 크기 (라이브 미리보기)", bg="#141518", fg=CXTheme.ACCENT_ORANGE,
                 font=("Segoe UI", 8, "bold")).pack(side="left")

        pv_body = tk.Frame(pv_frame, bg="#141518")
        pv_body.pack(fill="x", pady=(4, 0))

        self.actual_preview_cv = tk.Canvas(pv_body, width=80, height=80, bg="#111215",
                                           highlightthickness=1, highlightbackground=CXTheme.BG_CARD_BORDER)
        self.actual_preview_cv.pack(side="left", padx=(0, 10))

        pv_desc = tk.Label(pv_body, text="← 작업창(돋보기 확대)과 달리\n   화면 중앙에 실제로 찍히는\n   100% 실물 픽셀 크기입니다.\n   (배율 슬라이더로 조절 가능)",
                           bg="#141518", fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 8), justify="left")
        pv_desc.pack(side="left", fill="both", expand=True)

        self.lbl_img_coords = tk.Label(right_box, text="32 × 32 픽셀 캔버스", bg="#141518", fg=CXTheme.ACCENT_ORANGE,
                                       font=("Segoe UI", 9, "bold"), relief="flat", padx=10, pady=6, justify="left", anchor="w")
        self.lbl_img_coords.pack(fill="x", pady=(0, 8))

        # 이동 단위 선택
        step_row = tk.Frame(right_box, bg=CXTheme.BG_CARD)
        step_row.pack(fill="x", pady=(0, 8))
        tk.Label(step_row, text="중심 이동 단위:", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 9)).pack(side="left", padx=(0, 6))

        self.step_btns = {}
        for s_val in [0.1, 0.5, 1.0, 5.0]:
            b = tk.Button(step_row, text=f"{s_val}px", bg=CXTheme.ACCENT_ORANGE if s_val == self.img_nudge_step else "#25272F",
                          fg="#FFFFFF" if s_val == self.img_nudge_step else CXTheme.TEXT_MAIN, relief="flat", bd=0, padx=6, pady=2,
                          font=("Segoe UI", 8), cursor="hand2", command=lambda sv=s_val: self.set_img_step(sv))
            b.pack(side="left", padx=2)
            self.step_btns[s_val] = b

        # D-Pad 컨트롤 (방향 패드)
        dpad_frame = tk.Frame(right_box, bg=CXTheme.BG_CARD)
        dpad_frame.pack(fill="x", pady=(0, 10))

        # 상단 (▲)
        row_up = tk.Frame(dpad_frame, bg=CXTheme.BG_CARD)
        row_up.pack(pady=2)
        tk.Button(row_up, text="▲ 위로", bg="#25272F", fg=CXTheme.TEXT_MAIN, activebackground=CXTheme.ACCENT_ORANGE,
                  relief="flat", bd=0, width=10, pady=4, cursor="hand2", font=("Segoe UI", 9, "bold"),
                  command=lambda: self.nudge_img_anchor(0, -1)).pack()

        # 중단 (◀, 🎯 정중앙 맞춤, ▶)
        row_mid = tk.Frame(dpad_frame, bg=CXTheme.BG_CARD)
        row_mid.pack(pady=2)
        tk.Button(row_mid, text="◀ 좌로", bg="#25272F", fg=CXTheme.TEXT_MAIN, activebackground=CXTheme.ACCENT_ORANGE,
                  relief="flat", bd=0, width=8, pady=4, cursor="hand2", font=("Segoe UI", 9, "bold"),
                  command=lambda: self.nudge_img_anchor(-1, 0)).pack(side="left", padx=2)
        tk.Button(row_mid, text="🎯 정중앙 맞춤", bg="#1E1F24", fg=CXTheme.ACCENT_ORANGE, activebackground=CXTheme.ACCENT_HOVER,
                  relief="flat", bd=0, width=12, pady=4, cursor="hand2", font=("Segoe UI", 9, "bold"),
                  command=self.reset_img_anchor_to_center).pack(side="left", padx=2)
        tk.Button(row_mid, text="▶ 우로", bg="#25272F", fg=CXTheme.TEXT_MAIN, activebackground=CXTheme.ACCENT_ORANGE,
                  relief="flat", bd=0, width=8, pady=4, cursor="hand2", font=("Segoe UI", 9, "bold"),
                  command=lambda: self.nudge_img_anchor(1, 0)).pack(side="left", padx=2)

        # 하단 (▼)
        row_dn = tk.Frame(dpad_frame, bg=CXTheme.BG_CARD)
        row_dn.pack(pady=2)
        tk.Button(row_dn, text="▼ 아래로", bg="#25272F", fg=CXTheme.TEXT_MAIN, activebackground=CXTheme.ACCENT_ORANGE,
                  relief="flat", bd=0, width=10, pady=4, cursor="hand2", font=("Segoe UI", 9, "bold"),
                  command=lambda: self.nudge_img_anchor(0, 1)).pack()

        # 직접 픽셀 좌표 입력창
        manual_frame = tk.Frame(right_box, bg=CXTheme.BG_CARD)
        manual_frame.pack(fill="x", pady=(6, 0))
        tk.Label(manual_frame, text="중심점 좌표 직접 입력:", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MUTED, font=("Segoe UI", 8)).pack(anchor="w")

        m_inputs = tk.Frame(manual_frame, bg=CXTheme.BG_CARD)
        m_inputs.pack(fill="x", pady=2)
        tk.Label(m_inputs, text="X:", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 9)).pack(side="left", padx=(0, 2))
        self.ent_img_x = tk.Entry(m_inputs, bg=CXTheme.BG_INPUT, fg=CXTheme.TEXT_MAIN, insertbackground=CXTheme.ACCENT_ORANGE,
                                  relief="flat", width=6, justify="center", font=("Segoe UI", 9))
        self.ent_img_x.pack(side="left", padx=(0, 8))
        self.ent_img_x.bind("<Return>", lambda e: self.apply_manual_img_coords())

        tk.Label(m_inputs, text="Y:", bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 9)).pack(side="left", padx=(0, 2))
        self.ent_img_y = tk.Entry(m_inputs, bg=CXTheme.BG_INPUT, fg=CXTheme.TEXT_MAIN, insertbackground=CXTheme.ACCENT_ORANGE,
                                  relief="flat", width=6, justify="center", font=("Segoe UI", 9))
        self.ent_img_y.pack(side="left", padx=(0, 8))
        self.ent_img_y.bind("<Return>", lambda e: self.apply_manual_img_coords())

        self.theme_btn(m_inputs, "적용", self.apply_manual_img_coords).pack(side="left", padx=2)

        # 초기 픽셀 캔버스 로드
        self.ensure_pixel_image_loaded()

    # ---------- 픽셀 브러시 스튜디오 핵심 로직 ----------
    def ensure_pixel_image_loaded(self):
        p = self.cfg.get("image_path")
        if not p or not os.path.exists(p):
            p = self.default_pixel_path
            if not os.path.exists(p):
                im = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
                for x in range(13, 19):
                    im.putpixel((x, 15), (0, 255, 0, 255))
                    im.putpixel((x, 16), (0, 255, 0, 255))
                for y in range(13, 19):
                    im.putpixel((15, y), (0, 255, 0, 255))
                    im.putpixel((16, y), (0, 255, 0, 255))
                try:
                    im.save(p)
                except Exception:
                    pass
            self.set("image_path", p)
            self.set("img_anchor_x", 16.0)
            self.set("img_anchor_y", 16.0)

        self.update_image_canvas()

    def create_new_pixel_canvas(self, sz=32):
        p = self.default_pixel_path
        im = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        cx, cy = sz // 2, sz // 2
        im.putpixel((cx - 1, cy - 1), self.pixel_brush_color)
        im.putpixel((cx, cy - 1), self.pixel_brush_color)
        im.putpixel((cx - 1, cy), self.pixel_brush_color)
        im.putpixel((cx, cy), self.pixel_brush_color)
        im.save(p)

        self.cached_loaded_pil_img = im
        self.cached_loaded_pil_path = p
        self.set("image_path", p)
        self.set("use_image", True)
        self.set("img_anchor_x", float(cx))
        self.set("img_anchor_y", float(cy))
        if hasattr(self, "img_toggle"):
            self.img_toggle.set_state(True)
        if hasattr(self, "img_path_lbl"):
            self.img_path_lbl.configure(text=f"신규 픽셀 캔버스 ({sz}x{sz})")

        self.overlay.cached_custom_image = im.copy()
        self.overlay.cached_image_path = p
        self.redraw()
        self.update_image_canvas()

    def prompt_custom_pixel_canvas(self):
        sz = simpledialog.askinteger(
            "캔버스 크기 직접 입력",
            "생성할 정사각형 캔버스 가로/세로 픽셀 크기 (8 ~ 1024):\n(추천: 64=정밀, 128=초정밀, 256=극미세, 512=사진급)",
            initialvalue=256,
            minvalue=8,
            maxvalue=1024,
            parent=self.root
        )
        if sz:
            self.create_new_pixel_canvas(sz)

    def set_image_filter(self, mode):
        self.set("image_filter", mode)
        for fk, btn in getattr(self, "filter_btns", {}).items():
            btn.configure(
                bg=CXTheme.ACCENT_ORANGE if fk == mode else "#25272F",
                fg="#FFFFFF" if fk == mode else CXTheme.TEXT_MAIN
            )
        self.update_actual_preview()

    def set_brush_style(self, style):
        self.pixel_brush_style = style
        for sk, btn in getattr(self, "brush_style_btns", {}).items():
            btn.configure(
                bg=CXTheme.ACCENT_ORANGE if sk == style else "#25272F",
                fg="#FFFFFF" if sk == style else CXTheme.TEXT_MAIN
            )
        self.select_brush_tool("brush")
        self.update_image_canvas_marker()

    def set_brush_opacity(self, op):
        self.pixel_brush_opacity = op
        for ov, btn in getattr(self, "brush_op_btns", {}).items():
            btn.configure(
                bg=CXTheme.ACCENT_ORANGE if ov == op else "#25272F",
                fg="#FFFFFF" if ov == op else CXTheme.TEXT_MAIN
            )
        self.update_image_canvas_marker()

    def set_brush_size(self, sz):
        self.pixel_brush_size = sz
        for b_sz, btn in getattr(self, "brush_size_btns", {}).items():
            btn.configure(
                bg=CXTheme.ACCENT_ORANGE if b_sz == sz else "#25272F",
                fg="#FFFFFF" if b_sz == sz else CXTheme.TEXT_MAIN
            )
        self.select_brush_tool("brush")
        self.update_image_canvas_marker()

    def clear_pixel_canvas(self):
        if not self.cached_loaded_pil_img:
            return
        w, h = self.cached_loaded_pil_img.size
        self.cached_loaded_pil_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.save_pixel_image()
        self.overlay.cached_custom_image = self.cached_loaded_pil_img.copy()
        self.redraw()
        self.update_image_canvas()

    def save_pixel_image(self):
        if self.cached_loaded_pil_img and self.cached_loaded_pil_path:
            try:
                self.cached_loaded_pil_img.save(self.cached_loaded_pil_path)
            except Exception:
                pass

    def save_pixel_image_as(self):
        if not self.cached_loaded_pil_img:
            return
        p = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")],
            parent=self.root
        )
        if p:
            self.cached_loaded_pil_img.save(p)
            self.set("image_path", p)
            self.cached_loaded_pil_path = p
            if hasattr(self, "img_path_lbl"):
                self.img_path_lbl.configure(text=f"현재 파일: {os.path.basename(p)}")
            messagebox.showinfo("저장 완료", f"픽셀 크로스헤어가 성공적으로 저장되었습니다:\n{p}", parent=self.root)

    def select_brush_tool(self, tool_name):
        self.pixel_brush_tool = tool_name
        for tk_name, btn in self.tool_btns.items():
            btn.configure(
                bg=CXTheme.ACCENT_ORANGE if tk_name == tool_name else "#25272F",
                fg="#FFFFFF" if tk_name == tool_name else CXTheme.TEXT_MAIN
            )
        cursor_map = {"brush": "pencil", "eraser": "dotbox", "anchor": "crosshair"}
        if hasattr(self, "img_cv"):
            self.img_cv.configure(cursor=cursor_map.get(tool_name, "crosshair"))

    def set_brush_color(self, hex_col):
        self.pixel_brush_hex = hex_col
        self.pixel_brush_color = hex_rgb(hex_col) + (255,)
        if hasattr(self, "brush_swatch"):
            self.brush_swatch.configure(bg=hex_col)
        self.select_brush_tool("brush")

    def pick_brush_color(self):
        res = colorchooser.askcolor(self.pixel_brush_hex, parent=self.root)
        if res and res[1]:
            self.set_brush_color(res[1].upper())

    def toggle_pixel_grid(self):
        self.show_pixel_grid = not self.show_pixel_grid
        if hasattr(self, "btn_grid_toggle"):
            self.btn_grid_toggle.configure(
                text="▦ 격자선 ON" if self.show_pixel_grid else "▦ 격자선 OFF",
                fg=CXTheme.ACCENT_ORANGE if self.show_pixel_grid else CXTheme.TEXT_MUTED
            )
        self.update_image_canvas()

    def _on_pixel_cv_left(self, event):
        """마우스 좌클릭 / 드래그: 붓 찍기, 지우개, 또는 중심점 지정"""
        if self.pixel_brush_tool == "brush":
            self.paint_pixel_at(event.x, event.y, self.pixel_brush_color)
        elif self.pixel_brush_tool == "eraser":
            self.paint_pixel_at(event.x, event.y, (0, 0, 0, 0))
        elif self.pixel_brush_tool == "anchor":
            self.set_anchor_at(event.x, event.y)

    def _on_pixel_cv_right(self, event):
        """마우스 우클릭 / 드래그: 언제든 즉시 픽셀 지우개로 동작"""
        self.paint_pixel_at(event.x, event.y, (0, 0, 0, 0))

    def paint_pixel_at(self, event_x, event_y, color):
        """특정 픽셀 좌표에 색칠 또는 지우기 & 실시간 화면 오버레이에 즉각 반영"""
        if not self.cached_loaded_pil_img:
            return
        orig_w, orig_h = self.cached_loaded_pil_img.size
        gx = int((event_x - self.img_disp_ox) / self.img_disp_scale)
        gy = int((event_y - self.img_disp_oy) / self.img_disp_scale)

        sz = getattr(self, "pixel_brush_size", 1)
        style = getattr(self, "pixel_brush_style", "sharp")
        opacity = getattr(self, "pixel_brush_opacity", 1.0)
        changed = False

        is_eraser = (color == (0, 0, 0, 0) or self.pixel_brush_tool == "eraser")

        def blend_pixel(im, x, y, r, g, b, a):
            if not (0 <= x < orig_w and 0 <= y < orig_h):
                return
            if a <= 0:
                return
            curr_r, curr_g, curr_b, curr_a = im.getpixel((x, y))
            if curr_a == 0:
                im.putpixel((x, y), (r, g, b, a))
            else:
                sa = a / 255.0
                da = curr_a / 255.0
                oa = sa + da * (1.0 - sa)
                if oa > 0:
                    or_ = int((r * sa + curr_r * da * (1.0 - sa)) / oa)
                    og_ = int((g * sa + curr_g * da * (1.0 - sa)) / oa)
                    ob_ = int((b * sa + curr_b * da * (1.0 - sa)) / oa)
                    im.putpixel((x, y), (or_, og_, ob_, int(oa * 255)))

        if is_eraser:
            half = sz // 2 if sz > 1 else 0
            for dy in range(-half, sz - half if sz > 1 else 1):
                for dx in range(-half, sz - half if sz > 1 else 1):
                    px = gx + dx
                    py = gy + dy
                    if 0 <= px < orig_w and 0 <= py < orig_h:
                        self.cached_loaded_pil_img.putpixel((px, py), (0, 0, 0, 0))
                        changed = True
        else:
            base_r, base_g, base_b = color[:3]
            base_alpha = int(255 * opacity)

            if style == "sharp":
                if sz <= 1:
                    if 0 <= gx < orig_w and 0 <= gy < orig_h:
                        blend_pixel(self.cached_loaded_pil_img, gx, gy, base_r, base_g, base_b, base_alpha)
                        changed = True
                else:
                    half = sz // 2
                    for dy in range(-half, sz - half):
                        for dx in range(-half, sz - half):
                            px = gx + dx
                            py = gy + dy
                            if 0 <= px < orig_w and 0 <= py < orig_h:
                                blend_pixel(self.cached_loaded_pil_img, px, py, base_r, base_g, base_b, base_alpha)
                                changed = True
            else:
                # 스무스 펜 (사진처럼 부드러운 안티앨리어싱 그라데이션)
                rad = max(1, sz)
                for dy in range(-rad, rad + 1):
                    for dx in range(-rad, rad + 1):
                        dist = math.sqrt(dx * dx + dy * dy)
                        if dist <= rad:
                            factor = max(0.0, 1.0 - (dist / (rad + 0.5)))
                            pt_a = int(base_alpha * factor)
                            if pt_a > 0:
                                px = gx + dx
                                py = gy + dy
                                if 0 <= px < orig_w and 0 <= py < orig_h:
                                    blend_pixel(self.cached_loaded_pil_img, px, py, base_r, base_g, base_b, pt_a)
                                    changed = True

        if changed:
            self.save_pixel_image()
            self.overlay.cached_custom_image = self.cached_loaded_pil_img.copy()
            self.set("use_image", True)
            if hasattr(self, "img_toggle"):
                self.img_toggle.set_state(True)
            self.redraw()
            self.update_image_canvas()

    def set_anchor_at(self, event_x, event_y):
        """클릭한 픽셀을 모니터 중심 앵커로 지정"""
        if not self.cached_loaded_pil_img:
            return
        orig_w, orig_h = self.cached_loaded_pil_img.size
        ix = (event_x - self.img_disp_ox) / self.img_disp_scale
        iy = (event_y - self.img_disp_oy) / self.img_disp_scale
        ix = max(0.0, min(float(orig_w), round(ix, 1)))
        iy = max(0.0, min(float(orig_h), round(iy, 1)))
        self.set("img_anchor_x", ix)
        self.set("img_anchor_y", iy)
        self.update_image_canvas_marker()

    def browse_image(self):
        path = filedialog.askopenfilename(filetypes=[("PNG Image", "*.png"), ("All Files", "*.*")])
        if path:
            self.set("image_path", path)
            self.set("use_image", True)
            if hasattr(self, "img_path_lbl"):
                self.img_path_lbl.configure(text=f"현재 파일: {os.path.basename(path)}")
            if hasattr(self, "img_toggle"):
                self.img_toggle.set_state(True)
            try:
                with Image.open(path) as im:
                    w, h = im.size
                    self.set("img_anchor_x", round(w / 2.0, 1))
                    self.set("img_anchor_y", round(h / 2.0, 1))
            except Exception:
                pass
            self.cached_loaded_pil_path = ""
            self.update_image_canvas()

    def update_image_canvas(self):
        if not hasattr(self, "img_cv") or not self.img_cv.winfo_exists():
            return
        p = self.cfg.get("image_path")
        if not p or not os.path.exists(p):
            p = self.default_pixel_path

        if p != self.cached_loaded_pil_path or self.cached_loaded_pil_img is None:
            if os.path.exists(p):
                try:
                    self.cached_loaded_pil_img = Image.open(p).convert("RGBA")
                    self.cached_loaded_pil_path = p
                except Exception:
                    self.cached_loaded_pil_img = None
            else:
                self.cached_loaded_pil_img = None

        if self.cached_loaded_pil_img is None:
            self.cached_loaded_pil_img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            self.cached_loaded_pil_path = self.default_pixel_path
            try:
                self.cached_loaded_pil_img.save(self.default_pixel_path)
            except Exception:
                pass

        orig_w, orig_h = self.cached_loaded_pil_img.size

        # 384x384 캔버스에 꽉 차게 계산
        CV_SZ = 384
        if self.img_zoom_mode == "fit":
            disp_scale = min(CV_SZ / orig_w, CV_SZ / orig_h)
        else:
            disp_scale = float(self.img_zoom_mode)
        disp_scale = max(0.05, disp_scale)

        disp_w = int(round(orig_w * disp_scale))
        disp_h = int(round(orig_h * disp_scale))
        disp_ox = (CV_SZ - disp_w) // 2
        disp_oy = (CV_SZ - disp_h) // 2

        self.img_disp_scale = disp_scale
        self.img_disp_ox = disp_ox
        self.img_disp_oy = disp_oy

        # 체크보드 투명 배경 생성
        bg = Image.new("RGBA", (CV_SZ, CV_SZ), (18, 19, 22, 255))
        d = ImageDraw.Draw(bg)
        grid_sz = 16
        for gy in range(0, CV_SZ, grid_sz):
            for gx in range(0, CV_SZ, grid_sz):
                if ((gx // grid_sz) + (gy // grid_sz)) % 2 == 1:
                    d.rectangle([gx, gy, gx + grid_sz - 1, gy + grid_sz - 1], fill=(25, 27, 32, 255))

        # 픽셀 아트 이미지 확대 합성 (NEAREST로 완전 칼사각 픽셀 유지)
        disp_img = self.cached_loaded_pil_img.resize((disp_w, disp_h), Image.Resampling.NEAREST)
        bg.alpha_composite(disp_img, (disp_ox, disp_oy))

        # 격자선 그리기 (격자선이 켜져있고 셀 크기가 4픽셀 이상일 때)
        if self.show_pixel_grid and disp_scale >= 4.0:
            for x in range(orig_w + 1):
                lx = int(disp_ox + x * disp_scale)
                d.line([(lx, disp_oy), (lx, disp_oy + disp_h)], fill=(40, 42, 50, 180), width=1)
            for y in range(orig_h + 1):
                ly = int(disp_oy + y * disp_scale)
                d.line([(disp_ox, ly), (disp_ox + disp_w, ly)], fill=(40, 42, 50, 180), width=1)

        self.rendered_img_photo = ImageTk.PhotoImage(bg)
        self.img_cv.delete("all")
        self.img_cv.create_image(CV_SZ // 2, CV_SZ // 2, image=self.rendered_img_photo)

        self.update_actual_preview()
        self.update_image_canvas_marker()

    def update_actual_preview(self):
        """우측 1:1 모니터 실물 크기 라이브 미니 프리뷰 렌더링"""
        if not hasattr(self, "actual_preview_cv") or not self.actual_preview_cv.winfo_exists():
            return
        if not self.cached_loaded_pil_img:
            return
        orig_w, orig_h = self.cached_loaded_pil_img.size
        PV_SZ = 80
        pv_bg = Image.new("RGBA", (PV_SZ, PV_SZ), (18, 19, 22, 255))
        pv_d = ImageDraw.Draw(pv_bg)
        for pgy in range(0, PV_SZ, 8):
            for pgx in range(0, PV_SZ, 8):
                if ((pgx // 8) + (pgy // 8)) % 2 == 1:
                    pv_d.rectangle([pgx, pgy, pgx + 7, pgy + 7], fill=(25, 27, 32, 255))

        scale = float(self.cfg.get("image_scale", 1.0)) * float(self.cfg.get("layer_scale", 1.0))
        raw_ax = self.cfg.get("img_anchor_x")
        raw_ay = self.cfg.get("img_anchor_y")
        ax = float(raw_ax) if raw_ax is not None else (orig_w / 2.0)
        ay = float(raw_ay) if raw_ay is not None else (orig_h / 2.0)

        nw, nh = max(1, int(round(orig_w * scale))), max(1, int(round(orig_h * scale)))
        filt = self.cfg.get("image_filter", "sharp")
        resample = Image.Resampling.BILINEAR if filt == "smooth" else Image.Resampling.NEAREST
        pv_resized = self.cached_loaded_pil_img.resize((nw, nh), resample)
        pv_px = int(round(PV_SZ / 2.0 - ax * scale))
        pv_py = int(round(PV_SZ / 2.0 - ay * scale))
        pv_bg.alpha_composite(pv_resized, (pv_px, pv_py))

        self.actual_preview_photo = ImageTk.PhotoImage(pv_bg)
        self.actual_preview_cv.delete("all")
        self.actual_preview_cv.create_image(PV_SZ // 2, PV_SZ // 2, image=self.actual_preview_photo)
        self.actual_preview_cv.create_line(PV_SZ // 2, 0, PV_SZ // 2, PV_SZ, fill="#3A3D46", dash=(2, 2))
        self.actual_preview_cv.create_line(0, PV_SZ // 2, PV_SZ, PV_SZ // 2, fill="#3A3D46", dash=(2, 2))

    def update_image_canvas_marker(self):
        if not hasattr(self, "img_cv") or not self.cached_loaded_pil_img:
            return
        orig_w, orig_h = self.cached_loaded_pil_img.size
        raw_ax = self.cfg.get("img_anchor_x")
        raw_ay = self.cfg.get("img_anchor_y")
        ax = float(raw_ax) if raw_ax is not None else (orig_w / 2.0)
        ay = float(raw_ay) if raw_ay is not None else (orig_h / 2.0)

        mx = self.img_disp_ox + ax * self.img_disp_scale
        my = self.img_disp_oy + ay * self.img_disp_scale
        CV_SZ = 384

        self.img_cv.delete("marker")
        # 가이드 십자선 (점선)
        self.img_cv.create_line(0, my, CV_SZ, my, fill=CXTheme.ACCENT_ORANGE, width=1, dash=(3, 3), tags="marker")
        self.img_cv.create_line(mx, 0, mx, CV_SZ, fill=CXTheme.ACCENT_ORANGE, width=1, dash=(3, 3), tags="marker")

        # 조준점 원형 타겟 및 크로스
        self.img_cv.create_oval(mx - 8, my - 8, mx + 8, my + 8, outline=CXTheme.ACCENT_ORANGE, width=2, tags="marker")
        self.img_cv.create_oval(mx - 2, my - 2, mx + 2, my + 2, fill="#FFFFFF", outline=CXTheme.ACCENT_ORANGE, tags="marker")
        self.img_cv.create_line(mx - 14, my, mx - 9, my, fill=CXTheme.ACCENT_ORANGE, width=2, tags="marker")
        self.img_cv.create_line(mx + 9, my, mx + 14, my, fill=CXTheme.ACCENT_ORANGE, width=2, tags="marker")
        self.img_cv.create_line(mx, my - 14, mx, my - 9, fill=CXTheme.ACCENT_ORANGE, width=2, tags="marker")
        self.img_cv.create_line(mx, my + 9, mx, my + 14, fill=CXTheme.ACCENT_ORANGE, width=2, tags="marker")

        # 좌표 텍스트 갱신
        b_sz = getattr(self, "pixel_brush_size", 1)
        b_style = "스무스" if getattr(self, "pixel_brush_style", "sharp") == "smooth" else "솔리드"
        b_op = int(getattr(self, "pixel_brush_opacity", 1.0) * 100)
        self.lbl_img_coords.configure(
            text=f"📍 조준점 중심 픽셀:\n  X = {ax:.1f} px\n  Y = {ay:.1f} px\n  (캔버스: {orig_w} × {orig_h} px | 브러시: {b_sz}px {b_style} {b_op}%)"
        )

        # 입력 엔트리 텍스트 갱신
        if hasattr(self, "ent_img_x") and hasattr(self, "ent_img_y"):
            self.ent_img_x.delete(0, tk.END)
            self.ent_img_x.insert(0, f"{ax:.1f}")
            self.ent_img_y.delete(0, tk.END)
            self.ent_img_y.insert(0, f"{ay:.1f}")

    def nudge_img_anchor(self, dx, dy):
        if not self.cached_loaded_pil_img:
            return
        orig_w, orig_h = self.cached_loaded_pil_img.size
        raw_ax = self.cfg.get("img_anchor_x")
        raw_ay = self.cfg.get("img_anchor_y")
        ax = float(raw_ax) if raw_ax is not None else (orig_w / 2.0)
        ay = float(raw_ay) if raw_ay is not None else (orig_h / 2.0)
        step = float(self.img_nudge_step)
        new_ax = max(0.0, min(float(orig_w), round(ax + dx * step, 2)))
        new_ay = max(0.0, min(float(orig_h), round(ay + dy * step, 2)))
        self.set("img_anchor_x", new_ax)
        self.set("img_anchor_y", new_ay)
        self.update_image_canvas_marker()

    def reset_img_anchor_to_center(self):
        if not self.cached_loaded_pil_img:
            return
        orig_w, orig_h = self.cached_loaded_pil_img.size
        self.set("img_anchor_x", round(orig_w / 2.0, 1))
        self.set("img_anchor_y", round(orig_h / 2.0, 1))
        self.update_image_canvas_marker()

    def apply_manual_img_coords(self):
        if not self.cached_loaded_pil_img:
            return
        orig_w, orig_h = self.cached_loaded_pil_img.size
        try:
            x_val = float(self.ent_img_x.get())
            y_val = float(self.ent_img_y.get())
            x_val = max(0.0, min(float(orig_w), round(x_val, 2)))
            y_val = max(0.0, min(float(orig_h), round(y_val, 2)))
            self.set("img_anchor_x", x_val)
            self.set("img_anchor_y", y_val)
            self.update_image_canvas_marker()
        except Exception:
            pass

    def set_img_zoom(self, mode):
        self.img_zoom_mode = mode
        for zv, btn in self.zoom_btns.items():
            btn.configure(
                bg=CXTheme.ACCENT_ORANGE if zv == mode else "#25272F",
                fg="#FFFFFF" if zv == mode else CXTheme.TEXT_MAIN
            )
        self.update_image_canvas()

    def set_img_step(self, step):
        self.img_nudge_step = step
        for sv, btn in self.step_btns.items():
            btn.configure(
                bg=CXTheme.ACCENT_ORANGE if sv == step else "#25272F",
                fg="#FFFFFF" if sv == step else CXTheme.TEXT_MAIN
            )

    # ---------- 키바인드 뷰 ----------
    def build_keybinds_view(self):
        view = tk.Frame(self.content_area, bg=CXTheme.BG_MAIN)
        self.views["keybinds"] = view

        card = self.create_card(view, "전역 단축키 (Global Keybinds)")
        card.pack(fill="x")

        keys_info = [
            ("F8", "크로스헤어 표시 / 숨기기 토글"),
            ("F9", "설정창 열기 / 닫기 (트레이 최소화)"),
            ("F10", "다음 크로스헤어 프로필로 전환"),
            ("Ctrl + F12", "프로그램 완전 종료"),
            ("Shift + 방향키", "위치 탭에서 0.1px 단위 미세 이동")
        ]
        for k, desc in keys_info:
            r = tk.Frame(card, bg=CXTheme.BG_CARD)
            r.pack(fill="x", padx=12, pady=6)
            tk.Label(r, text=k, bg="#2A2C34", fg=CXTheme.ACCENT_ORANGE, font=("Segoe UI", 9, "bold"), width=12, padx=4, pady=2).pack(side="left")
            tk.Label(r, text=desc, bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 9)).pack(side="left", padx=10)

    # ---------- UI 헬퍼 컴포넌트 ----------
    def create_card(self, parent, title):
        card = tk.Frame(parent, bg=CXTheme.BG_CARD, highlightthickness=1, highlightbackground=CXTheme.BG_CARD_BORDER, padx=4, pady=6)
        hdr = tk.Frame(card, bg=CXTheme.BG_CARD)
        hdr.pack(fill="x", padx=8, pady=(2, 6))
        tk.Label(hdr, text=title, bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 10, "bold")).pack(side="left")
        return card

    def create_card_with_toggle(self, parent, title, toggle_key):
        card = tk.Frame(parent, bg=CXTheme.BG_CARD, highlightthickness=1, highlightbackground=CXTheme.BG_CARD_BORDER, padx=4, pady=6)
        hdr = tk.Frame(card, bg=CXTheme.BG_CARD)
        hdr.pack(fill="x", padx=8, pady=(2, 6))
        tk.Label(hdr, text=title, bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 10, "bold")).pack(side="left")

        ts = ToggleSwitch(hdr, initial=self.cfg.get(toggle_key, False), command=lambda s: self.set(toggle_key, s))
        ts.pack(side="right")
        self.toggles[toggle_key] = ts
        return card

    def add_slider(self, parent, label, key, from_, to, step=0.1):
        s = ModernSlider(parent, label, from_, to, step, initial=self.cfg.get(key, DEFAULT.get(key, 0.0)),
                         command=lambda v: self.set(key, v))
        s.pack(fill="x", padx=12, pady=4)
        self.sliders[key] = s

    def add_color_picker(self, parent, label, key):
        f = tk.Frame(parent, bg=CXTheme.BG_CARD)
        f.pack(fill="x", padx=12, pady=4)
        tk.Label(f, text=label, bg=CXTheme.BG_CARD, fg=CXTheme.TEXT_MAIN, font=("Segoe UI", 9)).pack(side="left")

        sw = tk.Label(f, width=3, height=1, bg=self.cfg.get(key, "#00FF00"), relief="flat", bd=0, cursor="hand2")
        sw.pack(side="right", padx=4)
        sw.bind("<Button-1>", lambda e: self.pick_color(key, sw))

        # 퀵 팔레트 버튼들
        for c in ["#00FF00", "#00FFA3", "#00E5FF", "#FFFF00", "#FF2B2B", "#FFFFFF"]:
            b = tk.Label(f, bg=c, width=2, height=1, cursor="hand2", relief="flat")
            b.pack(side="right", padx=1)
            b.bind("<Button-1>", lambda e, c=c, sw=sw: (self.set(key, c), sw.configure(bg=c)))

    def pick_color(self, key, swatch):
        res = colorchooser.askcolor(self.cfg.get(key, "#00FF00"), parent=self.root)
        if res and res[1]:
            c = res[1].upper()
            self.set(key, c)
            swatch.configure(bg=c)

    def theme_btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, bg="#25272F", fg=CXTheme.TEXT_MAIN, activebackground=CXTheme.ACCENT_ORANGE,
                         activeforeground="#FFFFFF", relief="flat", bd=0, padx=8, pady=3,
                         font=("Segoe UI", 8, "bold"), cursor="hand2", command=cmd)

    def set_dot_shape(self, shape_name):
        self.set("dot_shape", shape_name)
        for s, b in self.dot_shape_btns.items():
            if s == shape_name:
                b.configure(bg=CXTheme.ACCENT_ORANGE, fg="#FFFFFF")
            else:
                b.configure(bg="#25272F", fg=CXTheme.TEXT_MAIN)

    def toggle_arm(self, key):
        cur = self.cfg.get(key, True)
        self.set(key, not cur)
        btn = self.dir_btns.get(key)
        if btn:
            btn.configure(bg=CXTheme.ACCENT_ORANGE if not cur else "#25272F")

    # ---------- 상태 동기화 및 렌더링 ----------
    def set(self, key, val):
        if self._syncing:
            return
        self.cfg[key] = val
        self.redraw()

    def redraw(self):
        if not self._draw_job:
            self._draw_job = self.root.after(10, self._do_draw)
        if self._save_job:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(400, lambda: save_store(self.store))

    def _do_draw(self):
        self._draw_job = None
        self.overlay.draw(self.cfg)
        self.update_mini_preview()
        self.update_actual_preview()

    def update_mini_preview(self):
        """좌측 상단 레이어 카드 안의 80x80 미니 프리뷰 실시간 업데이트"""
        img = self.overlay.render(self.cfg, 40, 40)
        # 80x80 캔버스 중앙에 표시
        crop_size = 80
        cx = CANVAS // 2
        cropped = img.crop((cx - 40, cx - 40, cx + 40, cx + 40))
        self.preview_photo = ImageTk.PhotoImage(cropped)
        self.preview_cv.delete("all")
        self.preview_cv.create_image(40, 40, image=self.preview_photo)

    def load_profile(self, name):
        self.store["current"] = name
        self.profile_cb["values"] = list(self.store["profiles"].keys())
        self.profile_cb.set(name)
        self._syncing = True
        try:
            for k, s in self.sliders.items():
                if k in self.cfg:
                    s.set_value(self.cfg[k])
            for k, t in self.toggles.items():
                if k in self.cfg:
                    t.set_state(self.cfg[k])
            # 도트 모양 버튼
            d_shape = self.cfg.get("dot_shape", "사각")
            for s, b in self.dot_shape_btns.items():
                b.configure(bg=CXTheme.ACCENT_ORANGE if s == d_shape else "#25272F",
                            fg="#FFFFFF" if s == d_shape else CXTheme.TEXT_MAIN)
            # 방향 버튼
            for k, b in self.dir_btns.items():
                on = self.cfg.get(k, True)
                b.configure(bg=CXTheme.ACCENT_ORANGE if on else "#25272F")
        finally:
            self._syncing = False
        self.redraw()
        if hasattr(self, "img_path_lbl"):
            curr_p = self.cfg.get("image_path", "")
            self.img_path_lbl.configure(text=os.path.basename(curr_p) if curr_p else "선택된 파일 없음")
        if hasattr(self, "img_toggle"):
            self.img_toggle.set_state(self.cfg.get("use_image", False))
        self.update_image_canvas()

    # ---------- 프로필 관리 ----------
    def new_profile(self):
        n = simpledialog.askstring("새 프로필", "프로필 이름 입력:", parent=self.root)
        if n and n.strip():
            n = n.strip()
            self.store["profiles"][n] = dict(DEFAULT, name=n)
            self.load_profile(n)

    def dup_profile(self):
        cur = self.store["current"]
        n = simpledialog.askstring("프로필 복제", "복제할 프로필 이름:", initialvalue=cur + " (복사)", parent=self.root)
        if n and n.strip():
            n = n.strip()
            self.store["profiles"][n] = dict(self.cfg, name=n)
            self.load_profile(n)

    def rename_profile(self):
        old = self.store["current"]
        n = simpledialog.askstring("이름 변경", "새 프로필 이름:", initialvalue=old, parent=self.root)
        if n and n.strip():
            n = n.strip()
            ps = self.store["profiles"]
            self.store["profiles"] = {(n if k == old else k): v for k, v in ps.items()}
            self.load_profile(n)

    def del_profile(self):
        if len(self.store["profiles"]) <= 1:
            messagebox.showinfo("알림", "마지막 프로필은 삭제할 수 없습니다.", parent=self.root)
            return
        if messagebox.askyesno("삭제", f"'{self.store['current']}' 프로필을 삭제하시겠습니까?", parent=self.root):
            del self.store["profiles"][self.store["current"]]
            self.load_profile(next(iter(self.store["profiles"])))

    def next_profile(self):
        names = list(self.store["profiles"].keys())
        i = (names.index(self.store["current"]) + 1) % len(names)
        self.load_profile(names[i])

    def nudge(self, dx, dy):
        step = 0.1 if (user32.GetAsyncKeyState(VK["SHIFT"]) & 0x8000) else 1.0
        self.set("offset_x", round(self.cfg.get("offset_x", 0.0) + dx * step, 2))
        self.set("offset_y", round(self.cfg.get("offset_y", 0.0) + dy * step, 2))
        if "offset_x" in self.sliders:
            self.sliders["offset_x"].set_value(self.cfg["offset_x"])
        if "offset_y" in self.sliders:
            self.sliders["offset_y"].set_value(self.cfg["offset_y"])

    def center(self):
        self.set("offset_x", 0.0)
        self.set("offset_y", 0.0)
        if "offset_x" in self.sliders:
            self.sliders["offset_x"].set_value(0.0)
        if "offset_y" in self.sliders:
            self.sliders["offset_y"].set_value(0.0)

    # ---------- 발사 애니메이션 루프 (마우스 좌클릭 감지) ----------
    def fire_anim_loop(self):
        if self.cfg.get("fire_anim_on", False):
            # 마우스 좌클릭 상태 감지
            is_lbutton_down = bool(user32.GetAsyncKeyState(VK["LBUTTON"]) & 0x8000)
            if is_lbutton_down:
                spread = float(self.cfg.get("fire_spread", 4.0))
                self.overlay.current_fire_spread = spread
                self.overlay.draw(self.cfg)
            elif self.overlay.current_fire_spread > 0.05:
                decay = float(self.cfg.get("fire_decay", 0.85))
                self.overlay.current_fire_spread *= decay
                if self.overlay.current_fire_spread <= 0.05:
                    self.overlay.current_fire_spread = 0.0
                self.overlay.draw(self.cfg)

        self.root.after(16, self.fire_anim_loop)

    def hide_settings(self):
        self.root.withdraw()
        self.settings_visible = False

    def toggle_settings(self):
        if self.settings_visible:
            self.hide_settings()
        else:
            self.root.deiconify()
            self.root.lift()
            self.settings_visible = True

    def pressed(self, name):
        down = bool(user32.GetAsyncKeyState(VK[name]) & 0x8000)
        was = self.keystate.get(name, False)
        self.keystate[name] = down
        return down and not was

    def poll_keys(self):
        ctrl = bool(user32.GetAsyncKeyState(VK["CTRL"]) & 0x8000)
        if self.pressed("F8"):
            self.overlay.toggle()
            self.badge_lbl.configure(
                text="● 표시됨" if self.overlay.visible else "○ 숨김",
                fg=CXTheme.ACCENT_ORANGE if self.overlay.visible else CXTheme.TEXT_MUTED
            )
        if self.pressed("F9"):
            self.toggle_settings()
        if self.pressed("F10"):
            self.next_profile()
        if self.pressed("F12") and ctrl:
            self.quit()
            return
        self.root.after(30, self.poll_keys)

    def top_loop(self):
        self.overlay.keep_on_top()
        self.root.after(1000, self.top_loop)

    def quit(self):
        if getattr(self, "tray_icon", None):
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        save_store(self.store)
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
