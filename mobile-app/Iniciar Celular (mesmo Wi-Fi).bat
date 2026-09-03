@echo off
REM Modo alternativo/mais rapido - só funciona com o celular no MESMO Wi-Fi
REM do computador. Use este se o modo "de qualquer lugar" (tunel, no botao
REM normal "Iniciar Celular.bat") estiver lento ou nao conectar.
cd /d "%~dp0"

if not exist "node_modules\@react-native-async-storage" (
    echo Nova funcionalidade instalada ^(PIN de acesso^) - baixando uma
    echo biblioteca nova, so acontece uma vez, aguarde...
    call npm install
    echo.
)

if not exist "node_modules\react-native-svg" (
    echo Nova funcionalidade instalada ^(grafico de alocacao em rosca^) -
    echo baixando uma biblioteca nova, so acontece uma vez, aguarde...
    call npm install
    echo.
)

npx expo start
pause
