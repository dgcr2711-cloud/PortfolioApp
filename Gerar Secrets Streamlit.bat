@echo off
REM ============================================================
REM  Gerar Secrets Streamlit.bat
REM  De um duplo-clique neste arquivo para gerar o texto pronto
REM  para colar no painel "Secrets" do seu app hospedado no
REM  Streamlit Community Cloud (share.streamlit.io). So precisa
REM  rodar isto quando for hospedar o dashboard, ou se trocar a
REM  chave do Firebase / a configuracao de e-mail depois.
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

python gerar_secrets_streamlit.py

REM Abre o resultado sozinho no Bloco de Notas (2026-09-04) - antes disso
REM era preciso ir procurar o arquivo manualmente, o que confundia.
start "" notepad "%USERPROFILE%\.portfolio_b3_secrets\secrets_streamlit_gerado.txt"

echo.
pause
