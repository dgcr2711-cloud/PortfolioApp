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

REM 2026-09-03: a janela estava fechando sozinha no meio das perguntas.
REM Estas duas linhas evitam a causa mais comum disso (acentuacao/emoji
REM quebrando a leitura do terminal do Windows); o script python agora
REM tambem nunca fecha sozinho sem esperar uma tecla seu, mesmo se der erro.
chcp 65001 >nul
set PYTHONIOENCODING=utf-8

if not exist "venv\Scripts\activate.bat" (
    echo O app ainda nao foi aberto nenhuma vez neste computador.
    echo De um duplo-clique em "Iniciar App.bat" primeiro, feche o
    echo app, e depois rode este arquivo de novo.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

REM 2026-09-03: em vez de mandar fechar e abrir o "Iniciar App.bat" pra
REM instalar essa biblioteca, o proprio arquivo ja resolve isso sozinho
REM aqui, mostrando qualquer erro de instalacao na hora, na mesma janela.
pip show streamlit-authenticator >nul 2>nul
if errorlevel 1 (
    echo Instalando a biblioteca de login do site, aguarde...
    echo (normalmente leva menos de 1 minuto)
    echo.
    pip install "streamlit-authenticator>=0.4"
    if errorlevel 1 (
        echo.
        echo Nao foi possivel instalar a biblioteca de login. Copie todo o
        echo texto acima e me mostre para eu ajudar a resolver.
        pause
        exit /b 1
    )
    echo.
)

python configurar_login_site.py

echo.
echo (Se a janela acima fechou sem pedir uma tecla, algo bem incomum
echo  aconteceu - me avise.)
pause
