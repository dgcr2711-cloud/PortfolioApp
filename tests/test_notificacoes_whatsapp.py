"""
Testes automatizados de core/notificacoes_whatsapp.py — alerta de
preço-alvo por WhatsApp (via CallMeBot), enviado quando a cotação CAI até
(ou abaixo d)o preço configurado (mesmo critério de ui/styles.py:badge_alerta
e de core/notificacoes_email.py, que este módulo substituiu em 2026-08-31).

Nenhum teste aqui manda mensagem de verdade nem chama a internet:
`enviar_whatsapp_fn` é sempre um dublê (fake) que só registra as chamadas,
e `CAMINHO_CONFIG_WHATSAPP` é redirecionado manualmente para um arquivo
temporário (sem depender de fixtures/monkeypatch do pytest — ver o padrão
em tests/test_notificacoes_email.py) — sem tocar em
~/.portfolio_b3_secrets/ de verdade nem na rede.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

from core import notificacoes_whatsapp as notif


class EnviadorFake:
    """Dublê de enviar_whatsapp(): registra as chamadas e devolve um resultado programado."""

    def __init__(self, sucesso: bool = True):
        self.sucesso = sucesso
        self.chamadas: list[dict] = []

    def __call__(self, **kwargs):
        self.chamadas.append(kwargs)
        return self.sucesso


def _com_config_whatsapp(conteudo: dict | None, testar):
    """
    Cria um arquivo temporário de config (ou nenhum, se conteudo=None),
    redireciona notif.CAMINHO_CONFIG_WHATSAPP pra lá durante a chamada de
    `testar`, e sempre restaura o valor original — mesmo se `testar` lançar.
    """
    original = notif.CAMINHO_CONFIG_WHATSAPP
    with tempfile.TemporaryDirectory() as pasta_tmp:
        caminho = Path(pasta_tmp) / "whatsapp_alertas.json"
        if conteudo is not None:
            caminho.write_text(json.dumps(conteudo), encoding="utf-8")
        notif.CAMINHO_CONFIG_WHATSAPP = caminho
        try:
            testar()
        finally:
            notif.CAMINHO_CONFIG_WHATSAPP = original


_CONFIG_VALIDA = {"numero": "+5511999999999", "apikey": "123456"}


class _FalsoModuloStreamlit:
    """Dublê mínimo do módulo `streamlit`, só com o atributo `secrets` (um
    dict) — usado pra testar o fallback dos Secrets do Streamlit Cloud sem
    precisar instalar o streamlit de verdade."""

    def __init__(self, secrets: dict):
        self.secrets = secrets


def _com_streamlit_falso(secrets: dict | None, testar):
    """Insere um módulo `streamlit` falso em sys.modules (ou garante que
    não exista nenhum, se secrets=None) durante a chamada de `testar`, e
    sempre restaura o estado original — mesmo se `testar` lançar."""
    tinha_streamlit = "streamlit" in sys.modules
    streamlit_original = sys.modules.get("streamlit")
    if secrets is None:
        sys.modules.pop("streamlit", None)
    else:
        sys.modules["streamlit"] = _FalsoModuloStreamlit(secrets)
    try:
        testar()
    finally:
        if tinha_streamlit:
            sys.modules["streamlit"] = streamlit_original
        else:
            sys.modules.pop("streamlit", None)


_SECRETS_WHATSAPP_VALIDO = {"whatsapp_alertas": {"numero": "+5511888888888", "apikey": "999999"}}


def _com_variaveis_de_ambiente_whatsapp(valores: dict[str, str] | None, testar):
    """
    Define (ou remove) as variáveis de ambiente WHATSAPP_ALERTA_* durante a
    chamada de `testar`, e sempre restaura o estado original — mesmo se
    `testar` lançar. `valores=None` garante que nenhuma delas exista.
    """
    nomes = ["WHATSAPP_ALERTA_NUMERO", "WHATSAPP_ALERTA_APIKEY"]
    originais = {nome: os.environ.get(nome) for nome in nomes}
    for nome in nomes:
        os.environ.pop(nome, None)
    if valores:
        os.environ.update(valores)
    try:
        testar()
    finally:
        for nome, valor in originais.items():
            if valor is None:
                os.environ.pop(nome, None)
            else:
                os.environ[nome] = valor


_VARS_WHATSAPP_VALIDAS = {"WHATSAPP_ALERTA_NUMERO": "+5511777777777", "WHATSAPP_ALERTA_APIKEY": "555555"}


def test_sem_arquivo_de_configuracao_nao_notifica_nada():
    def testar():
        assert notif.notificacoes_configuradas() is False

        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}
        enviados = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 49.0}, enviar_whatsapp_fn=dublê)

        assert enviados == 0
        assert dublê.chamadas == []

    _com_config_whatsapp(None, testar)


def test_arquivo_de_configuracao_incompleto_conta_como_nao_configurado():
    def testar():
        assert notif.notificacoes_configuradas() is False

    _com_config_whatsapp({"numero": "+5511999999999"}, testar)  # falta apikey


def test_alerta_recem_atingido_envia_mensagem_e_marca_como_notificado():
    def testar():
        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}

        enviados = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 49.0}, enviar_whatsapp_fn=dublê)

        assert enviados == 1
        assert len(dublê.chamadas) == 1
        assert dublê.chamadas[0]["numero"] == "+5511999999999"
        assert "AXIA3" in dublê.chamadas[0]["mensagem"]
        assert dados["alertasEnviados"] == {"AXIA3": True}

    _com_config_whatsapp(_CONFIG_VALIDA, testar)


def test_alerta_ainda_nao_atingido_nao_envia_nada():
    def testar():
        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}

        enviados = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 53.10}, enviar_whatsapp_fn=dublê)

        assert enviados == 0
        assert dublê.chamadas == []
        assert dados["alertasEnviados"] == {}

    _com_config_whatsapp(_CONFIG_VALIDA, testar)


def test_nao_reenvia_mensagem_enquanto_alerta_continuar_atingido():
    """Reproduz o cenário real: o app roda 'Atualizar Dados' várias vezes
    seguidas com o preço ainda abaixo do alvo — só o primeiro clique deve
    mandar mensagem."""
    def testar():
        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}

        primeiro = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 49.0}, enviar_whatsapp_fn=dublê)
        segundo = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 48.5}, enviar_whatsapp_fn=dublê)
        terceiro = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 47.0}, enviar_whatsapp_fn=dublê)

        assert (primeiro, segundo, terceiro) == (1, 0, 0)
        assert len(dublê.chamadas) == 1

    _com_config_whatsapp(_CONFIG_VALIDA, testar)


def test_reseta_e_notifica_de_novo_apos_subir_e_cair_outra_vez():
    """Preço cai (notifica), sobe de volta acima do alvo (reseta), cai nele
    de novo (notifica outra vez) — cada "cruzamento" pra baixo é um alerta novo."""
    def testar():
        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}

        notif.verificar_e_notificar_alertas(dados, {"AXIA3": 49.0}, enviar_whatsapp_fn=dublê)  # atinge -> notifica
        assert dados["alertasEnviados"] == {"AXIA3": True}

        notif.verificar_e_notificar_alertas(dados, {"AXIA3": 55.0}, enviar_whatsapp_fn=dublê)  # sobe de novo -> reseta
        assert dados["alertasEnviados"] == {}

        enviados = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 48.0}, enviar_whatsapp_fn=dublê)  # cai de novo
        assert enviados == 1
        assert len(dublê.chamadas) == 2
        assert dados["alertasEnviados"] == {"AXIA3": True}

    _com_config_whatsapp(_CONFIG_VALIDA, testar)


def test_ticker_sem_cotacao_disponivel_nao_quebra_nem_notifica():
    def testar():
        dublê = EnviadorFake()
        dados = {"alertas": {"CMIG4": 9.50}, "alertasEnviados": {}}

        enviados = notif.verificar_e_notificar_alertas(dados, {}, enviar_whatsapp_fn=dublê)  # CMIG4 nem aparece

        assert enviados == 0
        assert dublê.chamadas == []

    _com_config_whatsapp(_CONFIG_VALIDA, testar)


def test_falha_no_envio_nao_marca_como_notificado_para_tentar_de_novo_depois():
    def testar():
        dublê = EnviadorFake(sucesso=False)  # simula sem internet / CallMeBot fora do ar
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}

        enviados = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 49.0}, enviar_whatsapp_fn=dublê)

        assert enviados == 0
        assert len(dublê.chamadas) == 1  # tentou
        assert dados["alertasEnviados"] == {}  # mas não marcou -> tenta de novo na próxima

    _com_config_whatsapp(_CONFIG_VALIDA, testar)


def test_varios_alertas_atingidos_ao_mesmo_tempo_notifica_todos():
    def testar():
        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0, "BBSE3": 34.0, "CPFE3": 41.0}, "alertasEnviados": {}}

        enviados = notif.verificar_e_notificar_alertas(
            dados, {"AXIA3": 49.0, "BBSE3": 40.0, "CPFE3": 40.5}, enviar_whatsapp_fn=dublê
        )

        # AXIA3 (49<=50) e CPFE3 (40.5<=41) atingiram; BBSE3 (40>34) não.
        assert enviados == 2
        assert dados["alertasEnviados"] == {"AXIA3": True, "CPFE3": True}

    _com_config_whatsapp(_CONFIG_VALIDA, testar)


def test_sem_arquivo_local_usa_configuracao_das_variaveis_de_ambiente():
    """Simula o script do GitHub Actions: sem arquivo local nem Streamlit,
    a configuração vem das variáveis de ambiente."""
    def testar():
        assert notif.notificacoes_configuradas() is True
        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}

        enviados = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 49.0}, enviar_whatsapp_fn=dublê)

        assert enviados == 1
        assert dublê.chamadas[0]["numero"] == "+5511777777777"

    _com_variaveis_de_ambiente_whatsapp(_VARS_WHATSAPP_VALIDAS, testar)


def test_sem_arquivo_local_usa_configuracao_dos_secrets_do_streamlit():
    """Simula o dashboard hospedado no Streamlit Cloud: sem o arquivo local
    nem variáveis de ambiente, a configuração vem dos Secrets do próprio app."""
    def testar():
        def com_streamlit():
            assert notif.notificacoes_configuradas() is True
            dublê = EnviadorFake()
            dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}

            enviados = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 49.0}, enviar_whatsapp_fn=dublê)

            assert enviados == 1
            assert dublê.chamadas[0]["numero"] == "+5511888888888"

        _com_streamlit_falso(_SECRETS_WHATSAPP_VALIDO, com_streamlit)

    _com_config_whatsapp(None, lambda: _com_variaveis_de_ambiente_whatsapp(None, testar))


def test_arquivo_local_tem_prioridade_sobre_variavel_de_ambiente():
    def testar():
        config = notif._carregar_config()
        assert config["numero"] == "+5511999999999"  # veio do arquivo local, não da variável de ambiente

    _com_config_whatsapp(_CONFIG_VALIDA, lambda: _com_variaveis_de_ambiente_whatsapp(_VARS_WHATSAPP_VALIDAS, testar))


def test_variavel_de_ambiente_tem_prioridade_sobre_secrets_do_streamlit():
    def testar():
        def com_streamlit():
            config = notif._carregar_config()
            assert config["numero"] == "+5511777777777"  # veio da variável de ambiente, não dos secrets

        _com_streamlit_falso(_SECRETS_WHATSAPP_VALIDO, com_streamlit)

    _com_config_whatsapp(None, lambda: _com_variaveis_de_ambiente_whatsapp(_VARS_WHATSAPP_VALIDAS, testar))


def test_secrets_do_streamlit_incompletos_conta_como_nao_configurado():
    def testar():
        def com_streamlit():
            assert notif.notificacoes_configuradas() is False

        _com_streamlit_falso({"whatsapp_alertas": {"numero": "+5511999999999"}}, com_streamlit)  # falta apikey

    _com_config_whatsapp(None, lambda: _com_variaveis_de_ambiente_whatsapp(None, testar))


def test_sem_nada_configurado_nao_notifica():
    def testar():
        def sem_streamlit():
            assert notif.notificacoes_configuradas() is False

        _com_streamlit_falso(None, sem_streamlit)

    _com_config_whatsapp(None, lambda: _com_variaveis_de_ambiente_whatsapp(None, testar))


def test_enviar_whatsapp_captura_erro_de_conexao_e_retorna_false():
    import urllib.error

    def urlopen_que_boia(*args, **kwargs):
        raise urllib.error.URLError("sem internet")

    original = notif.urllib.request.urlopen
    notif.urllib.request.urlopen = urlopen_que_boia
    try:
        resultado = notif.enviar_whatsapp(numero="+5511999999999", apikey="123", mensagem="teste")
        assert resultado is False
    finally:
        notif.urllib.request.urlopen = original


def test_enviar_whatsapp_com_resposta_http_200_sem_a_palavra_error_e_sucesso():
    class RespostaFalsa:
        status = 200

        def read(self):
            return b"Message queued. You will receive it in a few seconds."

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    original = notif.urllib.request.urlopen
    notif.urllib.request.urlopen = lambda url, timeout=15: RespostaFalsa()
    try:
        resultado = notif.enviar_whatsapp(numero="+5511999999999", apikey="123", mensagem="teste")
        assert resultado is True
    finally:
        notif.urllib.request.urlopen = original


def test_enviar_whatsapp_com_a_palavra_error_no_corpo_e_falha():
    class RespostaFalsa:
        status = 200

        def read(self):
            return b"Error: apikey invalid"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    original = notif.urllib.request.urlopen
    notif.urllib.request.urlopen = lambda url, timeout=15: RespostaFalsa()
    try:
        resultado = notif.enviar_whatsapp(numero="+5511999999999", apikey="123", mensagem="teste")
        assert resultado is False
    finally:
        notif.urllib.request.urlopen = original


def test_enviar_whatsapp_com_status_http_diferente_de_200_e_falha():
    class RespostaFalsa:
        status = 500

        def read(self):
            return b""

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    original = notif.urllib.request.urlopen
    notif.urllib.request.urlopen = lambda url, timeout=15: RespostaFalsa()
    try:
        resultado = notif.enviar_whatsapp(numero="+5511999999999", apikey="123", mensagem="teste")
        assert resultado is False
    finally:
        notif.urllib.request.urlopen = original
