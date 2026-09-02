@echo off
REM ============================================================================
REM Desliga o Envio Automatico: remove a Tarefa Agendada criada pelo
REM "Instalar Envio Automatico.bat". Depois de rodar este arquivo, as
REM atualizacoes do PortfolioApp voltam a precisar ser enviadas manualmente
REM pelo GitHub Desktop (Commit + Push), como era antes.
REM ============================================================================

echo Desligando o envio automatico...
echo.

schtasks /delete /tn "PortfolioApp - Envio Automatico GitHub" /f >nul 2>&1

if errorlevel 1 (
    echo O envio automatico ja estava desligado ^(ou nunca foi instalado^).
) else (
    echo Pronto - o envio automatico foi desligado.
    echo A partir de agora, use o GitHub Desktop normalmente para enviar
    echo as atualizacoes ^(Commit + Push^).
)
echo.
pause
