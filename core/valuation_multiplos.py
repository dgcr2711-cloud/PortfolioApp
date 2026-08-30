"""
"Football field" de valuation — reúne várias estimativas independentes de
"preço justo" de uma ação num só lugar, para comparar a FAIXA entre elas em
vez de confiar cegamente num único método. O nome vem do gráfico clássico
de finanças corporativas (faixas horizontais empilhadas, parecidas com as
linhas de um campo de futebol americano).

Métodos combinados aqui:
  - Fluxo de Caixa Descontado (FCD) — já existia na aba 🎯 Preço Teto
    (core.calculations.calcular_fcd); este módulo só recebe o resultado
    PRONTO como parâmetro, não recalcula nada do FCD.
  - Número de Graham — fórmula clássica de Benjamin Graham:
        Preço Justo = raiz(22.5 x LPA x VPA)
    (22.5 vem de 15 x 1.5 — o P/L máximo e o P/VP máximo que Graham
    considerava aceitáveis para uma ação "defensiva"). Só faz sentido com
    LPA (Lucro por Ação) e VPA (Valor Patrimonial por Ação) POSITIVOS —
    uma empresa com prejuízo não tem "preço justo de Graham" (a fórmula
    original nem se aplicava a esse caso).
  - Valor Patrimonial por Ação (VPA) — o "piso" mais conservador: quanto
    sobraria por ação se a empresa fosse liquidada pelo valor CONTÁBIL
    (não de mercado) dos seus ativos.
  - Múltiplo de P/L-alvo — LPA de hoje vezes um P/L que o USUÁRIO considera
    razoável pra empresa/setor. Não existe um "P/L correto" universal —
    por isso esse número é um parâmetro informado por quem está usando o
    app (igual ao WACC no FCD), não algo calculado ou buscado sozinho.

Módulo PURO: recebe os números já prontos (LPA, VPA, resultado do FCD já
calculado etc.) e só combina/organiza — não fala com o Yahoo Finance nem
com nenhuma fonte externa.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetodoValuation:
    nome: str
    preco_justo: float


@dataclass
class ResultadoFootballField:
    metodos: list[MetodoValuation] = field(default_factory=list)

    @property
    def minimo(self) -> float | None:
        return min((m.preco_justo for m in self.metodos), default=None)

    @property
    def maximo(self) -> float | None:
        return max((m.preco_justo for m in self.metodos), default=None)

    @property
    def media(self) -> float | None:
        if not self.metodos:
            return None
        return sum(m.preco_justo for m in self.metodos) / len(self.metodos)


def calcular_numero_graham(lpa: float | None, vpa: float | None) -> float | None:
    """raiz(22.5 x LPA x VPA) — None se LPA ou VPA vierem ausentes, zero ou
    negativos (a fórmula original de Graham não se aplica a empresa com
    prejuízo ou patrimônio líquido negativo)."""
    if lpa is None or vpa is None or lpa <= 0 or vpa <= 0:
        return None
    return (22.5 * lpa * vpa) ** 0.5


def calcular_valor_por_multiplo_pl(lpa: float | None, pl_alvo: float | None) -> float | None:
    """LPA x um P/L que o usuário considera razoável para a empresa/setor.
    None se LPA vier ausente/negativo (múltiplo de P/L não faz sentido
    sobre prejuízo) ou o P/L-alvo vier ausente/não-positivo."""
    if lpa is None or lpa <= 0 or pl_alvo is None or pl_alvo <= 0:
        return None
    return lpa * pl_alvo


def montar_football_field(
    lpa: float | None,
    vpa: float | None,
    pl_alvo: float | None = None,
    preco_teto_dcf: float | None = None,
) -> ResultadoFootballField:
    """
    Junta os métodos que DERAM para calcular (cada um é independente —
    faltar um não impede os outros) num resultado único, pronto para
    exibir como uma faixa (mínimo-máximo) na tela.

    Parâmetros:
        lpa: Lucro por Ação (ex: "trailingEps" do yfinance).
        vpa: Valor Patrimonial por Ação (ex: "bookValue" do yfinance).
        pl_alvo: P/L que o usuário considera razoável (opcional — sem ele,
            o método "Múltiplo de P/L" simplesmente não entra na conta).
        preco_teto_dcf: preço-teto já calculado por core.calculations.calcular_fcd
            (opcional — sem ele, o método "FCD" não entra na conta).
    """
    metodos: list[MetodoValuation] = []

    if preco_teto_dcf is not None and preco_teto_dcf > 0:
        metodos.append(MetodoValuation("Fluxo de Caixa Descontado", preco_teto_dcf))

    graham = calcular_numero_graham(lpa, vpa)
    if graham is not None:
        metodos.append(MetodoValuation("Número de Graham", graham))

    if vpa is not None and vpa > 0:
        metodos.append(MetodoValuation("Valor Patrimonial por Ação", vpa))

    multiplo = calcular_valor_por_multiplo_pl(lpa, pl_alvo)
    if multiplo is not None:
        metodos.append(MetodoValuation(f"Múltiplo de P/L ({pl_alvo:g}x)", multiplo))

    return ResultadoFootballField(metodos=metodos)
