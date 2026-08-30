"""
Leitura, escrita, exportação e importação dos dados da carteira.

Os dados ficam salvos em um arquivo JSON local (data/portfolio_data.json),
usando exatamente as mesmas chaves e o mesmo formato do backup exportado
pelo dashboard HTML original (aba Configurações -> "Exportar dados"). Isso
significa que você pode pegar qualquer backup .json que já exportou do
dashboard antigo e importar direto aqui, sem precisar converter nada.

Diferente do dashboard em HTML (que guardava tudo no localStorage do
navegador, preso a um computador/navegador específico), aqui os dados
ficam num arquivo de verdade no seu computador — mais fácil de ler, versionar
e fazer backup.
"""

from __future__ import annotations

import json
import os
import shutil
import uuid
from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from core.config import ARQUIVO_DADOS, PASTA_BACKUPS, PASTA_DADOS, WATCHLIST_PADRAO

# Backups diários automáticos (ver _fazer_backup_diario_se_necessario) mais
# antigos que isto são apagados sozinhos, para a pasta backups/ nunca crescer
# para sempre — 30 dias cobre bem qualquer "percebi tarde demais que apaguei
# algo por engano" razoável, sem acumular anos de cópias que ninguém abre.
DIAS_PARA_MANTER_BACKUP_DIARIO = 30


def novo_id() -> str:
    """Gera um id único para compras, vendas, proventos e eventos."""
    return str(uuid.uuid4())


def estrutura_padrao() -> dict[str, Any]:
    """
    Retorna uma carteira vazia, no mesmo formato usado pelo dashboard
    original. Sempre que adicionar um novo "tipo de dado" ao app (ex: uma
    nova aba), acrescente a chave correspondente aqui também, com um valor
    padrão vazio — assim arquivos antigos continuam carregando sem erro.
    """
    return {
        "compras": [],       # compras E vendas (campo "tipo" em cada item)
        "cotacoes": {},      # ticker -> {preco, nome, fonte, previousClose, atualizadoEm}
        "proventos": [],
        "historico": [],     # snapshots de patrimônio ao longo do tempo
        "alertas": {},       # ticker -> preço-alvo
        "setores": {},       # ticker -> setor
        "precosTeto": {},    # ticker -> {precoTeto, precoTetoComMargem, atualizadoEm}
        "watchlist": list(WATCHLIST_PADRAO),
        "eventos": [],       # desdobramento / grupamento / bonificação
        "fundamentos": {},   # ticker -> {pl, pvp, dividend_yield, roe, ...} (ver core/fundamentals.py)
        "teses": {},         # ticker -> lista de entradas do diário de tese (ver core/teses.py)
        "piotroski": {},     # ticker -> {pontos, totalAvaliado, classificacao, criterios, atualizadoEm} (core/piotroski.py)
        "altman": {},        # ticker -> {zScore, classificacao, atualizadoEm} (core/altman.py)
        # Taxa livre de risco anual (%) usada no cálculo do Índice de Sharpe
        # (core/risco.py) — ex: a Selic/CDI do período. É só um chute inicial
        # razoável; o usuário deve ajustar na aba Evolução conforme a taxa
        # vigente, já que o app não busca isso automaticamente.
        "taxaLivreRiscoAnualPct": 10.0,
        # Meta de alocação (%) por ticker, definida por você (core/rebalanceamento.py).
        # Um ticker que não aparece aqui simplesmente não tem meta definida
        # ainda — não é tratado como "deveria ter 0%".
        "metasAlocacao": {},
        # Controle de quais alertas de preço já geraram um e-mail (core/notificacoes_email.py)
        # — ticker -> True enquanto o alerta continuar "atingido"; é removido
        # daqui assim que a cotação volta a subir acima do preço-alvo, pra
        # poder notificar de novo numa próxima queda, sem reenviar e-mail
        # repetido a cada "Atualizar Dados" enquanto o preço não se mexe.
        "alertasEnviados": {},
        "exportadoEm": None,
    }


