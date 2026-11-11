@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Atualizar-Iniciar.ps1"
if errorlevel 1 (
  echo.
  echo A aplicacao nao foi concluida. Leia o erro acima.
  pause
)
endlocal
