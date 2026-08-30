@echo off
REM ============================================================
REM  Rodar Testes.bat
REM  De um duplo-clique neste arquivo para conferir se o motor de
REM  calculo do app (preco medio, preco teto, Imposto de Renda,
REM  concentracao da carteira etc.) continua calculando tudo
REM  certinho. Isso NAO mexe nos seus dados nem precisa do app
REM  aberto - e so uma bateria de contas de conferencia.
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

pip show openpyxl >nul 2>nul
if errorlevel 1 (
    echo Instalando bibliotecas do app que ainda faltam neste ambiente...
    pip install -r requirements.txt
    echo.
)

pip show pytest >nul 2>nul
if errorlevel 1 (
    echo Instalando a ferramenta de testes ^(pytest^), so acontece uma vez...
    pip install -r requirements-dev.txt
    echo.
)

echo ============================================================
echo   Conferindo o motor de calculo do app...
echo ============================================================
echo.

python -m pytest -v

echo.
echo ============================================================
echo   Se aparecer "passed" em verde acima, esta tudo certo.
echo   Se aparecer "failed" em vermelho, me manda o texto acima
echo   que eu explico o que aconteceu.
echo ============================================================
echo.
pause
