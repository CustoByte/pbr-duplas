@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Atualizar-Iniciar.ps1" -FeedUrl "https://raw.githubusercontent.com/CustoByte/pbr-duplas/feat/full493-waterfall/expansion/update-test.json"
if errorlevel 1 pause
endlocal
