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

if not exist "node_modules\react-native-svg" (
    echo Nova funcionalidade instalada ^(grafico de alocacao em rosca^) -
    echo baixando uma biblioteca nova, so acontece uma vez, aguarde...
    call npm install
    echo.
)

echo ============================================================
echo  Abrindo em modo "de qualquer lugar" (tunel) - assim o celular
echo  NAO precisa estar no mesmo Wi-Fi do computador pra funcionar.
echo  Pode usar dados moveis (4G/5G) no celular tranquilamente.
echo.
echo  Na PRIMEIRA vez, pode aparecer uma pergunta no meio do caminho
echo  perguntando se pode instalar uma ferramenta extra (ngrok) -
echo  digite Y e aperte Enter pra aceitar. So acontece uma vez.
echo.
echo  Se demorar demais pra conectar ou a conexao ficar instavel,
echo  fecha esta janela e me avisa - tem um modo mais rapido (mesmo
echo  Wi-Fi) como alternativa.
echo ============================================================
echo.

REM -c limpa o cache do empacotador (Metro) antes de abrir — sem isso, às
REM vezes uma mudança recente no app não aparece no celular mesmo depois de
REM fechar e abrir de novo, porque ele reaproveita uma versão antiga
REM guardada em cache. Deixa a abertura alguns segundos mais lenta, mas
REM garante que o celular sempre pega a versão mais nova de verdade.
npx expo start --tunnel -c
pause
