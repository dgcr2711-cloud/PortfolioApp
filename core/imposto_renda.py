"""
Motor de cálculo da aba "🏛️ Imposto de Renda" — uma versão mais completa do
que o resumo simplificado que já existia em calculations.resumo_ir_mensal()
(esse continua existindo e sendo usado na aba Compras & Vendas, só que como
uma ESTIMATIVA rápida; esta aba nova é o "estudo" mais refinado).

O que este módulo faz de diferente/a mais:

1. Separa Day Trade de operação comum (Swing Trade) automaticamente —
   comparando, ticker a ticker e dia a dia, o quanto foi comprado e vendido
   NO MESMO DIA. A parte "day trade" (o menor entre comprado e vendido no
   dia) é tributada à parte, à alíquota de 20%, sem direito a isenção;
   o restante (se sobrar compra ou venda) segue o fluxo normal de preço
   médio ponderado (Swing Trade), com isenção mensal e alíquota conforme a
   regra vigente na data de cada mês (ver core.config.TABELA_IR_ACOES —
   hoje, isenção de R$20 mil/mês e alíquota de 15%).

2. Compensa prejuízos de meses anteriores automaticamente — a Receita
   Federal permite abater prejuízo de operações da MESMA modalidade
   (Swing Trade só compensa com Swing Trade; Day Trade só compensa com Day
   Trade) em qualquer mês futuro, sem prazo de prescrição. O resumo antigo
   não fazia isso; este faz, mês a mês, mantendo o saldo de prejuízo a
   compensar.

3. Estima o IRRF ("dedo-duro") retido automaticamente pela corretora em
   cada operação, e já desconta esse valor do DARF a pagar do mês — é
   assim que funciona na prática: o IRRF é uma ANTECIPAÇÃO do imposto, não
   um imposto extra.

4. Aplica a regra do valor mínimo de R$10: se o DARF do mês (depois de
   compensar prejuízo e descontar o IRRF) ficar abaixo de R$10, a Receita
   permite não pagar naquele mês — o valor é somado ao próximo mês em que
   ultrapassar o mínimo.

Tudo aqui é, na melhor forma possível, uma ESTIMATIVA para ajudar a se
organizar — não substitui a conferência final com um contador, especialmente
porque o valor exato de IRRF retido deve ser conferido no "Informe de
Rendimentos" que sua corretora emite todo ano (é a fonte oficial).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core import calculations as calc
from core.config import regra_ir_vigente_em

ALIQUOTA_IR_DAY_TRADE = 0.20            # 20% sobre o lucro de day trade, sem isenção
ALIQUOTA_IRRF_SWING = 0.00005           # 0,005% sobre o valor da VENDA (operação comum)
ALIQUOTA_IRRF_DAY_TRADE = 0.01          # 1% sobre o LUCRO positivo apurado no dia (day trade)
VALOR_MINIMO_DARF = 10.0                # Abaixo disso, soma pro próximo mês (regra da Receita)


@dataclass
class ResultadoIR:
    swing: list[dict[str, Any]] = field(default_factory=list)
    day_trade: list[dict[str, Any]] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def _extrair_day_trade_e_ajustar(compras: list[dict]) -> tuple[list[dict[str, Any]], list[dict]]:
    """
    Agrupa as transações por (ticker, data) e separa a parcela de Day Trade
    (o menor entre a quantidade comprada e vendida naquele dia, pro mesmo
    ticker) do restante, que segue para o ledger normal de preço médio
    (Swing Trade). Devolve (resultados_day_trade, transações_ajustadas).
    """
    grupos: dict[tuple[Any, Any], dict[str, list[dict]]] = {}
    for c in compras:
        chave = (c.get("ticker"), c.get("data"))
        tipo = c.get("tipo", "compra")
        grupos.setdefault(chave, {"compra": [], "venda": []})[tipo].append(c)

    resultados_day_trade: list[dict[str, Any]] = []
    transacoes_ajustadas: list[dict] = []

    for (ticker, data_str), grupo in grupos.items():
        compras_dia = grupo["compra"]
        vendas_dia = grupo["venda"]

        if not compras_dia or not vendas_dia:
            transacoes_ajustadas.extend(compras_dia)
            transacoes_ajustadas.extend(vendas_dia)
            continue

        qtd_compras = sum(float(c["qtd"]) for c in compras_dia)
        qtd_vendas = sum(float(c["qtd"]) for c in vendas_dia)
        qtd_day_trade = min(qtd_compras, qtd_vendas)

        if qtd_day_trade <= 1e-9:
            transacoes_ajustadas.extend(compras_dia)
            transacoes_ajustadas.extend(vendas_dia)
            continue

        valor_total_compra = sum(float(c["qtd"]) * float(c["preco"]) + float(c.get("taxas") or 0) for c in compras_dia)
        valor_total_venda = sum(float(c["qtd"]) * float(c["preco"]) - float(c.get("taxas") or 0) for c in vendas_dia)
        preco_medio_compra = valor_total_compra / qtd_compras
        preco_medio_venda = valor_total_venda / qtd_vendas

        resultados_day_trade.append({
            "ticker": ticker,
            "data": data_str,
            "qtd": qtd_day_trade,
            "lucro": qtd_day_trade * (preco_medio_venda - preco_medio_compra),
        })

        # O que sobrar de compra ou venda naquele dia (nem tudo que foi
        # comprado precisa ter sido vendido no mesmo dia, e vice-versa)
        # segue pro ledger normal, mantendo o preço médio original de cada
        # linha e só reduzindo a quantidade/taxas na mesma proporção.
        qtd_restante_compra = qtd_compras - qtd_day_trade
        if qtd_restante_compra > 1e-9:
            fator = qtd_restante_compra / qtd_compras
            for c in compras_dia:
                transacoes_ajustadas.append({**c, "qtd": float(c["qtd"]) * fator, "taxas": float(c.get("taxas") or 0) * fator})

        qtd_restante_venda = qtd_vendas - qtd_day_trade
        if qtd_restante_venda > 1e-9:
            fator = qtd_restante_venda / qtd_vendas
            for c in vendas_dia:
                transacoes_ajustadas.append({**c, "qtd": float(c["qtd"]) * fator, "taxas": float(c.get("taxas") or 0) * fator})

    return resultados_day_trade, transacoes_ajustadas


def construir_resultados_ir(compras: list[dict], eventos: list[dict]) -> ResultadoIR:
    """Ponto de entrada: devolve os resultados realizados já separados entre
    Swing Trade e Day Trade, prontos para resumo_mensal_ir()."""
    resultados_day_trade, transacoes_swing = _extrair_day_trade_e_ajustar(compras)
    ledger = calc.construir_ledger(transacoes_swing, eventos)
    return ResultadoIR(swing=ledger.resultados_realizados, day_trade=resultados_day_trade, avisos=ledger.avisos)


def _agrupar_por_mes(resultados: list[dict[str, Any]], com_total_vendido: bool) -> dict[str, dict[str, float]]:
    por_mes: dict[str, dict[str, float]] = {}
    for r in resultados:
        mes = (r.get("data") or "")[:7]
        if not mes:
            continue
        m = por_mes.setdefault(mes, {"total_vendido": 0.0, "lucro": 0.0})
        if com_total_vendido:
            m["total_vendido"] += r["qtd"] * r["preco_venda"]
        m["lucro"] += r["lucro"]
    return por_mes


def resumo_mensal_ir(resultado: ResultadoIR) -> list[dict[str, Any]]:
    """
    Um resumo por mês (mais antigo primeiro, pra compensação de prejuízo
    fazer sentido cronologicamente), com Swing Trade e Day Trade apurados
    separadamente — cada um com seu próprio saldo de prejuízo a compensar
    — e um DARF combinado por mês (mesmo código 6015 cobre as duas
    modalidades), já aplicando a regra do valor mínimo de R$10.
    """
    swing_por_mes = _agrupar_por_mes(resultado.swing, com_total_vendido=True)
    dt_por_mes = _agrupar_por_mes(resultado.day_trade, com_total_vendido=False)
    todos_meses = sorted(set(swing_por_mes) | set(dt_por_mes))

    prejuizo_swing = 0.0
    prejuizo_dt = 0.0
    pendente_abaixo_minimo = 0.0
    linhas = []

    for mes in todos_meses:
        dados_swing = swing_por_mes.get(mes, {"total_vendido": 0.0, "lucro": 0.0})
        dados_dt = dt_por_mes.get(mes, {"lucro": 0.0})

        total_vendido_swing = dados_swing["total_vendido"]
        lucro_swing = dados_swing["lucro"]
        lucro_dt = dados_dt["lucro"]
        # Alíquota e limite de isenção do Swing Trade são os que valiam NO
        # MÊS da operação (core.config.TABELA_IR_ACOES) — assim, uma venda
        # de anos atrás continua sendo calculada com a regra da época, mesmo
        # que a Receita mude esses valores no futuro. O Day Trade é sempre
        # 20%, sem isenção, e isso nunca mudou historicamente — por isso
        # continua como constante (ALIQUOTA_IR_DAY_TRADE).
        regra_swing = regra_ir_vigente_em(mes)
        isento_swing = total_vendido_swing <= regra_swing["limite_isencao_mensal"]

        # --- Swing Trade ---
        if lucro_swing < 0:
            prejuizo_swing += -lucro_swing
            imposto_swing = 0.0
            prejuizo_usado_swing = 0.0
        elif isento_swing:
            imposto_swing = 0.0
            prejuizo_usado_swing = 0.0
        else:
            prejuizo_usado_swing = min(lucro_swing, prejuizo_swing)
            prejuizo_swing -= prejuizo_usado_swing
            imposto_swing = (lucro_swing - prejuizo_usado_swing) * regra_swing["aliquota"]

        # --- Day Trade (nunca isento) ---
        if lucro_dt < 0:
            prejuizo_dt += -lucro_dt
            imposto_dt = 0.0
            prejuizo_usado_dt = 0.0
        else:
            prejuizo_usado_dt = min(lucro_dt, prejuizo_dt)
            prejuizo_dt -= prejuizo_usado_dt
            imposto_dt = (lucro_dt - prejuizo_usado_dt) * ALIQUOTA_IR_DAY_TRADE

        # --- IRRF estimado (antecipação, descontada do DARF do mês) ---
        irrf_swing = total_vendido_swing * ALIQUOTA_IRRF_SWING
        irrf_dt = max(0.0, lucro_dt) * ALIQUOTA_IRRF_DAY_TRADE

        imposto_devido_mes = max(0.0, (imposto_swing + imposto_dt) - (irrf_swing + irrf_dt))

        # --- Regra do valor mínimo de R$10 (soma pro próximo mês) ---
        total_com_pendente = imposto_devido_mes + pendente_abaixo_minimo
        if total_com_pendente < VALOR_MINIMO_DARF:
            darf_a_pagar = 0.0
            pendente_abaixo_minimo = total_com_pendente
        else:
            darf_a_pagar = total_com_pendente
            pendente_abaixo_minimo = 0.0

        linhas.append({
            "mes": mes,
            "swing": {
                "total_vendido": total_vendido_swing, "lucro": lucro_swing, "isento": isento_swing,
                "prejuizo_compensado": prejuizo_usado_swing, "prejuizo_acumulado_restante": prejuizo_swing,
                "imposto": imposto_swing, "irrf_estimado": irrf_swing,
            },
            "day_trade": {
                "lucro": lucro_dt,
                "prejuizo_compensado": prejuizo_usado_dt, "prejuizo_acumulado_restante": prejuizo_dt,
                "imposto": imposto_dt, "irrf_estimado": irrf_dt,
            },
            "imposto_devido_mes": imposto_devido_mes,
            "darf_a_pagar": darf_a_pagar,
            "abaixo_do_minimo": darf_a_pagar == 0.0 and imposto_devido_mes > 0,
        })

    return linhas


def posicoes_em_data(compras: list[dict], eventos: list[dict], data_corte_iso: str) -> list[dict[str, Any]]:
    """Posição consolidada (ticker, quantidade, custo total investido) como
    estava EXATAMENTE até uma data de corte (ex: 31/12 de um ano) — usado
    pela ficha "Bens e Direitos" da declaração anual, que pede a posição no
    fim do ano-calendário, pelo CUSTO DE AQUISIÇÃO (não pelo valor de
    mercado)."""
    compras_ate_data = [c for c in compras if (c.get("data") or "") <= data_corte_iso]
    eventos_ate_data = [e for e in eventos if (e.get("data") or "") <= data_corte_iso]
    return calc.consolidar_posicoes(compras_ate_data, eventos_ate_data)


def resumo_anual_proventos(proventos: list[dict], ano: str) -> dict[str, float]:
    """Total de Dividendos (isentos) e JCP (tributação exclusiva na fonte,
    15%) recebidos num ano — os dois valores vão em fichas diferentes da
    declaração anual (ver aba, seção "Declaração Anual")."""
    total_dividendos = 0.0
    total_jcp = 0.0
    total_rendimentos = 0.0
    for p in proventos:
        if (p.get("data") or "")[:4] != ano:
            continue
        valor = float(p.get("valor") or 0)
        tipo = p.get("tipo")
        if tipo == "JCP":
            total_jcp += valor
        elif tipo == "Rendimento":
            total_rendimentos += valor
        else:
            total_dividendos += valor
    return {
        "dividendos": total_dividendos,
        "jcp": total_jcp,
        "rendimentos_fii": total_rendimentos,
        "jcp_irrf_estimado": total_jcp * 0.15,
    }
