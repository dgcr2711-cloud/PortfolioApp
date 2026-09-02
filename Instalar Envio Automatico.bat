@echo off
setlocal
REM ============================================================================
REM Instala o Envio Automatico: cria uma Tarefa Agendada do Windows que roda
REM sozinha, a cada 20 minutos, para sempre (mesmo depois de reiniciar o
REM computador) - sem voce precisar abrir o GitHub Desktop nem clicar em nada.
REM
REM So precisa rodar este arquivo UMA VEZ (dois cliques nele). Depois disso
REM pode fechar e esquecer que ele existe.
REM
REM O resultado (sucesso ou erro) e escrito num arquivo de texto que abre
REM sozinho no Bloco de Notas - assim nao tem pressa nenhuma pra ler, ao
REM contrario da janela preta que fecha rapido demais.
REM ============================================================================

set "LOG=%~dp0resultado_instalacao.txt"

(
echo ============================================================
echo   Instalando o Envio Automatico para o GitHub
echo ============================================================
echo Rodado em: %date% %time%
echo.
) > "%LOG%"

REM Confere se o "git" esta disponivel neste computador antes de continuar.
where git >nul 2>&1
if errorlevel 1 (
    (
    echo [ERRO] O programa "git" nao foi encontrado neste computador.
    echo.
    echo Isso pode acontecer porque o GitHub Desktop, em alguns casos, nao
    echo deixa o "git" disponivel para outros programas usarem. Para
    echo resolver, instale o "Git for Windows" pelo link abaixo e depois
    echo rode este arquivo de novo ^(dois cliques nele^):
    echo.
    echo   https://git-scm.com/download/win
    echo.
    echo ^(Pode aceitar todas as opcoes padrao durante a instalacao.^)
    ) >> "%LOG%"
    start "" notepad "%LOG%"
    exit /b 1
)

schtasks /create /tn "PortfolioApp - Envio Automatico GitHub" /tr "\"%~dp0sync_para_github.bat\"" /sc minute /mo 20 /f >nul 2>&1

if errorlevel 1 (
    (
    echo [ERRO] Nao foi possivel criar a tarefa agendada.
    echo.
    echo Tente de novo clicando com o botao DIREITO neste arquivo e
    echo escolhendo "Executar como administrador".
    ) >> "%LOG%"
    start "" notepad "%LOG%"
    exit /b 1
)

(
echo PRONTO! Envio automatico instalado com sucesso.
echo.
echo A partir de agora, a cada 20 minutos o seu computador vai checar
echo sozinho se ha alguma atualizacao pendente do PortfolioApp e enviar
echo para o GitHub automaticamente - sem voce precisar abrir o GitHub
echo Desktop nem clicar em Commit/Push nunca mais.
echo.
echo Isso vale tanto para as atualizacoes que eu ^(Claude^) te enviar de
echo agora em diante quanto para qualquer alteracao que ja esteja no seu
echo computador aguardando envio.
echo.
echo Se um dia quiser desligar isso, use o arquivo
echo "Desativar Envio Automatico.bat".
) >> "%LOG%"

start "" notepad "%LOG%"
exit /b 0