def _mesclar_com_padrao(dados: dict[str, Any]) -> dict[str, Any]:
    """Garante que todas as chaves esperadas existam, mesmo em arquivos antigos/parciais."""
    base = estrutura_padrao()
    base.update({k: v for k, v in dados.items() if k in base})
    return base


def carregar_dados() -> dict[str, Any]:
    """
    Carrega os dados — da nuvem (Firestore) se a sincronização estiver
    configurada e alcançável, ou do arquivo local em qualquer outro caso
    (nuvem não configurada, sem internet, ou primeira vez rodando o app).

    Por quê a nuvem primeiro (2026-08-30)? Pra "rodar de qualquer lugar" —
    se você editou algo por um dashboard hospedado ou por um script de
    segundo plano enquanto estava longe deste computador, o PC precisa
    enxergar essa versão mais nova, não uma cópia antiga parada no disco
    local. O arquivo local NUNCA deixa de existir nem de funcionar: toda
    vez que os dados vêm da nuvem, uma cópia é salva localmente também (ver
    abaixo) — o app continua 100% utilizável offline, com os dados da
    última vez em que a nuvem foi alcançada.
    """
    from core import cloud_sync  # import tardio: quem nunca configura a nuvem não precisa nem ter firebase_admin instalado

    PASTA_DADOS.mkdir(parents=True, exist_ok=True)

    dados_da_nuvem = cloud_sync.carregar_dados_completos_da_nuvem()
    if dados_da_nuvem is not None:
        dados = _mesclar_com_padrao(dados_da_nuvem)
        _salvar_localmente(dados)  # mantém uma cópia local fresca como cache/backup offline
        return dados

    if not ARQUIVO_DADOS.exists():
        dados = estrutura_padrao()
        salvar_dados(dados)  # também semeia a nuvem, se configurada
        return dados
    try:
        with open(ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            dados = json.load(f)
        return _mesclar_com_padrao(dados)
    except (json.JSONDecodeError, OSError):
        # Arquivo corrompido/ilegível: não sobrescreve — melhor avisar o
        # usuário na tela do que apagar dados por engano.
        raise RuntimeError(
            f"Não foi possível ler {ARQUIVO_DADOS}. O arquivo pode estar corrompido. "
            "Verifique se há um backup em data/backups/."
        )


def salvar_dados(dados: dict[str, Any]) -> None:
    """
    Salva os dados localmente (sempre, protegido — ver _salvar_localmente)
    e também os envia pra nuvem (Firestore), se a sincronização estiver
    configurada — best-effort: uma falha ao enviar pra nuvem (sem internet,
    chave inválida) NUNCA impede nem desfaz a gravação local, que já
    aconteceu antes e é o que garante o app continuar funcionando offline.
    """
    _salvar_localmente(dados)

    from core import cloud_sync  # import tardio: mesmo motivo de carregar_dados()

    cloud_sync.salvar_dados_completos_na_nuvem(dados)


def _salvar_localmente(dados: dict[str, Any]) -> None:
    """
    A gravação no disco local, protegida contra dois riscos:

    1. Gravação pela metade: em vez de escrever direto por cima do arquivo
       real, escreve tudo primeiro num arquivo temporário e só troca pelo
       definitivo no final (`os.replace`, que o sistema operacional garante
       ser atômico dentro da mesma pasta) — uma queda de energia ou
       travamento no meio do processo nunca deixa `portfolio_data.json`
       corrompido pela metade; na pior das hipóteses, a última gravação
       simplesmente não se completa e o arquivo anterior continua intacto.
    2. Erro do dia a dia sem uma cópia de segurança pra recorrer: antes da
       PRIMEIRA gravação de cada dia, guarda uma cópia em data/backups/ (ver
       _fazer_backup_diario_se_necessario) — cobre exclusões por engano
       (transação, evento societário, preço-teto) sem exigir nenhuma ação
       manual, e sem repetir a cópia a cada um dos vários saves que um único
       clique em "🔄 Atualizar Dados" pode disparar no mesmo dia.

    Extraída como função própria (2026-08-30) pra ser reaproveitada também
    por carregar_dados() quando os dados vêm da nuvem e precisam de uma
    cópia local fresca — sem tentar reenviar pra nuvem o que acabou de vir
    de lá (ver salvar_dados(), que é quem cuida do envio pra nuvem).
    """
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    _fazer_backup_diario_se_necessario()

    arquivo_temporario = ARQUIVO_DADOS.with_suffix(".tmp")
    try:
        with open(arquivo_temporario, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass  # best-effort: nem todo sistema de arquivos suporta fsync, mas o os.replace abaixo continua atômico mesmo assim
        os.replace(arquivo_temporario, ARQUIVO_DADOS)
    except Exception:
        # Se algo deu errado ANTES do os.replace (ex: um valor não-serializável
        # nos dados), o arquivo real nunca chega a ser tocado — mas o arquivo
        # temporário parcial não deve ficar largado no disco.
        arquivo_temporario.unlink(missing_ok=True)
        raise


def _fazer_backup_diario_se_necessario() -> None:
    """
    Guarda uma cópia de portfolio_data.json em data/backups/ na primeira
    gravação de cada dia (nome com a data, ex: backup-diario-2026-08-30.json
    — chamadas seguintes no mesmo dia veem que o arquivo de hoje já existe e
    não fazem nada). Também apaga sozinho backups diários mais antigos que
    DIAS_PARA_MANTER_BACKUP_DIARIO, pra pasta nunca crescer sem limite.

    Nunca lança exceção: é uma rede de segurança extra, não pode ser o
    motivo de uma gravação normal falhar.
    """
    if not ARQUIVO_DADOS.exists():
        return  # nada ainda pra fazer backup (primeira execução do app)

    try:
        PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
        caminho_hoje = PASTA_BACKUPS / f"backup-diario-{datetime.now().strftime('%Y-%m-%d')}.json"
        if not caminho_hoje.exists():
            shutil.copy2(ARQUIVO_DADOS, caminho_hoje)

        limite = datetime.now() - timedelta(days=DIAS_PARA_MANTER_BACKUP_DIARIO)
        for arquivo in PASTA_BACKUPS.glob("backup-diario-*.json"):
            if datetime.fromtimestamp(arquivo.stat().st_mtime) < limite:
                arquivo.unlink()
    except OSError:
        pass


def fazer_backup_automatico(dados: dict[str, Any]) -> Path:
    """
    Salva uma cópia datada em data/backups/. Chamado antes de importar um
    arquivo novo, para nunca perder os dados atuais por engano — nome
    diferente do backup diário (_fazer_backup_diario_se_necessario) para que
    os dois nunca se confundam nem se sobrescrevam.
    """
    PASTA_BACKUPS.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    caminho = PASTA_BACKUPS / f"backup-antes-de-importar-{carimbo}.json"
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return caminho


def exportar_dados_json(dados: dict[str, Any]) -> str:
    """Retorna os dados como string JSON formatada, pronta para download."""
    dados_export = deepcopy(dados)
    dados_export["exportadoEm"] = datetime.now().isoformat()
    return json.dumps(dados_export, ensure_ascii=False, indent=2)


def importar_dados_json(conteudo: str | bytes) -> dict[str, Any]:
    """
    Lê um JSON de backup (do dashboard antigo ou deste app) e devolve uma
    carteira completa e válida. Chaves desconhecidas (ex: "releases",
    "indicadores" do dashboard antigo, que este app não usa) são ignoradas
    silenciosamente.
    """
    dados_brutos = json.loads(conteudo)
    if not isinstance(dados_brutos, dict):
        raise ValueError("O arquivo não parece ser um backup válido (esperado um objeto JSON).")
    return _mesclar_com_padrao(dados_brutos)
