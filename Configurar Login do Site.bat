@echo off
REM ============================================================
REM  Configurar Login do Site.bat
REM  De um duplo-clique neste arquivo para criar (ou trocar) o
REM  usuario e senha que protegem o SITE NA NUVEM. A senha
REM  digitada aqui fica so no seu computador (nunca e enviada
REM  pra ninguem em texto puro).
REM ============================================================

setlocal
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo O app ainda nao foi aberto nenhuma vez neste computador.
    echo De um duplo-clique em "Iniciar App.bat" primeiro, feche o
    echo app, e depois rode este arquivo de novo.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

python configurar_login_site.py

echo.
pause
