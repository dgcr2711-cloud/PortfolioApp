"""
Script de verificação de alertas em SEGUNDO PLANO (2026-08-30).

Diferente do e-mail de alerta "normal" (core/notificacoes_email.py), que só
é verificado quando ALGUÉM clica em "🔄 Atualizar Dados" (no seu PC ou no
dashboard hospedado), este script roda sozinho, num horário fixo, mesmo que
ninguém abra o app naquele dia — pelo GitHub Actions (ver
.github/workflows/verificar_alertas.yml para o agendamento).

O que ele faz, em ordem:
  1. Lê a carteira mais recente do Firestore (a mesma "fonte da verdade"
     usada pelo PC e pelos dashboards hospedados — ver core/data_store.py).
  2. Busca cotações novas no Yahoo Finance para as posições e a watchlist.
  3. Compara com os alertas de preço-alvo configurados e manda e-mail para
     os que acabaram de ser atingidos (core/notificacoes_email.py — mesma
     lógica, mesmos testes, do botão "Atualizar Dados").
  4. Salva de volta no Firestore a cotação nova e quais alertas já foram
     notificados — assim o PC e os dashboards hospedados veem o mesmo
     estado na próxima vez que abrirem, sem reenviar e-mail duplicado.

Onde ficam as credenciais aqui? Este script roda numa máquina do GitHub,
não no seu PC — não existe a pasta pessoal (~/.portfolio_b3_secrets) nem um
app Streamlit de verdade rodando. Por isso a chave do Firebase e a
configuração de e-mail vêm de "Secrets" do próprio repositório do GitHub
(Settings -> Secrets and variables -> Actions), expostos a este script como
variáveis de ambiente — ver core/cloud_sync.py::_obter_credenciais_dict_da_
variavel_de_ambiente e core/notificacoes_email.py::_carregar_config_da_
variavel_de_ambiente. Nunca ficam no código nem são commitados.

Nunca lança exceção "para cima": qualquer problema (sem cotação para um
ticker, Firestore fora do ar, etc.) já é tratado dentro das próprias
funções reaproveitadas aqui (mesmas usadas e testadas no app principal) —
este script só decide o que imprimir no log do GitHub Actions e qual código
de saída devolver.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Permite rodar este script diretamente (python scripts/verificar_alertas_segundo_plano.py)
# sem precisar instalar o projeto como pacote — mesmo truque usado em app.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import calculations as calc  # noqa: E402
from core import market_data  # noqa: E402
from core.data_store import carregar_dados, salvar_dados  # noqa: E402
from core.notificacoes_email import (  # noqa: E402
    notificacoes_configuradas,
    verificar_e_notificar_alertas,
)
from ui.ativos import montar_lista_ativos  # noqa: E402


def main() -> int:
    if not notificacoes_configuradas():
        print(
            "[alertas] Configuração de e-mail não encontrada (variáveis de ambiente "
            "EMAIL_ALERTA_* ausentes) — nada a fazer. Verifique os Secrets do repositório."
        )
        return 0

    dados = carregar_dados()

    if not dados.get("alertas"):
        print("[alertas] Nenhum alerta de preço-alvo configurado na carteira — nada a verificar.")
        return 0

    posicoes = calc.consolidar_posicoes(dados["compras"], dados["eventos"])
    tickers_posicoes = {p["ticker"] for p in posicoes}
    tickers_alvo = [t for t in dados["watchlist"] if t not in tickers_posicoes]
    tickers = [p["ticker"] for p in posicoes] + tickers_alvo

    if not tickers:
        print("[alertas] Nenhuma posição nem empresa-alvo na carteira — nada a verificar.")
        return 0

    print(f"[alertas] Buscando cotação de {len(tickers)} ativo(s) no Yahoo Finance...")
    novas_cotacoes, falhas = market_data.atualizar_cotacoes(tickers, dados["cotacoes"])
    dados["cotacoes"] = novas_cotacoes
    if falhas:
        print(f"[alertas] Aviso: sem cotação para {', '.join(falhas)} nesta tentativa.")

    cotacao_por_ticker = {a["ticker"]: a["cotacao_atual"] for a in montar_lista_ativos(dados)}
    enviados = verificar_e_notificar_alertas(dados, cotacao_por_ticker)

    salvar_dados(dados)  # também grava no Firestore, pra manter o PC e os dashboards em dia

    plural = "s" if enviados != 1 else ""
    print(f"[alertas] Verificação concluída. {enviados} e-mail{plural} de alerta enviado{plural}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
