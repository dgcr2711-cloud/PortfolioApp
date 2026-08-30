"""
Testes automatizados de core/data_store.py — leitura/escrita local
(atômica, com backup diário automático) e, desde 2026-08-30, sincronização
com a nuvem (Firestore) como fonte de verdade quando configurada.

Nenhum teste aqui toca o Firestore de verdade nem a pasta real de dados do
projeto: `ARQUIVO_DADOS`/`PASTA_DADOS`/`PASTA_BACKUPS` são redirecionados
pra uma pasta temporária, e `core.cloud_sync.carregar_dados_completos_da_nuvem`/
`salvar_dados_completos_na_nuvem` são sempre substituídos por um dublê
(fake) em memória — mesmo rodando este arquivo numa máquina que já tem a
chave real do Firebase configurada (como a sua, Diego), nada daqui chega
na internet. Isso é importante: sem isso, rodar "pytest" no seu PC
começaria a ler/escrever na sua carteira DE VERDADE no Firestore a cada
execução dos testes.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core import cloud_sync, data_store


class NuvemFalsa:
    """
    Dublê de core.cloud_sync: guarda os "dados da nuvem" em memória (None =
    nuvem não configurada/inacessível/documento ainda não existe) e conta
    quantas vezes cada função foi chamada, sem nunca tocar em rede nem no
    Firestore de verdade.
    """

    def __init__(self, dados_iniciais: dict | None = None):
        self.dados = dados_iniciais
        self.chamadas_salvar = 0
        self.chamadas_carregar = 0
        self.falhar_ao_salvar = False

    def carregar(self):
        self.chamadas_carregar += 1
        return self.dados

    def salvar(self, dados: dict) -> bool:
        self.chamadas_salvar += 1
        if self.falhar_ao_salvar:
            return False
        self.dados = dados
        return True


def _com_ambiente_isolado(testar, dados_iniciais_na_nuvem: dict | None = None):
    """
    Redireciona os caminhos de arquivo do data_store pra uma pasta
    temporária e a "nuvem" pra uma NuvemFalsa, chama `testar(nuvem)`, e
    sempre restaura tudo ao original — mesmo se `testar` lançar.
    """
    arquivo_original = data_store.ARQUIVO_DADOS
    pasta_dados_original = data_store.PASTA_DADOS
    pasta_backups_original = data_store.PASTA_BACKUPS
    carregar_original = cloud_sync.carregar_dados_completos_da_nuvem
    salvar_original = cloud_sync.salvar_dados_completos_na_nuvem

    with tempfile.TemporaryDirectory() as pasta_tmp:
        pasta = Path(pasta_tmp)
        data_store.PASTA_DADOS = pasta
        data_store.ARQUIVO_DADOS = pasta / "portfolio_data.json"
        data_store.PASTA_BACKUPS = pasta / "backups"

        nuvem = NuvemFalsa(dados_iniciais_na_nuvem)
        cloud_sync.carregar_dados_completos_da_nuvem = nuvem.carregar
        cloud_sync.salvar_dados_completos_na_nuvem = nuvem.salvar

        try:
            testar(nuvem)
        finally:
            data_store.ARQUIVO_DADOS = arquivo_original
            data_store.PASTA_DADOS = pasta_dados_original
            data_store.PASTA_BACKUPS = pasta_backups_original
            cloud_sync.carregar_dados_completos_da_nuvem = carregar_original
            cloud_sync.salvar_dados_completos_na_nuvem = salvar_original


# --- Comportamento local (sem nuvem configurada) -----------------------

def test_primeira_vez_sem_nuvem_cria_estrutura_padrao_local():
    def testar(nuvem):
        dados = data_store.carregar_dados()
        assert dados["compras"] == []
        assert dados["alertas"] == {}
        assert data_store.ARQUIVO_DADOS.exists()

    _com_ambiente_isolado(testar, dados_iniciais_na_nuvem=None)


def test_salvar_e_recarregar_sem_nuvem_preserva_os_dados():
    def testar(nuvem):
        dados = data_store.estrutura_padrao()
        dados["alertas"]["AXIA3"] = 50.0
        data_store.salvar_dados(dados)

        recarregados = data_store.carregar_dados()
        assert recarregados["alertas"] == {"AXIA3": 50.0}

    _com_ambiente_isolado(testar, dados_iniciais_na_nuvem=None)


def test_arquivo_local_antigo_sem_chaves_novas_ganha_valores_padrao():
    def testar(nuvem):
        data_store.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        with open(data_store.ARQUIVO_DADOS, "w", encoding="utf-8") as f:
            json.dump({"compras": [{"ticker": "AXIA3"}]}, f)  # formato "antigo", faltando várias chaves

        dados = data_store.carregar_dados()
        assert dados["compras"] == [{"ticker": "AXIA3"}]
        assert dados["alertas"] == {}  # chave que não existia no arquivo antigo -> valor padrão
        assert dados["alertasEnviados"] == {}

    _com_ambiente_isolado(testar, dados_iniciais_na_nuvem=None)


# --- Nuvem como fonte de verdade (2026-08-30) ---------------------------

def test_com_nuvem_configurada_carregar_dados_usa_a_nuvem_em_vez_do_arquivo_local():
    def testar(nuvem):
        # Arquivo local tem uma versão ANTIGA...
        data_store.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        dados_locais_antigos = data_store.estrutura_padrao()
        dados_locais_antigos["alertas"]["AXIA3"] = 999.0
        with open(data_store.ARQUIVO_DADOS, "w", encoding="utf-8") as f:
            json.dump(dados_locais_antigos, f)

        # ...mas a nuvem tem uma versão mais NOVA (editada de outro lugar).
        nuvem.dados = {**data_store.estrutura_padrao(), "alertas": {"AXIA3": 50.0}}

        dados = data_store.carregar_dados()
        assert dados["alertas"] == {"AXIA3": 50.0}  # veio da nuvem, não do arquivo local antigo

    _com_ambiente_isolado(testar)


def test_dados_vindos_da_nuvem_sao_salvos_localmente_como_cache_offline():
    def testar(nuvem):
        nuvem.dados = {**data_store.estrutura_padrao(), "alertas": {"BBSE3": 34.0}}

        data_store.carregar_dados()

        with open(data_store.ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            conteudo_local = json.load(f)
        assert conteudo_local["alertas"] == {"BBSE3": 34.0}

    _com_ambiente_isolado(testar)


def test_sem_nuvem_configurada_carregar_dados_nao_tenta_usar_dado_nenhum_dela():
    def testar(nuvem):
        # nuvem.dados é None (não configurada/inacessível) -> precisa cair pro arquivo local
        dados = data_store.estrutura_padrao()
        dados["watchlist"] = ["ITUB4"]
        data_store.salvar_dados(dados)

        assert nuvem.chamadas_salvar == 1  # tentou mandar pra nuvem (best-effort)

        recarregados = data_store.carregar_dados()
        assert recarregados["watchlist"] == ["ITUB4"]  # veio do arquivo local, já que nuvem.dados é None

    _com_ambiente_isolado(testar, dados_iniciais_na_nuvem=None)


def test_salvar_dados_grava_local_e_manda_para_a_nuvem():
    def testar(nuvem):
        dados = data_store.estrutura_padrao()
        dados["alertas"]["CPFE3"] = 41.0

        data_store.salvar_dados(dados)

        assert nuvem.chamadas_salvar == 1
        assert nuvem.dados["alertas"] == {"CPFE3": 41.0}
        with open(data_store.ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            conteudo_local = json.load(f)
        assert conteudo_local["alertas"] == {"CPFE3": 41.0}

    _com_ambiente_isolado(testar, dados_iniciais_na_nuvem=None)


def test_falha_ao_enviar_para_nuvem_nao_impede_gravacao_local():
    """Sem internet ou chave inválida: a gravação local (a que garante o
    app continuar funcionando) precisa acontecer de qualquer jeito."""
    def testar(nuvem):
        nuvem.falhar_ao_salvar = True
        dados = data_store.estrutura_padrao()
        dados["alertas"]["SAPR4"] = 6.40

        data_store.salvar_dados(dados)  # não deve lançar exceção

        with open(data_store.ARQUIVO_DADOS, "r", encoding="utf-8") as f:
            conteudo_local = json.load(f)
        assert conteudo_local["alertas"] == {"SAPR4": 6.40}

    _com_ambiente_isolado(testar, dados_iniciais_na_nuvem=None)


def test_primeira_vez_com_nuvem_configurada_mas_documento_ainda_nao_existe():
    """nuvem.dados é None (documento ainda não existe no Firestore) e
    também não há arquivo local ainda -> cria estrutura padrão, salva local
    E tenta semear a nuvem."""
    def testar(nuvem):
        dados = data_store.carregar_dados()

        assert dados["compras"] == []
        assert data_store.ARQUIVO_DADOS.exists()
        assert nuvem.chamadas_salvar == 1  # tentou semear a nuvem também

    _com_ambiente_isolado(testar, dados_iniciais_na_nuvem=None)


# --- Proteção contra nuvem "vazia" apagando dados reais (2026-08-30) ---
# (ver docstring de data_store.carregar_dados() e _sem_dados_de_verdade())

def test_nuvem_vazia_mas_arquivo_local_tem_carteira_real_usa_o_local_e_conserta_a_nuvem():
    def testar(nuvem):
        # Arquivo local já tem uma carteira DE VERDADE (compra registrada).
        data_store.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        dados_locais_reais = data_store.estrutura_padrao()
        dados_locais_reais["compras"] = [{"ticker": "AXIA3", "tipo": "compra", "quantidade": 100, "preco": 10.0}]
        with open(data_store.ARQUIVO_DADOS, "w", encoding="utf-8") as f:
            json.dump(dados_locais_reais, f)

        # ...mas a nuvem responde com um documento vazio (ex: um dashboard
        # hospedado que rodou antes de qualquer sincronização real).
        nuvem.dados = data_store.estrutura_padrao()

        dados = data_store.carregar_dados()

        assert dados["compras"] == dados_locais_reais["compras"]  # usou o local, não a nuvem vazia
        assert nuvem.dados["compras"] == dados_locais_reais["compras"]  # e corrigiu a nuvem sozinho
        assert nuvem.chamadas_salvar == 1

    _com_ambiente_isolado(testar)


def test_nuvem_vazia_e_local_tambem_vazio_usa_a_nuvem_normalmente_sem_reenviar():
    def testar(nuvem):
        data_store.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        with open(data_store.ARQUIVO_DADOS, "w", encoding="utf-8") as f:
            json.dump(data_store.estrutura_padrao(), f)  # local também vazio

        nuvem.dados = data_store.estrutura_padrao()

        dados = data_store.carregar_dados()

        assert dados["compras"] == []
        assert nuvem.chamadas_salvar == 0  # nada de real pra proteger, comportamento normal

    _com_ambiente_isolado(testar)


def test_nuvem_vazia_sem_nenhum_arquivo_local_ainda_usa_a_nuvem_normalmente():
    def testar(nuvem):
        # Sem arquivo local nenhum (ex: primeira vez do dashboard hospedado).
        nuvem.dados = data_store.estrutura_padrao()

        dados = data_store.carregar_dados()

        assert dados["compras"] == []
        assert nuvem.chamadas_salvar == 0  # não há dado local real pra proteger

    _com_ambiente_isolado(testar)


def test_nuvem_com_carteira_real_tem_prioridade_mesmo_com_local_tambem_real():
    """A nuvem só perde a prioridade quando está genuinamente vazia — com
    dados de verdade dos dois lados, ela continua ganhando (é a mais nova)."""
    def testar(nuvem):
        data_store.PASTA_DADOS.mkdir(parents=True, exist_ok=True)
        dados_locais = data_store.estrutura_padrao()
        dados_locais["compras"] = [{"ticker": "LOCAL3", "tipo": "compra", "quantidade": 1, "preco": 1.0}]
        with open(data_store.ARQUIVO_DADOS, "w", encoding="utf-8") as f:
            json.dump(dados_locais, f)

        dados_nuvem_reais = data_store.estrutura_padrao()
        dados_nuvem_reais["compras"] = [{"ticker": "NUVEM3", "tipo": "compra", "quantidade": 2, "preco": 2.0}]
        nuvem.dados = dados_nuvem_reais

        dados = data_store.carregar_dados()

        assert dados["compras"] == dados_nuvem_reais["compras"]
        assert nuvem.chamadas_salvar == 0  # não precisou "consertar" nada

    _com_ambiente_isolado(testar)


# --- Comportamento local original (atomicidade / backup) --------------

def test_gravacao_atomica_nao_deixa_arquivo_temporario_para_tras():
    def testar(nuvem):
        dados = data_store.estrutura_padrao()
        data_store.salvar_dados(dados)

        arquivo_tmp = data_store.ARQUIVO_DADOS.with_suffix(".tmp")
        assert not arquivo_tmp.exists()
        assert data_store.ARQUIVO_DADOS.exists()

    _com_ambiente_isolado(testar, dados_iniciais_na_nuvem=None)


def test_backup_diario_e_criado_na_primeira_gravacao_do_dia():
    def testar(nuvem):
        dados = data_store.estrutura_padrao()
        data_store.salvar_dados(dados)  # primeira gravação: ainda não deveria ter backup (arquivo não existia antes)
        data_store.salvar_dados(dados)  # segunda gravação: agora sim, o arquivo "de antes" existia

        backups = list(data_store.PASTA_BACKUPS.glob("backup-diario-*.json"))
        assert len(backups) == 1

    _com_ambiente_isolado(testar, dados_iniciais_na_nuvem=None)
