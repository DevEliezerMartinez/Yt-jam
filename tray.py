"""
YT Jam — System Tray
Muestra el estado del servidor en la bandeja del sistema.
Click derecho para ver opciones: iniciar, detener, abrir browser.
"""

import subprocess
import threading
import time
import sys
import os
import webbrowser
import requests
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item

# ── Config ────────────────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SERVER_DIR   = os.path.join(BASE_DIR, "server")
VENV_PYTHON  = os.path.join(SERVER_DIR, "venv", "Scripts", "python.exe")
SERVER_URL   = "http://localhost:8000"
CHECK_INTERVAL = 5  # segundos entre health checks

# ── Estado global ─────────────────────────────────────────────────────────
procs = {"uvicorn": None, "cloudflared": None}
status = {"up": False}

# ── Iconos dinámicos ──────────────────────────────────────────────────────
def make_icon(color):
    """Genera un ícono circular de 64x64 del color dado."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60], fill=color)
    # Letra Y adentro
    draw.text((20, 16), "YT", fill="white")
    return img

ICON_GREEN = make_icon("#22c55e")   # servidor arriba
ICON_RED   = make_icon("#ef4444")   # servidor abajo
ICON_GRAY  = make_icon("#6b7280")   # iniciando

# ── Procesos ──────────────────────────────────────────────────────────────
def start_server():
    if procs["uvicorn"] and procs["uvicorn"].poll() is None:
        return  # ya corre
    procs["uvicorn"] = subprocess.Popen(
        [VENV_PYTHON, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=SERVER_DIR,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

def start_tunnel():
    if procs["cloudflared"] and procs["cloudflared"].poll() is None:
        return  # ya corre
    procs["cloudflared"] = subprocess.Popen(
        ["cloudflared", "tunnel", "run", "yt-jam"],
        creationflags=subprocess.CREATE_NO_WINDOW,
    )

def stop_all():
    for name, proc in procs.items():
        if proc and proc.poll() is None:
            proc.terminate()
            procs[name] = None

# ── Health check ──────────────────────────────────────────────────────────
def health_loop(icon):
    while True:
        try:
            r = requests.get(SERVER_URL, timeout=2)
            is_up = r.status_code == 200
        except Exception:
            is_up = False

        if is_up != status["up"]:
            status["up"] = is_up
            icon.icon  = ICON_GREEN if is_up else ICON_RED
            icon.title = "YT Jam ✅ Corriendo" if is_up else "YT Jam ❌ Detenido"

        time.sleep(CHECK_INTERVAL)

# ── Acciones del menú ─────────────────────────────────────────────────────
def on_start(icon, item):
    start_server()
    start_tunnel()

def on_stop(icon, item):
    stop_all()
    icon.icon  = ICON_RED
    icon.title = "YT Jam ❌ Detenido"

def on_open(icon, item):
    webbrowser.open(SERVER_URL)

def on_quit(icon, item):
    stop_all()
    icon.stop()

# ── Main ──────────────────────────────────────────────────────────────────
def main():
    menu = pystray.Menu(
        item("▶  Iniciar",         on_start),
        item("⏹  Detener",         on_stop),
        pystray.Menu.SEPARATOR,
        item("🌐  Abrir servidor",  on_open),
        pystray.Menu.SEPARATOR,
        item("✖  Salir",           on_quit),
    )

    icon = pystray.Icon(
        name="yt-jam",
        icon=ICON_GRAY,
        title="YT Jam — Iniciando…",
        menu=menu,
    )

    # Arrancar servidor al iniciar
    threading.Thread(target=lambda: (start_server(), start_tunnel()), daemon=True).start()

    # Health check en background
    threading.Thread(target=health_loop, args=(icon,), daemon=True).start()

    icon.run()

if __name__ == "__main__":
    main()
