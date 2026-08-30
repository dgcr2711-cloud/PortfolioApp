"""
Altman Z-Score — nota criada em 1968 pelo professor Edward Altman para
estimar o risco de uma empresa entrar em dificuldade financeira grave
(falência, recuperação judicial) nos próximos ~2 anos, combinando 5
índices financeiros num único número.

Fórmula clássica (a original, pensada para empresas de capital aberto —
ver ressalva importante abaixo):

    Z = 1.2*A + 1.4*B + 3.3*C + 0.6*D + 1.0*E

    A = Capital de Giro / Ativos Totais         (liquidez de curto prazo)
    B = Lucros Retidos / Ativos Totais           (lucratividade acumulada ao longo do tempo)
    C = EBIT / Ativos Totais                     (rentabilidade operacional)
    D = Valor de Mercado / Passivo Total          (alavancagem, medida a valor de mercado)
    E = Receita / Ativos Totais                   (giro dos ativos)

Faixas de classificação (as mesmas do modelo original de Altman):
    Z > 2.99            -> Zona Segura   (baixo risco de dificuldade financeira)
    1.81 <= Z <= 2.99    -> Zona de Alerta ("zona cinzenta" — atenção redobrada)
    Z < 1.81             -> Zona de Risco  (risco elevado)

⚠️ RESSALVA IMPORTANTE: o modelo original foi calibrado com empresas
INDUSTRIAIS americanas dos anos 1960. Bancos e outras instituições
financeiras têm uma estrutura de balanço tão diferente (a maior parte do
"passivo" de um banco é depósito de cliente, não dívida no sentido
tradicional; "capital de giro" também não tem o mesmo significado) que a
fórmula tende a dar leituras sem sentido para elas — essa ressalva é
mostrada ao usuário na tela (não é responsabilidade deste módulo, que só
calcula; ver core.fundamentals.buscar_dados_altman e a aba que exibe isso).

Este módulo é PURO: recebe os números já extraídos num dicionário e devolve
o Z-Score — não fala com o Yahoo Finance nem com nenhuma fonte externa, o
que permite testar a conta inteira com números inventados, sem depender de
internet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

LIMIAR_ZONA_SEGURA = 2.99
LIMIAR_ZONA_RISCO = 1.81


def _dividir_seguro(numerador: float | None, denominador: float | None) -> float | None:
    """Divisão que devolve None (em vez de lançar erro) quando falta algum
    dos dois números ou o denominador é zero."""
    if numerador is None or denominador is None or denominador == 0:
        return None
    return numerador / denominador


@dataclass
class ResultadoAltman:
    z_score: float | None
    classificacao: str
    # Os 5 componentes individuais (A a E) ficam disponíveis mesmo quando
    # falta algum e o z_score final não pôde ser calculado — útil para
    # mostrar ao usuário QUAL dado está faltando, em vez de só dizer
    # "não deu para calcular".
    componentes: dict[str, float | None] = field(default_factory=dict)


def calcular_altman(dados: dict[str, Any]) -> ResultadoAltman:
    """
    Calcula o Z-Score a partir de um dicionário com os números de UM ano
    fiscal (diferente do Piotroski, que compara dois anos — o Altman é uma
    "foto" de um momento só). Qualquer chave ausente ou None resulta em
    z_score=None (a fórmula soma os 5 termos com peso fixo — ao contrário
    do Piotroski, não há como dar "crédito parcial" quando falta um dos
    cinco, o resultado final ficaria incorreto).

    Chaves esperadas (todas opcionais):
        ativo_circulante, passivo_circulante, ativos_totais,
        lucros_retidos, ebit, valor_mercado, passivo_total, receita
    """
    g = dados.get
    ativos_totais = g("ativos_totais")
    ativo_circulante = g("ativo_circulante")
    passivo_circulante = g("passivo_circulante")

    capital_giro = None
    if ativo_circulante is not None and passivo_circulante is not None:
        capital_giro = ativo_circulante - passivo_circulante

    a = _dividir_seguro(capital_giro, ativos_totais)
    b = _dividir_seguro(g("lucros_retidos"), ativos_totais)
    c = _dividir_seguro(g("ebit"), ativos_totais)
    d = _dividir_seguro(g("valor_mercado"), g("passivo_total"))
    e = _dividir_seguro(g("receita"), ativos_totais)

    componentes = {
        "capital_giro_sobre_ativos": a,
        "lucros_retidos_sobre_ativos": b,
        "ebit_sobre_ativos": c,
        "valor_mercado_sobre_passivo": d,
        "receita_sobre_ativos": e,
    }

    if any(componente is None for componente in (a, b, c, d, e)):
        return ResultadoAltman(z_score=None, classificacao="Dados insuficientes", componentes=componentes)

    z = 1.2 * a + 1.4 * b + 3.3 * c + 0.6 * d + 1.0 * e

    if z > LIMIAR_ZONA_SEGURA:
        classificacao = "Zona Segura"
    elif z >= LIMIAR_ZONA_RISCO:
        classificacao = "Zona de Alerta"
    else:
        classificacao = "Zona de Risco"

    return ResultadoAltman(z_score=z, classificacao=classificacao, componentes=componentes)
