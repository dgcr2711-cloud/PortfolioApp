"""
Piotroski F-Score — pontuação de 0 a 9 que mede a "saúde financeira" de uma
empresa a partir de 9 critérios binários (1 ponto cada, comparando o ano
fiscal mais recente com o anterior), separados em três grupos: rentabilidade
(4 critérios), alavancagem/liquidez/fonte de capital (3) e eficiência
operacional (2). Criado pelo professor Joseph Piotroski (2000) — a ideia
original era separar, dentro de um grupo de empresas "baratas" (baixo
P/VP), quais tinham fundamentos realmente sólidos das que eram "armadilhas
de valor" (o preço está baixo porque a empresa está mesmo piorando).

Este módulo é PURO: recebe os números brutos de dois anos fiscais já
extraídos num dicionário e devolve a pontuação — não fala com o Yahoo
Finance nem com nenhuma fonte externa (isso é trabalho de
core.fundamentals.buscar_dados_piotroski, que popula os campos que este
módulo espera). Essa separação permite testar toda a lógica de pontuação
com números inventados, sem precisar de internet nem do yfinance.

Cada critério que não pôde ser calculado (por faltar algum dos números
necessários) fica marcado como None — não conta ponto a favor nem contra,
e não entra no denominador do resultado. Isso evita dar uma nota "0/9"
enganosa quando na verdade faltou dado, não que a empresa tenha ido mal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _dividir_seguro(numerador: float | None, denominador: float | None) -> float | None:
    """Divisão que devolve None (em vez de lançar erro) quando falta algum
    dos dois números ou o denominador é zero."""
    if numerador is None or denominador is None or denominador == 0:
        return None
    return numerador / denominador


@dataclass
class CriterioPiotroski:
    chave: str
    rotulo: str
    grupo: str
    passou: bool | None  # None = não deu para calcular (dado faltando)


@dataclass
class ResultadoPiotroski:
    criterios: list[CriterioPiotroski] = field(default_factory=list)

    @property
    def pontos(self) -> int:
        """Quantos dos critérios AVALIADOS a empresa passou (não conta os None)."""
        return sum(1 for c in self.criterios if c.passou is True)

    @property
    def total_avaliado(self) -> int:
        """Quantos dos 9 critérios deram para calcular (tinham todos os dados
        necessários) — pode ser menor que 9 se faltar algum dado do yfinance."""
        return sum(1 for c in self.criterios if c.passou is not None)

    @property
    def completo(self) -> bool:
        """True só quando os 9 critérios puderam ser avaliados — usado para
        decidir se dá pra mostrar uma classificação com confiança."""
        return self.total_avaliado == len(self.criterios)

    @property
    def classificacao(self) -> str:
        """
        Classificação só é dada quando os 9 critérios puderam ser avaliados —
        com dado faltando, mostrar "Forte"/"Fraco" com base em, digamos,
        5 de 6 critérios avaliados seria proporcional e poderia enganar (uma
        pontuação escalada não é a mesma coisa que a pontuação real do
        método). Faixas clássicas do paper original de Piotroski: 8-9 =
        forte candidata a "value investing"; 0-2 = fraca (evitar); 3-7 =
        neutra.
        """
        if not self.completo:
            return f"Dados parciais ({self.total_avaliado}/{len(self.criterios)} critérios avaliados)"
        if self.pontos >= 8:
            return "Forte"
        if self.pontos <= 2:
            return "Fraca"
        return "Neutra"


def calcular_piotroski(dados: dict[str, Any]) -> ResultadoPiotroski:
    """
    Calcula o F-Score a partir de um dicionário com os números de DOIS anos
    fiscais (o mais recente = "_atual", o anterior = "_anterior"). Qualquer
    chave ausente ou None é tratada como "não deu para calcular esse
    critério" — nunca lança erro.

    Chaves esperadas (todas opcionais):
        lucro_liquido_atual, lucro_liquido_anterior
        ativos_totais_atual, ativos_totais_anterior
        fluxo_caixa_operacional_atual
        divida_longo_prazo_atual, divida_longo_prazo_anterior
        ativo_circulante_atual, passivo_circulante_atual
        ativo_circulante_anterior, passivo_circulante_anterior
        num_acoes_atual, num_acoes_anterior
        margem_bruta_atual, margem_bruta_anterior
        receita_atual, receita_anterior
    """
    g = dados.get

    lucro_atual = g("lucro_liquido_atual")
    lucro_anterior = g("lucro_liquido_anterior")
    ativos_atual = g("ativos_totais_atual")
    ativos_anterior = g("ativos_totais_anterior")
    cfo_atual = g("fluxo_caixa_operacional_atual")

    roa_atual = _dividir_seguro(lucro_atual, ativos_atual)
    roa_anterior = _dividir_seguro(lucro_anterior, ativos_anterior)

    leverage_atual = _dividir_seguro(g("divida_longo_prazo_atual"), ativos_atual)
    leverage_anterior = _dividir_seguro(g("divida_longo_prazo_anterior"), ativos_anterior)

    liquidez_atual = _dividir_seguro(g("ativo_circulante_atual"), g("passivo_circulante_atual"))
    liquidez_anterior = _dividir_seguro(g("ativo_circulante_anterior"), g("passivo_circulante_anterior"))

    num_acoes_atual = g("num_acoes_atual")
    num_acoes_anterior = g("num_acoes_anterior")

    margem_bruta_atual = g("margem_bruta_atual")
    margem_bruta_anterior = g("margem_bruta_anterior")

    giro_atual = _dividir_seguro(g("receita_atual"), ativos_atual)
    giro_anterior = _dividir_seguro(g("receita_anterior"), ativos_anterior)

    def _passou(condicao_ok: bool, *valores_necessarios: Any) -> bool | None:
        if any(v is None for v in valores_necessarios):
            return None
        return condicao_ok

    criterios = [
        CriterioPiotroski(
            "roa_positivo", "Lucro líquido positivo (ROA > 0)", "Rentabilidade",
            _passou((lucro_atual or 0) > 0, lucro_atual),
        ),
        CriterioPiotroski(
            "cfo_positivo", "Fluxo de caixa operacional positivo", "Rentabilidade",
            _passou((cfo_atual or 0) > 0, cfo_atual),
        ),
        CriterioPiotroski(
            "roa_melhorou", "ROA melhorou vs. ano anterior", "Rentabilidade",
            _passou(roa_atual is not None and roa_anterior is not None and roa_atual > roa_anterior, roa_atual, roa_anterior),
        ),
        CriterioPiotroski(
            "qualidade_do_lucro", "Caixa operacional maior que o lucro contábil (accruals)", "Rentabilidade",
            _passou(cfo_atual is not None and lucro_atual is not None and cfo_atual > lucro_atual, cfo_atual, lucro_atual),
        ),
        CriterioPiotroski(
            "alavancagem_caiu", "Endividamento de longo prazo caiu vs. ano anterior", "Alavancagem/Liquidez",
            _passou(leverage_atual is not None and leverage_anterior is not None and leverage_atual < leverage_anterior, leverage_atual, leverage_anterior),
        ),
        CriterioPiotroski(
            "liquidez_melhorou", "Liquidez corrente melhorou vs. ano anterior", "Alavancagem/Liquidez",
            _passou(liquidez_atual is not None and liquidez_anterior is not None and liquidez_atual > liquidez_anterior, liquidez_atual, liquidez_anterior),
        ),
        CriterioPiotroski(
            "sem_diluicao", "Não emitiu novas ações (sem diluição)", "Alavancagem/Liquidez",
            _passou(num_acoes_atual is not None and num_acoes_anterior is not None and num_acoes_atual <= num_acoes_anterior, num_acoes_atual, num_acoes_anterior),
        ),
        CriterioPiotroski(
            "margem_bruta_melhorou", "Margem bruta melhorou vs. ano anterior", "Eficiência Operacional",
            _passou(margem_bruta_atual is not None and margem_bruta_anterior is not None and margem_bruta_atual > margem_bruta_anterior, margem_bruta_atual, margem_bruta_anterior),
        ),
        CriterioPiotroski(
            "giro_ativos_melhorou", "Giro de ativos melhorou vs. ano anterior", "Eficiência Operacional",
            _passou(giro_atual is not None and giro_anterior is not None and giro_atual > giro_anterior, giro_atual, giro_anterior),
        ),
    ]

    return ResultadoPiotroski(criterios=criterios)
