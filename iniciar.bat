@echo off
rem Lanzador para Windows: prepara el entorno la primera vez y abre el chat con el agente.
cd /d "%~dp0"

if exist .venv\Scripts\python.exe goto clave

echo Preparando el entorno por primera vez, tarda 1 o 2 minutos...
py -3 -m venv .venv 2>nul
if not exist .venv\Scripts\python.exe python -m venv .venv 2>nul
if not exist .venv\Scripts\python.exe goto sin_python
.venv\Scripts\python.exe -m pip install -q --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto error_pip

:clave
if exist .env goto correr
echo.
echo Falta la clave de Groq. Puedes obtener una gratis en https://console.groq.com/keys
set /p CLAVE=Pega tu GROQ_API_KEY y presiona Enter:
>.env echo GROQ_API_KEY=%CLAVE%

:correr
echo.
.venv\Scripts\python.exe agente.py
pause
exit /b 0

:sin_python
echo No se encontro Python 3.10 o superior. Instalalo desde https://www.python.org/downloads/
pause
exit /b 1

:error_pip
rmdir /s /q .venv
echo No se pudieron instalar las dependencias. Revisa tu conexion a internet y vuelve a intentarlo.
pause
exit /b 1
