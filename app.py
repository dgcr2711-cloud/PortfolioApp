"""
Meu Portfólio B3 — Dashboard de Investimentos (versão Streamlit)
==================================================================

Ponto de entrada do app. Rode com:

    streamlit run app.py

Este arquivo só monta a página (barra lateral + qual aba está ativa) e
delega TODO o conteúdo de cada aba para os módulos em ui/. Se você quiser
adicionar uma aba nova no futuro:

    1. Crie ui/minha_aba.py com uma função render(dados, ...).
    2. Importe o módulo aqui embaixo.
    3. Acrescente o nome da aba na lista ABAS e um "elif" correspondente.

A lógica de cálculo (preço médio, preço teto, IR, TWR etc.) mora em
core/calculations.py — nada disso depende do Streamlit, então ela pode ser
reaproveitada ou testada isoladamente.
"""

from __future__ import annotations

import streamlit as st

from core import cloud_sync
from core.data_store import carregar_dados, esta_no_modo_demo, salvar_dados
from ui import (
    carteira,
    compras,
    configuracoes,
    evolucao,
    fundamentos,
    imposto_renda,
    preco_teto,
    proventos,
    tese_investimento,
    visao_geral,
)
from ui.acoes_comuns import atualizar_dados, exibir_status_cotacoes
from ui.styles import desativar_traducao_automatica, injetar_css

st.set_page_config(page_title="Meu Portfólio B3", page_icon="📊", layout="wide")
injetar_css()
desativar_traducao_automatica()

# Correção de segurança (2026-08-30): chama isto uma vez, logo na abertura do
# app, para que a chave do Firebase (se ainda estiver no local antigo, dentro
# da pasta do projeto) seja movida para fora dela imediatamente — sem
# depender de o usuário clicar em "🔄 Atualizar Dados" primeiro. Ver
# core/cloud_sync.py::_migrar_chave_antiga_se_necessario().
cloud_sync.sincronizacao_configurada()

# ----------------------------------------------------------------------
# Estado da sessão: os dados da carteira ficam em st.session_state para não
# precisar reler o arquivo do disco a cada interação. Toda alteração passa
# por salvar_estado(), que atualiza a sessão E grava no disco imediatamente
# — assim você nunca perde uma alteração ao fechar o navegador.
# ----------------------------------------------------------------------
if "dados" not in st.session_state:
    st.session_state["dados"] = carregar_dados()


def salvar_estado(novos_dados: dict) -> None:
    st.session_state["dados"] = novos_dados
    salvar_dados(novos_dados)


dados = st.session_state["dados"]

# Aviso do link de demonstração (2026-08-30) — ver
# core/data_store.py::_modo_demo_ativo(). Fica bem visível, logo no topo,
# pra quem receber esse link (ex: um amigo) nunca confundir a carteira
# fictícia mostrada aqui com dados reais de alguém.
if esta_no_modo_demo():
    st.info("🎭 **Modo demonstração** — esta é uma carteira fictícia, só para mostrar como o app funciona. Nenhum dado real.")

ABAS = [
    "🏠 Visão Geral",
    "📈 Carteira",
    "🧾 Compras & Vendas",
    "📅 Proventos",
    "🎯 Preço Teto",
    "🔎 Fundamentos",
    "📊 Evolução",
    "🏛️ Imposto de Renda",
    "📓 Diário de Tese",
    "⚙️ Configurações",
]

# Agrupamento das 10 abas em categorias — só para organizar visualmente a
# barra lateral (que estava com uma lista única de 10 opções, ficando longa
# de rolar/escanear). Cada aba de ABAS precisa aparecer em exatamente um
# grupo aqui (checado logo abaixo, na inicialização) — nenhuma lógica de
# cálculo ou de outra aba depende desse agrupamento.
GRUPOS_ABAS = [
    ("📊 Carteira & Fundamentos", ["🏠 Visão Geral", "📈 Carteira", "🔎 Fundamentos"]),
    ("💰 Movimentações", ["🧾 Compras & Vendas", "📅 Proventos", "🎯 Preço Teto"]),
    ("📈 Análise & Impostos", ["📊 Evolução", "🏛️ Imposto de Renda", "📓 Diário de Tese"]),
    ("⚙️ Sistema", ["⚙️ Configurações"]),
]
assert sorted(aba for _, abas in GRUPOS_ABAS for aba in abas) == sorted(ABAS), (
    "GRUPOS_ABAS ficou dessincronizado de ABAS — toda aba precisa estar em exatamente um grupo."
)

