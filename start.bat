@echo off
:: YT Jam — Launcher
:: Coloca este archivo en el Desktop o en shell:startup para arranque automático

set BASE=C:\Users\UNE\Documents\EliezerMartinez\yt-jam

:: Instalar dependencias del tray si no están
"%BASE%\server\venv\Scripts\pip.exe" install pystray pillow requests --quiet

:: Lanzar el tray (se minimiza solo a la bandeja)
start "" "%BASE%\server\venv\Scripts\pythonw.exe" "%BASE%\tray.py"
