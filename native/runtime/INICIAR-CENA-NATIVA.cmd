@echo off
setlocal
cd /d "%~dp0"
if exist "Mega-Lucario.glb" (
    "PBRNative.exe" --main-pack "%~dp0PBRNative.pck" -- --data-dir "%~dp0user-data" --model "%~dp0Mega-Lucario.glb"
) else (
    "PBRNative.exe" --main-pack "%~dp0PBRNative.pck" -- --data-dir "%~dp0user-data"
)
if errorlevel 1 pause
