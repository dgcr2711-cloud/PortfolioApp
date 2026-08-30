"""
Aba "🏛️ Imposto de Renda" — o estudo completo de IR para renda variável
(pessoa física, ações à vista na B3) pedido para o app: uma parte
educativa (o "porquê" de cada regra, explicado em português simples) e uma
parte interativa (os cálculos aplicados nos SEUS dados reais de compras,
vendas e proventos).

Este módulo só monta a tela; todo o cálculo mora em core/imposto_renda.py
(mais completo que o resumo rápido que já existe na aba Compras & Vendas —
aquele é uma estimativa simples, este separa Day Trade de Swing Trade,
compensa prejuízo mês a mês e já desconta o IRRF retido).

IMPORTANTE: isto é uma ferramenta de organização e estudo, escrita com base
em pesquisa da legislação vigente em 2026 (incluindo a Lei 15.270/2025, que
passou a tributar dividendos pela primeira vez a partir de 01/01/2026) —
não é, e não substitui, a orientação de um contador. A Receita Federal e a
regulamentação de pontos da lei nova podem mudar; sempre confira o "Informe
de Rendimentos" da sua corretora antes de declarar ou pagar qualquer DARF.
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from core import calculations as calc
from core import imposto_renda as ir
from core.formatting import formatar_data_br, formatar_moeda, formatar_moeda_priv, formatar_numero


def render(dados: dict, ocultar_valores: bool) -> None:
    st.title("Imposto de Renda")
    st.caption("Estudo completo de IR para ações na B3 — regras vigentes em 2026, aplicadas à sua carteira")

    st.warning(
        "⚠️ **Isto é uma ferramenta de estudo e organização, não uma declaração pronta.** "
        "Os cálculos aqui são estimativas feitas com base na legislação vigente — sempre confira o "
        "**Informe de Rendimentos** que sua corretora emite todo ano (é a fonte oficial dos valores) "
        "e, principalmente em anos de mudança de lei como 2026, considere confirmar com um contador "
        "antes de pagar um DARF ou entregar a declaração anual."
    )

    _estudo()
    st.divider()
    _resumo_mensal_interativo(dados, ocultar_valores)
    st.divider()
    _bens_e_direitos(dados, ocultar_valores)
    st.divider()
    _proventos_do_ano(dados, ocultar_valores)


# ==========================================================================
# Parte 1 — o estudo (educativo)
# ==========================================================================

def _estudo() -> None:
    st.subheader("📖 O estudo: como funciona o IR em ações")

    with st.expander("🔎 Visão geral — as duas modalidades"):
        st.markdown(
            "Para quem investe em ações comuns na B3, existem **duas modalidades** de operação, "
            "e a Receita Federal trata cada uma com regras próprias — inclusive prejuízo de uma "
            "modalidade **não compensa** ganho da outra:\n\n"
            "- **Swing Trade**: compra e venda em dias diferentes (o caso mais comum para quem "
            "investe pensando em médio/longo prazo).\n"
            "- **Day Trade**: compra e venda do MESMO ativo no MESMO dia.\n\n"
            "Se você comprou e vendeu um pouco do mesmo ativo no mesmo dia, mas também tinha (ou "
            "ficou com) uma parte que não foi negociada nesse mesmo dia, a Receita separa: a parte "
            "que virou compra-e-venda no dia é Day Trade, o resto segue como Swing Trade. É "
            "exatamente essa separação que a seção **Resumo Mensal** logo abaixo faz automaticamente "
            "com os seus dados."
        )

    with st.expander("📈 Swing Trade — a regra do dia a dia"):
        st.markdown(
            "- Alíquota: **15% sobre o lucro** do mês nessa modalidade.\n"
            "- **Isenção**: se o total **vendido** no mês (soma do valor de venda de todas as "
            "operações de Swing Trade, não o lucro) for **até R$ 20.000**, o lucro fica isento de "
            "IR naquele mês — mas o prejuízo, se houver, continua podendo ser compensado depois.\n"
            "- O lucro é calculado pelo **preço médio ponderado** de compra do ativo na data da "
            "venda (não pelo preço da compra específica que 'saiu primeiro').\n"
            "- Fundos Imobiliários (FIIs) seguem uma regra diferente e mais simples: **não têm "
            "faixa de isenção** — todo ganho de capital na venda de cotas de FII paga 20%, "
            "qualquer que seja o valor vendido no mês (ver seção própria abaixo)."
        )

    with st.expander("⚡ Day Trade — a regra mais rígida"):
        st.markdown(
            "- Alíquota: **20% sobre o lucro** do dia/mês.\n"
            "- **Não existe isenção nenhuma** para Day Trade, seja qual for o valor operado no mês — "
            "diferente do Swing Trade.\n"
            "- Prejuízo de Day Trade só compensa lucro de Day Trade (nunca de Swing Trade, e "
            "vice-versa)."
        )

    with st.expander("💸 IRRF — o \"dedo-duro\" que já é antecipação do imposto"):
        st.markdown(
            "A sua corretora é obrigada a reter automaticamente um pequeno valor de IR na fonte em "
            "toda operação de venda — é o chamado **IRRF \"dedo-duro\"**, que serve para a Receita "
            "rastrear quem operou na bolsa. Ele **não é um imposto extra**: é uma antecipação do "
            "imposto que você deve, e entra como **crédito** no DARF do mês (ou pode até gerar "
            "restituição, se o total retido no ano superar o imposto devido).\n\n"
            "- **Swing Trade**: 0,005% sobre o valor de cada **venda**.\n"
            "- **Day Trade**: 1% sobre o **lucro positivo** apurado no dia.\n\n"
            "O valor exato retido no ano vem no Informe de Rendimentos da corretora — os valores "
            "mostrados nesta aba são estimativas calculadas com essas mesmas alíquotas."
        )

    with st.expander("🔄 Compensação de prejuízos"):
        st.markdown(
            "Prejuízo em ações pode ser compensado com lucro futuro **sem prazo de prescrição** — "
            "não expira nunca, mesmo que leve anos para você voltar a ter lucro. A única regra é "
            "que a compensação só vale **dentro da mesma modalidade**: prejuízo de Swing Trade só "
            "abate lucro de Swing Trade; prejuízo de Day Trade só abate lucro de Day Trade.\n\n"
            "Isso vale mesmo em meses isentos: se você teve prejuízo de Swing Trade num mês em que "
            "o total vendido também estava dentro da faixa de isenção, o prejuízo continua sendo "
            "acumulado e disponível para abater lucro de um mês futuro — a seção Resumo Mensal "
            "abaixo já mantém esse saldo automaticamente, mês a mês."
        )

    with st.expander("🧾 DARF — o boleto do imposto"):
        st.markdown(
            "- **Código da receita: 6015** (\"IRPF – Ganhos Líquidos em Operações em Bolsa\").\n"
            "- **Prazo**: até o **último dia útil do mês seguinte** ao mês em que a venda com lucro "
            "aconteceu (ex: lucro apurado em março, DARF vence no último dia útil de abril).\n"
            "- **Valor mínimo**: se o imposto devido do mês, depois de compensar prejuízo e "
            "descontar o IRRF, ficar **abaixo de R$ 10**, você não precisa pagar naquele mês — o "
            "valor é somado ao imposto devido do próximo mês em que o total ultrapassar o mínimo.\n"
            "- Atraso gera multa e juros (Selic) como qualquer outro imposto federal — vale a pena "
            "gerar o DARF (no site/app da Receita, ou pelo próprio sistema da corretora, se "
            "oferecido) assim que souber que deve."
        )

    with st.expander("🏢 Fundos Imobiliários (FIIs) e BDRs — só para referência"):
        st.markdown(
            "Você ainda não opera FIIs nem BDRs nesta carteira, mas fica o resumo caso passe a "
            "operar:\n\n"
            "- **FIIs**: rendimentos mensais distribuídos já são **isentos de IR** para pessoa "
            "física (desde que o fundo tenha no mínimo 50 cotistas e as cotas sejam negociadas só "
            "em bolsa/balcão organizado, o que é o caso da imensa maioria). Já o **ganho de capital "
            "na venda de cotas** paga **20%**, sem qualquer faixa de isenção por valor vendido no "
            "mês — diferente das ações comuns.\n"
            "- **BDRs** (recibos de ações estrangeiras negociados na B3): tributados igual a ações "
            "comuns — 15% Swing / 20% Day Trade, com a mesma faixa de isenção de R$ 20.000/mês para "
            "Swing Trade."
        )

    with st.expander("💰 Proventos (dividendos e JCP) — a grande novidade de 2026"):
        st.markdown(
            "**Lei 15.270/2025**, sancionada em 26/11/2025 e em vigor desde **1º de janeiro de "
            "2026**, passou a tributar **dividendos** pela primeira vez na história recente do "
            "país (antes, todo dividendo era isento). As regras:\n\n"
            "- **Isento até R$ 50.000 por mês**, por empresa pagadora (CNPJ) e por CPF do "
            "beneficiário — ou seja, o limite é por empresa, não pela soma de todas.\n"
            "- Acima disso, **IRRF de 10%** sobre o valor **total** distribuído naquele mês por "
            "aquela empresa (não só sobre o excedente) — retido pela própria empresa pagadora, não "
            "pela corretora.\n"
            "- **Regra de transição**: lucros que já tinham sido aprovados para distribuição até "
            "31/12/2025 podem ainda ser pagos em 2026, 2027 ou 2028 sem essa tributação nova.\n"
            "- A lei também criou um **\"IRPFM\"** (IR Pessoa Física Mínimo, alíquota progressiva de "
            "0% a 10%) que só afeta quem tem renda anual total acima de R$ 600 mil (ficando mais "
            "alto perto de R$ 1,2 milhão+) — apurado apenas na declaração anual, com o IRRF já "
            "retido servindo de crédito. Não é o caso da maioria dos investidores pessoa física.\n"
            "- **JCP (Juros sobre Capital Próprio)**: continua com **tributação exclusiva na fonte "
            "de 15%**, igual a antes — a lei nova não alterou esse ponto nas fontes consultadas.\n\n"
            "⚠️ Como é uma lei muito recente, alguns pontos ainda podem ser detalhados por "
            "regulamentação futura da Receita Federal — vale acompanhar."
        )

    with st.expander("📋 Declaração Anual — o que informar"):
        st.markdown(
            "Na declaração de Imposto de Renda de Pessoa Física do ano seguinte, a parte de ações "
            "entra em três lugares diferentes:\n\n"
            "- **Bens e Direitos**: a posição que você tinha em 31/12 do ano-base, ativo por "
            "ativo, pelo **custo de aquisição** (o que você pagou, não o valor de mercado do dia). "
            "A seção \"Posição em uma Data\" logo abaixo calcula isso automaticamente para você, "
            "para qualquer data de corte.\n"
            "- **Rendimentos Isentos e Não Tributáveis**: dividendos recebidos dentro da faixa de "
            "isenção da Lei 15.270/2025.\n"
            "- **Rendimentos Sujeitos à Tributação Exclusiva/Definitiva**: JCP recebido no ano (e, "
            "se aplicável, dividendos que excederam a faixa de isenção mensal).\n\n"
            "A seção \"Proventos do Ano\" mais abaixo já separa esses totais por tipo, ano a ano."
        )


# ==========================================================================
# Parte 2 — resumo mensal interativo (Swing x Day Trade)
# ==========================================================================

def _resumo_mensal_interativo(dados: dict, ocultar_valores: bool) -> None:
    st.subheader("📊 Resumo Mensal — Swing Trade x Day Trade (seus dados)")
    st.caption(
        "Calculado automaticamente a partir das suas compras e vendas registradas na aba "
        "Compras & Vendas, já separando Day Trade de Swing Trade e compensando prejuízo mês a mês."
    )

    resultado = ir.construir_resultados_ir(dados["compras"], dados["eventos"])
    for aviso in resultado.avisos:
        st.warning(aviso)

    resumo = ir.resumo_mensal_ir(resultado)
    if not resumo:
        st.caption("Nenhuma venda registrada ainda — assim que você registrar uma venda, o resumo aparece aqui.")
        return

    linhas = []
    for r in resumo:
        s, d = r["swing"], r["day_trade"]
        situacao_swing = "✅ Isento" if s["isento"] else ("➖ Prejuízo" if s["lucro"] < 0 else "⚠️ Tributável")
        linhas.append({
            "Mês": r["mes"],
            "Swing — Vendido": formatar_moeda_priv(s["total_vendido"], ocultar_valores),
            "Swing — Lucro/Prej.": formatar_moeda_priv(s["lucro"], ocultar_valores),
            "Swing — Situação": situacao_swing,
            "Day Trade — Lucro/Prej.": formatar_moeda_priv(d["lucro"], ocultar_valores) if d["lucro"] != 0 else "—",
            "IRRF Estimado (crédito)": formatar_moeda(s["irrf_estimado"] + d["irrf_estimado"]),
            "DARF a Pagar": formatar_moeda(r["darf_a_pagar"]) if r["darf_a_pagar"] > 0 else ("Abaixo do mínimo (R$10)" if r["abaixo_do_minimo"] else "—"),
        })
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)

    with st.expander("Ver saldo de prejuízo acumulado (compensação futura)"):
        ultimo = resumo[-1]
        c1, c2 = st.columns(2)
        c1.metric("Prejuízo acumulado — Swing Trade", formatar_moeda(ultimo["swing"]["prejuizo_acumulado_restante"]))
        c2.metric("Prejuízo acumulado — Day Trade", formatar_moeda(ultimo["day_trade"]["prejuizo_acumulado_restante"]))
        st.caption("Esse saldo (se houver) fica disponível para abater lucro futuro da mesma modalidade, sem prazo de validade.")


# ==========================================================================
# Parte 3 — Bens e Direitos (posição numa data de corte)
# ==========================================================================

def _bens_e_direitos(dados: dict, ocultar_valores: bool) -> None:
    st.subheader("🏛️ Bens e Direitos — posição numa data (para a declaração anual)")
    st.caption("A declaração anual pede a posição de 31/12 pelo custo de aquisição — mas você pode conferir qualquer data aqui.")

    hoje = date.today()
    data_corte = st.date_input(
        "Data de corte", value=date(hoje.year - 1, 12, 31), max_value=hoje,
        help="Normalmente 31 de dezembro do ano-base da declaração.",
    )
    posicoes = ir.posicoes_em_data(dados["compras"], dados["eventos"], data_corte.isoformat())
    if not posicoes:
        st.caption(f"Nenhuma posição em aberto em {formatar_data_br(data_corte.isoformat())}.")
        return

    linhas = [{
        "Ticker": p["ticker"], "Quantidade": formatar_numero(p["qtd_total"], 4),
        "Custo Total (aquisição)": formatar_moeda_priv(p["valor_total_investido"], ocultar_valores),
        "Preço Médio": formatar_moeda(p["preco_medio_ponderado"]),
    } for p in sorted(posicoes, key=lambda p: p["ticker"])]
    st.dataframe(pd.DataFrame(linhas), use_container_width=True, hide_index=True)

    total = sum(p["valor_total_investido"] for p in posicoes)
    st.metric(f"Total em {formatar_data_br(data_corte.isoformat())} (custo de aquisição)", formatar_moeda_priv(total, ocultar_valores))


# ==========================================================================
# Parte 4 — Proventos do ano (para Rendimentos Isentos / Tributação Exclusiva)
# ==========================================================================

def _proventos_do_ano(dados: dict, ocultar_valores: bool) -> None:
    st.subheader("💰 Proventos do Ano — para a Declaração")
    st.caption("Totais de dividendos, JCP e rendimentos de FII recebidos num ano, já separados por tipo.")

    proventos = dados.get("proventos") or []
    if not proventos:
        st.caption("Nenhum provento registrado ainda — registre na aba 📅 Proventos.")
        return

    anos = sorted({(p.get("data") or "")[:4] for p in proventos if p.get("data")}, reverse=True)
    if not anos:
        st.caption("Nenhum provento com data válida registrado ainda.")
        return

    ano = st.selectbox("Ano", anos)
    resumo = ir.resumo_anual_proventos(proventos, ano)

    c1, c2, c3 = st.columns(3)
    c1.metric("Dividendos (isentos até R$50k/mês por empresa)", formatar_moeda_priv(resumo["dividendos"], ocultar_valores))
    c2.metric("JCP (tributação exclusiva, 15%)", formatar_moeda_priv(resumo["jcp"], ocultar_valores))
    c3.metric("Rendimentos de FII (isentos)", formatar_moeda_priv(resumo["rendimentos_fii"], ocultar_valores))

    if resumo["jcp"] > 0:
        st.caption(f"IRRF estimado sobre o JCP recebido em {ano} (15%, já retido na fonte): {formatar_moeda(resumo['jcp_irrf_estimado'])}")

    st.caption(
        "⚠️ Se algum pagamento individual de dividendo por empresa (CNPJ) ultrapassou R$ 50.000 no "
        "mês, o excedente pode ter tido IRRF de 10% retido pela própria empresa pagadora (Lei "
        "15.270/2025) — confira o Informe de Rendimentos da corretora para o valor exato retido."
    )
