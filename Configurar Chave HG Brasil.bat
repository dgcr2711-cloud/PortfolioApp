@echo off
REM ============================================================
REM  Configurar Chave HG Brasil.bat
REM  De um duplo-clique neste arquivo para salvar a chave da API
REM  HG Brasil Finance (taxas SELIC/CDI + cotacoes de reforco).
REM  A chave fica so no seu computador (nunca e enviada pra
REM  ninguem em texto puro).
REM ============================================================

setlocal
cd /d "%~dp0"

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

python configurar_chave_hgbrasil.py

echo.
echo (Se a janela acima fechou sem pedir uma tecla, algo bem incomum
echo  aconteceu - me avise.)
pause
