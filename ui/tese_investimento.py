"""
Aba "📓 Diário de Tese" — por que você comprou (ou está de olho em) cada
ativo, e o que reavaliar se a tese mudar. Pedido explícito da auditoria:
"o melhor investidor de value investing escreve por que comprou, não só
o que comprou" — este diário é justamente esse hábito, dentro do app.

Cada ativo acumula uma LISTA de entradas ao longo do tempo (nunca
sobrescreve a anterior) — a ideia é reler daqui a um ano e comparar o que
você escreveu com o que realmente aconteceu.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from core import calculations as calc
from core import teses
from core.config import COR_NEGATIVO, COR_POSITIVO
from core.formatting import formatar_moeda_priv, formatar_pct
from ui.ativos import todos_os_tickers
from ui.styles import card_kpi_html, render_cards


def _formatar_data_hora(data_iso: str) -> str:
    try:
        return datetime.fromisoformat(data_iso).strftime("%d/%m/%Y às %H:%M")
    except ValueError:
        return data_iso


def render(dados: dict, ocultar_valores: bool, salvar) -> None:
    st.title("Diário de Tese de Investimento")
    st.caption(
        "Por que você comprou (ou está de olho em) cada ativo — e o que reavaliar se a tese mudar. "
        "Escreva pensando no \"eu\" de daqui a um ano, tentando entender a decisão de hoje."
    )

    tickers = todos_os_tickers(dados)
    if not tickers:
        st.info(
            'Nenhum ativo ainda. Registre uma compra na aba "🧾 Compras & Vendas" ou adicione uma '
            'empresa-alvo na aba "📈 Carteira" antes de começar o diário.'
        )
        return

    tickers_com_tese = set(teses.tickers_com_tese(dados))
    rotulos = [f"{t} 📓" if t in tickers_com_tese else t for t in tickers]
    indice_escolhido = st.selectbox("Ativo", range(len(tickers)), format_func=lambda i: rotulos[i])
    ticker = tickers[indice_escolhido]

    _painel_contexto(dados, ticker, ocultar_valores)

    with st.form(f"form_tese_{ticker}", clear_on_submit=True, border=True):
        texto = st.text_area(
            "Nova entrada",
            placeholder=(
                "Ex: Comprei pensando no crescimento de X% ao ano nos próximos 5 anos, "
                "com margem de segurança de 20% sobre o Preço Teto calculado. Reavaliar se..."
            ),
            height=140,
            max_chars=teses.LIMITE_CARACTERES_TEXTO,
        )
        enviado = st.form_submit_button("💾 Salvar entrada", type="primary")
        if enviado:
            try:
                teses.adicionar_entrada(dados, ticker, texto)
            except ValueError as e:
                st.error(str(e))
            else:
                salvar(dados)
                st.rerun()

    entradas = teses.listar_entradas(dados, ticker)
    if not entradas:
        st.caption(f"Nenhuma entrada ainda para {ticker}. Escreva a primeira acima.")
        return

    st.subheader(f"Histórico — {ticker}")
    for entrada in entradas:
        with st.container(border=True):
            col_data, col_remover = st.columns([5, 1])
            col_data.caption(_formatar_data_hora(entrada["data"]))
            if col_remover.button("🗑️", key=f"rm_tese_{entrada['id']}", help="Remover esta entrada"):
                teses.remover_entrada(dados, ticker, entrada["id"])
                salvar(dados)
                st.rerun()
            st.write(entrada["texto"])


def _painel_contexto(dados: dict, ticker: str, ocultar_valores: bool) -> None:
    """Um lembrete rápido dos números atuais do ativo, para ler a tese antiga já comparando com a realidade de hoje."""
    posicoes = calc.calcular_posicoes_completas(dados["compras"], dados["eventos"], dados["cotacoes"])
    posicao = next((p for p in posicoes if p["ticker"] == ticker), None)

    pt = dados.get("precosTeto", {}).get(ticker)
    preco_teto = pt["precoTeto"] if pt else None

    cards = []
    if posicao:
        cards.append(card_kpi_html("Preço Médio", formatar_moeda_priv(posicao["preco_medio_ponderado"], ocultar_valores)))
        cards.append(card_kpi_html("Cotação Atual", formatar_moeda_priv(posicao["cotacao_atual"], False)))
        sinal = "+" if posicao["lucro_pct"] >= 0 else ""
        cor_resultado = COR_POSITIVO if posicao["lucro_pct"] >= 0 else COR_NEGATIVO
        cards.append(card_kpi_html("Resultado", f"{sinal}{formatar_pct(posicao['lucro_pct'])}", cor_valor=cor_resultado))
    else:
        cards.append(card_kpi_html("Preço Médio", "— empresa-alvo"))
        cot = dados["cotacoes"].get(ticker)
        cards.append(card_kpi_html("Cotação Atual", formatar_moeda_priv(cot["preco"], False) if cot else "— sem cotação"))
        cards.append(card_kpi_html("Resultado", "—"))
    cards.append(card_kpi_html("Preço Teto", formatar_moeda_priv(preco_teto, False) if preco_teto else "— não calculado"))
    render_cards(cards)
