@echo off
REM ============================================================
REM  Gerar App Android.bat
REM  De um duplo-clique neste arquivo para gerar um instalavel
REM  (.apk) de verdade do app do celular -- sem precisar do
REM  tunel do Expo, sem precisar do PC ligado depois de instalado,
REM  e sem publicar em loja nenhuma (fica so no seu celular).
REM
REM  Na PRIMEIRA vez que voce rodar isto, vai aparecer um passo
REM  a mais: pedindo pra voce fazer login (ou criar uma conta
REM  gratuita) no site expo.dev -- é a Amazon/plataforma que
REM  monta o instalavel pra voce, de graca, na nuvem. So precisa
REM  fazer isso uma vez.
REM
REM  Quando terminar (10-20 minutos, roda na nuvem, pode deixar
REM  a janela aberta em segundo plano), aparece um link no final
REM  -- abra esse link no PROPRIO CELULAR (manda o link por
REM  WhatsApp pra voce mesmo, por exemplo) e baixe o .apk direto
REM  la. O Android vai avisar "app de fonte desconhecida" --
REM  normal, e' so confirmar que voce quer instalar mesmo.
REM ============================================================

setlocal
cd /d "%~dp0"

if not exist "node_modules" (
    echo Parece que e' a primeira vez rodando o app do celular neste
    echo computador. De um duplo-clique em "Iniciar Celular.bat"
    echo primeiro (so pra instalar as dependencias), feche, e depois
    echo rode este arquivo de novo.
    echo.
    pause
    exit /b 1
)

echo.
echo Gerando o instalavel Android na nuvem (Expo/EAS)...
echo Se pedir login, e' a sua conta gratuita do expo.dev.
echo.

call npx eas-cli@latest build --platform android --profile preview

echo.
echo Pronto! Se aparecer um link acima, abra ele NO CELULAR (nao
echo aqui no PC) pra baixar e instalar o app de verdade.
echo.
pause
