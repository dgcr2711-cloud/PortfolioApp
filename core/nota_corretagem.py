"""
Leitura automática de Notas de Corretagem em PDF, pra evitar digitar cada
compra/venda manualmente. Usado pela aba 🧾 Compras & Vendas
(ui/compras.py -> _importar_nota_corretagem).

Como funciona: nota de corretagem é um documento com formato definido pela
B3/CBLC — todo corretora usa os MESMOS termos ("Data pregão", "Negócios
realizados", "Valor Operação", "Emolumentos", "Taxa de liquidação/CCP" etc.),
só o LAYOUT visual (fontes, colunas, cabeçalho) muda de corretora pra
corretora. Este leitor foi construído e testado contra uma nota real da BTG
Pactual — deve funcionar bem para notas parecidas (a maioria das corretoras
segue esse mesmo padrão de texto), mas nunca é garantido 100% para todo
layout que existe por aí. Por isso a regra de ouro do projeto se aplica
aqui também: o resultado SEMPRE passa por uma tela de conferência (em
ui/compras.py) antes de entrar de verdade na carteira — nunca é salvo
direto, exatamente pra cobrir os casos em que a leitura vier errada ou
incompleta.

Uma nota costuma ter mais de uma "linha de negócio" pro MESMO ativo (ex:
uma compra de 900 ações a um preço e outras 100 a um preço um pouco
diferente, executadas em lotes). Consolidamos essas linhas num único
lançamento por (ticker, compra/venda), com o preço médio ponderado das
linhas — o resultado financeiro é idêntico a lançar cada linha separada
(o preço médio da carteira dá no mesmo), só fica mais legível no histórico.
As taxas totais da nota são rateadas proporcionalmente ao valor de cada
ativo, para o caso de uma nota ter mais de um ativo diferente.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class TransacaoLida:
    ticker: str
    tipo: str  # "compra" ou "venda"
    qtd: float
    preco: float
    taxas: float


@dataclass
class NotaCorretagemLida:
    corretora: str | None = None
    data: str | None = None  # 'YYYY-MM-DD'
    numero_nota: str | None = None
    transacoes: list[TransacaoLida] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)


def _para_float_br(texto: str) -> float:
    """Converte '34.211,00' -> 34211.0 e '34,21' -> 34.21."""
    limpo = texto.strip().replace(".", "").replace(",", ".")
    return float(limpo)


def _extrair_texto(arquivo_ou_bytes: bytes | str) -> str:
    import pdfplumber

    origem = io.BytesIO(arquivo_ou_bytes) if isinstance(arquivo_ou_bytes, bytes) else arquivo_ou_bytes
    with pdfplumber.open(origem) as pdf:
        return "\n".join(pagina.extract_text() or "" for pagina in pdf.pages)


def _extrair_data_pregao(texto: str) -> tuple[str | None, str | None]:
    """Retorna (data ISO, numero_da_nota) a partir do cabeçalho da nota."""
    m = re.search(
        r"Nr\.\s*nota\s+Folha\s+Data\s+preg[ãa]o\s*\n\s*(\S+)\s+\S+\s+(\d{2})/(\d{2})/(\d{4})",
        texto,
    )
    if not m:
        return None, None
    numero_nota, dia, mes, ano = m.groups()
    return f"{ano}-{mes}-{dia}", numero_nota


def _extrair_corretora(texto: str) -> str | None:
    """Toda corretora brasileira tem "CTVM" (Corretora de Títulos e Valores
    Mobiliários) no nome oficial — é uma marca bem mais confiável de achar
    do que tentar adivinhar a posição da linha no cabeçalho, que varia de
    layout pra layout. Só decorativo (não afeta nenhum cálculo)."""
    m = re.search(r"^(.*\bCTVM\b.*)$", texto, re.MULTILINE)
    return m.group(1).strip() if m else None


_PADRAO_LINHA_NEGOCIO = re.compile(
    r"^(?P<resto>.+?)\s+(?P<qtd>[\d.]+)\s+(?P<preco>[\d.,]+)\s+(?P<valor>[\d.,]+)\s+[DC]\s*$"
)
_PADRAO_TICKER = re.compile(r"\b([A-Z]{4}\d{1,2})\b")
_PADRAO_CV = re.compile(r"\b([CV])\b")


def _extrair_linhas_negocio(texto: str, avisos: list[str]) -> list[dict[str, Any]]:
    """Lê a tabela "Negócios realizados" (entre esse título e "Resumo dos
    Negócios") e devolve uma linha bruta por negócio (ainda não consolidada
    por ticker)."""
    bloco = re.search(r"Neg[óo]cios realizados\s*\n(.*?)\nResumo dos Neg[óo]cios", texto, re.DOTALL)
    if not bloco:
        avisos.append('Não encontrei a tabela "Negócios realizados" nesta nota — o layout pode ser diferente do esperado.')
        return []

    linhas_lidas = []
    for linha in bloco.group(1).splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("Q Negociação"):
            continue
        m = _PADRAO_LINHA_NEGOCIO.match(linha)
        if not m:
            avisos.append(f'Não consegui interpretar esta linha da nota: "{linha}"')
            continue

        resto = m.group("resto")
        cv = _PADRAO_CV.search(resto)
        ticker = _PADRAO_TICKER.search(resto)
        if not ticker:
            avisos.append(f'Não encontrei o ticker nesta linha: "{linha}"')
            continue

        linhas_lidas.append({
            "ticker": ticker.group(1),
            "tipo": "compra" if (cv and cv.group(1) == "C") else "venda",
            "qtd": _para_float_br(m.group("qtd")),
            "preco": _para_float_br(m.group("preco")),
            "valor": _para_float_br(m.group("valor")),
        })
    return linhas_lidas


def _taxa(texto: str, padrao_nome: str) -> float:
    """Procura uma linha de taxa pelo nome (ex: "Emolumentos  1,71  D") e
    devolve o valor, ou 0.0 se a linha não existir nesta nota (nem toda nota
    tem toda taxa — ex: "Taxa de termo/opções" só existe se houve operação a
    termo)."""
    m = re.search(padrao_nome + r"\s+([\d.,]+)\s*[DC]?", texto)
    return _para_float_br(m.group(1)) if m else 0.0


def _extrair_total_taxas(texto: str) -> float:
    """Soma todas as taxas da nota (liquidação, registro, emolumentos, termo,
    A.N.A., transferência de ativos e o bloco "corretagem/despesas" — que já
    inclui corretagem propriamente dita, ISS e IRRF). Somar os componentes
    (em vez de usar só "Líquido para" menos "Valor das operações") funciona
    corretamente mesmo numa nota que mistura compra E venda no mesmo dia."""
    return (
        _taxa(texto, r"Taxa de liquida[çc][ãa]o/?CCP")
        + _taxa(texto, r"Taxa de registro")
        + _taxa(texto, r"Emolumentos")
        + _taxa(texto, r"Taxa de termo/op[çc][õo]es")
        + _taxa(texto, r"Taxa A\.N\.A\.")
        + _taxa(texto, r"Taxa de Transfer[êe]ncia de Ativos")
        + _taxa(texto, r"Total corretagem\s*/\s*Despesas")
    )


def extrair_nota_corretagem(arquivo_ou_bytes: bytes | str) -> NotaCorretagemLida:
    """Lê um PDF de nota de corretagem e devolve os dados encontrados,
    prontos para o usuário conferir antes de salvar (ver ui/compras.py).
    Aceita os bytes do arquivo (ex: `arquivo.getvalue()` de um
    st.file_uploader) ou um caminho de arquivo no disco.
    Nunca lança exceção por conta própria de formato inesperado — em vez
    disso, preenche `avisos` explicando o que não deu pra ler; quem chama
    decide se ainda vale a pena mostrar uma tela de conferência parcial."""
    resultado = NotaCorretagemLida()
    try:
        texto = _extrair_texto(arquivo_ou_bytes)
    except Exception as e:
        resultado.avisos.append(f"Não consegui abrir este PDF: {e}")
        return resultado

    resultado.corretora = _extrair_corretora(texto)
    resultado.data, resultado.numero_nota = _extrair_data_pregao(texto)
    if not resultado.data:
        resultado.avisos.append('Não encontrei a "Data pregão" — confira a data manualmente antes de salvar.')

    linhas_brutas = _extrair_linhas_negocio(texto, resultado.avisos)
    if not linhas_brutas:
        resultado.avisos.append("Nenhuma transação foi reconhecida nesta nota.")
        return resultado

    total_taxas = _extrair_total_taxas(texto)
    valor_total_nota = sum(l["valor"] for l in linhas_brutas)

    # Consolida linhas do mesmo ticker+tipo (uma nota pode ter o mesmo ativo
    # negociado em lotes/preços diferentes) e rateia as taxas totais
    # proporcionalmente ao valor de cada grupo.
    grupos: dict[tuple[str, str], dict[str, float]] = {}
    for l in linhas_brutas:
        chave = (l["ticker"], l["tipo"])
        grupo = grupos.setdefault(chave, {"qtd": 0.0, "valor": 0.0})
        grupo["qtd"] += l["qtd"]
        grupo["valor"] += l["valor"]

    for (ticker, tipo), grupo in grupos.items():
        proporcao = (grupo["valor"] / valor_total_nota) if valor_total_nota > 0 else (1 / len(grupos))
        resultado.transacoes.append(TransacaoLida(
            ticker=ticker,
            tipo=tipo,
            qtd=grupo["qtd"],
            preco=round(grupo["valor"] / grupo["qtd"], 4) if grupo["qtd"] else 0.0,
            taxas=round(total_taxas * proporcao, 2),
        ))

    return resultado
