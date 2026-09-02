@echo off
REM ============================================================================
REM Script "trabalhador": e chamado sozinho pelo Agendador de Tarefas do
REM Windows a cada 20 minutos (ver "Instalar Envio Automatico.bat"). Roda em
REM segundo plano, sem abrir nenhuma janela visivel na maioria das vezes.
REM
REM O que faz: se houver qualquer arquivo novo ou alterado no projeto desde o
REM ultimo envio, envia (commit + push) automaticamente para o GitHub. Se nao
REM houver nada novo, nao faz nada (nao gera commits vazios).
REM
REM Por que isso importa: o robo automatico de alertas de WhatsApp (GitHub
REM Actions) e o site hospedado no Streamlit Cloud SEMPRE rodam a versao que
REM esta no GitHub, nunca a que esta so no seu computador — sem isso, toda
REM correcao/melhoria ficaria "presa" no seu PC ate voce abrir o GitHub
REM Desktop manualmente e clicar em Commit/Push.
REM ============================================================================

cd /d "%~dp0"

git add -A >nul 2>&1

REM "git diff --cached --quiet" devolve 0 se NAO ha nada preparado pra
REM commitar (nada mudou) — nesse caso, sai sem fazer nada.
git diff --cached --quiet
if %errorlevel% equ 0 (
    exit /b 0
)

git commit -m "Atualizacao automatica (envio agendado do Windows)" >nul 2>&1
git push >nul 2>&1

exit /b 0