if "aba_ativa" not in st.session_state:
    st.session_state["aba_ativa"] = ABAS[0]

with st.sidebar:
    st.markdown("### 📊 Meu Portfólio")
    st.caption("Ações B3")

    for titulo_grupo, abas_do_grupo in GRUPOS_ABAS:
        grupo_tem_aba_ativa = st.session_state["aba_ativa"] in abas_do_grupo
        with st.expander(titulo_grupo, expanded=grupo_tem_aba_ativa):
            for nome_aba in abas_do_grupo:
                esta_ativa = nome_aba == st.session_state["aba_ativa"]
                if st.button(
                    nome_aba,
                    key=f"nav_{nome_aba}",
                    use_container_width=True,
                    type="primary" if esta_ativa else "secondary",
                ):
                    st.session_state["aba_ativa"] = nome_aba
                    st.rerun()

    aba_ativa = st.session_state["aba_ativa"]

    st.divider()

    ocultar_valores = st.toggle(
        "👁️ Ocultar valores", value=st.session_state.get("ocultar_valores", False),
        help="Mascara valores em R$ e quantidades na tela (útil ao compartilhar a tela).",
    )
    st.session_state["ocultar_valores"] = ocultar_valores

    # Botão pedido explicitamente no projeto: força uma busca nova de
    # preços no Yahoo Finance, ignorando o cache de 5 minutos.
    if st.button("🔄 Atualizar Dados", use_container_width=True, type="primary"):
        atualizar_dados(dados, salvar_estado)
        st.rerun()

    exibir_status_cotacoes()

    st.divider()
    st.caption("💡 Dica: os dados ficam salvos automaticamente a cada alteração, em data/portfolio_data.json.")


if aba_ativa == "🏠 Visão Geral":
    visao_geral.render(dados, ocultar_valores)
elif aba_ativa == "📈 Carteira":
    carteira.render(dados, ocultar_valores, salvar_estado)
elif aba_ativa == "🧾 Compras & Vendas":
    compras.render(dados, ocultar_valores, salvar_estado)
elif aba_ativa == "📅 Proventos":
    proventos.render(dados, ocultar_valores, salvar_estado)
elif aba_ativa == "🎯 Preço Teto":
    preco_teto.render(dados, salvar_estado)
elif aba_ativa == "🔎 Fundamentos":
    fundamentos.render(dados, salvar_estado)
elif aba_ativa == "📊 Evolução":
    evolucao.render(dados, salvar_estado)
elif aba_ativa == "🏛️ Imposto de Renda":
    imposto_renda.render(dados, ocultar_valores)
elif aba_ativa == "📓 Diário de Tese":
    tese_investimento.render(dados, ocultar_valores, salvar_estado)
elif aba_ativa == "⚙️ Configurações":
    configuracoes.render(dados, salvar_estado)

# Atualização automática ao abrir (pedido de Diego, 2026-08-31, otimizada
# em 2026-08-31 pra não travar mais a tela toda): roda "🔄 Atualizar
# Dados" sozinha uma única vez por sessão do navegador — vale tanto
# abrindo pela pasta (Iniciar App.bat) quanto por um link salvo, porque as
# duas formas resultam numa aba nova do navegador, que é exatamente o que
# dispara uma sessão nova aqui. A trava por session_state garante que isso
# acontece só nessa primeira vez: cliques depois (trocar de aba, registrar
# uma compra etc.) causam reruns do script mas não disparam a busca de
# novo. Desligável na aba Configurações (dados["atualizarAutomaticamenteAoAbrir"])
# para quem preferir o app abrindo mais rápido, sem essa busca automática.
#
# Fica de propósito DEPOIS de toda a barra lateral e do conteúdo da aba
# ativa (que já foram desenhados acima, usando os últimos dados salvos em
# disco — instantâneo, sem rede): assim a tela aparece na hora com o que
# já tinha, e só depois a busca roda por trás, com um aviso pequeno lá na
# barra lateral (reaberta abaixo) — em vez da tela inteira ficar em branco
# esperando "Buscando cotações..." antes de mostrar qualquer coisa, como
# acontecia antes.
if dados.get("atualizarAutomaticamenteAoAbrir", True) and not st.session_state.get("atualizacao_automatica_feita"):
    st.session_state["atualizacao_automatica_feita"] = True
    with st.sidebar:
        atualizar_dados(dados, salvar_estado)
    st.rerun()
