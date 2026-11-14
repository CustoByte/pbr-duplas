@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 launcher\app.py
if errorlevel 1 pause
exit /b
:python_fallback
where python >nul 2>nul
if errorlevel 1 goto missing_python
python launcher\app.py
if errorlevel 1 pause
exit /b
:missing_python
echo Esta base de desenvolvimento requer Python 3.11 ou superior com Tk.
echo Instale pelo python.org com a opcao Tcl/Tk e execute novamente.
pause
