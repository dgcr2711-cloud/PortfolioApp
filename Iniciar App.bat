@echo off
REM ============================================================
REM  Iniciar App.bat
REM  De um duplo-clique neste arquivo para abrir o app.
REM  Na primeira vez, ele instala tudo sozinho (pode demorar um
REM  pouco mais). Nas próximas vezes, abre direto.
REM ============================================================

setlocal
cd /d "%~dp0"

echo ============================================================
echo   Meu Portfolio B3 - verificando o computador...
echo ============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo O Python nao foi encontrado no seu computador.
    echo.
    echo 1. Acesse: https://www.python.org/downloads/
    echo 2. Baixe e abra o instalador.
    echo 3. IMPORTANTE: marque a caixinha "Add python.exe to PATH"
    echo    antes de clicar em Install Now.
    echo 4. Depois de instalar, feche esta janela e de um duplo-clique
    echo    neste arquivo de novo.
    echo.
    pause
    exit /b 1
)

if not exist "venv\Scripts\activate.bat" (
    echo Primeira vez rodando o app - preparando tudo, aguarde...
    echo (isso pode levar de 1 a 3 minutos, so acontece uma vez^)
    echo.
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo Nao foi possivel criar o ambiente. Copie o texto acima
        echo e me mostre para eu ajudar a resolver.
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    echo Instalando bibliotecas necessarias...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Houve um problema instalando as bibliotecas. Copie o
        echo texto acima e me mostre para eu ajudar a resolver.
        pause
        exit /b 1
    )
) else (
    call venv\Scripts\activate.bat
)

set TEM_CHAVE_FIREBASE=
if exist "firebase-service-account.json" set TEM_CHAVE_FIREBASE=1
if exist "%USERPROFILE%\.portfolio_b3_secrets\firebase-service-account.json" set TEM_CHAVE_FIREBASE=1
if defined TEM_CHAVE_FIREBASE (
    pip show firebase-admin >nul 2>nul
    if errorlevel 1 (
        echo Instalando biblioteca do celular ^(firebase-admin^)...
        pip install -r requirements-mobile.txt
    )
)

pip show pdfplumber >nul 2>nul
if errorlevel 1 (
    echo Instalando biblioteca de leitura de notas de corretagem ^(pdfplumber^)...
    pip install -r requirements.txt
)

pip show openpyxl >nul 2>nul
if errorlevel 1 (
    echo Instalando biblioteca de exportacao para Excel ^(openpyxl^)...
    pip install -r requirements.txt
)

pip show streamlit-authenticator >nul 2>nul
if errorlevel 1 (
    echo Instalando biblioteca de login do site ^(streamlit-authenticator^)...
    pip install -r requirements.txt
)

echo.
echo ============================================================
echo   Preparando o app do celular...
echo ============================================================
echo.

where node >nul 2>nul
if errorlevel 1 (
    echo O Node.js nao foi encontrado - o app do celular nao vai abrir agora.
    echo Baixe em https://nodejs.org ^(versao LTS^) se quiser usar o celular.
    echo O app do PC abre normalmente mesmo assim.
    echo.
) else (
    if not exist "mobile-app\node_modules" (
        echo Primeira vez com o app do celular - instalando, aguarde um pouco...
        pushd mobile-app
        call npm install
        popd
    )
    echo Abrindo o servidor do celular numa segunda janela...
    start "Meu Portfolio B3 - Celular" "%~dp0mobile-app\Iniciar Celular.bat"
)

echo.
echo ============================================================
echo   Abrindo o app no seu navegador...
echo   (para fechar o app depois, feche esta janela preta
echo    E a janela preta do celular que abriu junto)
echo ============================================================
echo.

REM O app agora roda com "headless=true" (necessario para funcionar
REM hospedado no Streamlit Cloud - ver .streamlit/config.toml), entao o
REM Streamlit nao abre mais o navegador sozinho. Esta linha abre o
REM navegador manualmente depois de alguns segundos, pra manter a mesma
REM experiencia de sempre no seu PC.
start "" cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:8501"

streamlit run app.py

pause
