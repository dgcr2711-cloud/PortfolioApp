@echo off
REM Aberto automaticamente pelo "Iniciar App.bat" da pasta principal.
REM Pode fechar esta janela quando terminar de usar o app no celular.
cd /d "%~dp0"

if not exist "node_modules\@react-native-async-storage" (
    echo Nova funcionalidade instalada ^(PIN de acesso^) - baixando uma
    echo biblioteca nova, so acontece uma vez, aguarde...
    call npm install
    echo.
)

npx expo start
pause
