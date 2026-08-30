"""
Testes automatizados de core/notificacoes_email.py — e-mail de alerta de
preço-alvo, enviado quando a cotação CAI até (ou abaixo d)o preço
configurado (mesmo critério de ui/styles.py:badge_alerta).

Nenhum teste aqui manda e-mail de verdade: `enviar_email_fn` é sempre um
dublê (fake) que só registra as chamadas, e `CAMINHO_CONFIG_EMAIL` é
redirecionado manualmente para um arquivo temporário (sem depender de
fixtures/monkeypatch do pytest, pra rodar igual tanto aqui quanto com o
pytest de verdade no PC — ver o padrão em tests/test_calculations.py) —
sem tocar em ~/.portfolio_b3_secrets/ de verdade nem na rede.

Rode com `pytest -v` (ver instruções em tests/test_calculations.py).
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from core import notificacoes_email as notif


class EnviadorFake:
    """Dublê de enviar_email(): registra as chamadas e devolve um resultado programado."""

    def __init__(self, sucesso: bool = True):
        self.sucesso = sucesso
        self.chamadas: list[dict] = []

    def __call__(self, **kwargs):
        self.chamadas.append(kwargs)
        return self.sucesso


def _com_config_email(conteudo: dict | None, testar):
    """
    Cria um arquivo temporário de config (ou nenhum, se conteudo=None),
    redireciona notif.CAMINHO_CONFIG_EMAIL pra lá durante a chamada de
    `testar`, e sempre restaura o valor original — mesmo se `testar` lançar.
    """
    original = notif.CAMINHO_CONFIG_EMAIL
    with tempfile.TemporaryDirectory() as pasta_tmp:
        caminho = Path(pasta_tmp) / "email_alertas.json"
        if conteudo is not None:
            caminho.write_text(json.dumps(conteudo), encoding="utf-8")
        notif.CAMINHO_CONFIG_EMAIL = caminho
        try:
            testar()
        finally:
            notif.CAMINHO_CONFIG_EMAIL = original


_CONFIG_VALIDA = {"remetente": "voce@gmail.com", "senha_app": "abcd efgh ijkl mnop", "destinatario": "voce@gmail.com"}


def test_sem_arquivo_de_configuracao_nao_notifica_nada():
    def testar():
        assert notif.notificacoes_configuradas() is False

        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}
        enviados = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 49.0}, enviar_email_fn=dublê)

        assert enviados == 0
        assert dublê.chamadas == []

    _com_config_email(None, testar)


def test_arquivo_de_configuracao_incompleto_conta_como_nao_configurado():
    def testar():
        assert notif.notificacoes_configuradas() is False

    _com_config_email({"remetente": "voce@gmail.com"}, testar)  # falta senha_app e destinatario


def test_alerta_recem_atingido_envia_email_e_marca_como_notificado():
    def testar():
        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}

        enviados = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 49.0}, enviar_email_fn=dublê)

        assert enviados == 1
        assert len(dublê.chamadas) == 1
        assert dublê.chamadas[0]["destinatario"] == "voce@gmail.com"
        assert "AXIA3" in dublê.chamadas[0]["assunto"]
        assert dados["alertasEnviados"] == {"AXIA3": True}

    _com_config_email(_CONFIG_VALIDA, testar)


def test_alerta_ainda_nao_atingido_nao_envia_nada():
    def testar():
        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}

        enviados = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 53.10}, enviar_email_fn=dublê)

        assert enviados == 0
        assert dublê.chamadas == []
        assert dados["alertasEnviados"] == {}

    _com_config_email(_CONFIG_VALIDA, testar)


def test_nao_reenvia_email_enquanto_alerta_continuar_atingido():
    """Reproduz o cenário real: o app roda 'Atualizar Dados' várias vezes
    seguidas com o preço ainda abaixo do alvo — só o primeiro clique deve
    mandar e-mail."""
    def testar():
        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}

        primeiro = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 49.0}, enviar_email_fn=dublê)
        segundo = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 48.5}, enviar_email_fn=dublê)
        terceiro = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 47.0}, enviar_email_fn=dublê)

        assert (primeiro, segundo, terceiro) == (1, 0, 0)
        assert len(dublê.chamadas) == 1

    _com_config_email(_CONFIG_VALIDA, testar)


def test_reseta_e_notifica_de_novo_apos_subir_e_cair_outra_vez():
    """Preço cai (notifica), sobe de volta acima do alvo (reseta), cai nele
    de novo (notifica outra vez) — cada "cruzamento" pra baixo é um alerta novo."""
    def testar():
        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}

        notif.verificar_e_notificar_alertas(dados, {"AXIA3": 49.0}, enviar_email_fn=dublê)  # atinge -> notifica
        assert dados["alertasEnviados"] == {"AXIA3": True}

        notif.verificar_e_notificar_alertas(dados, {"AXIA3": 55.0}, enviar_email_fn=dublê)  # sobe de novo -> reseta
        assert dados["alertasEnviados"] == {}

        enviados = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 48.0}, enviar_email_fn=dublê)  # cai de novo
        assert enviados == 1
        assert len(dublê.chamadas) == 2
        assert dados["alertasEnviados"] == {"AXIA3": True}

    _com_config_email(_CONFIG_VALIDA, testar)


def test_ticker_sem_cotacao_disponivel_nao_quebra_nem_notifica():
    def testar():
        dublê = EnviadorFake()
        dados = {"alertas": {"CMIG4": 9.50}, "alertasEnviados": {}}

        enviados = notif.verificar_e_notificar_alertas(dados, {}, enviar_email_fn=dublê)  # CMIG4 nem aparece

        assert enviados == 0
        assert dublê.chamadas == []

    _com_config_email(_CONFIG_VALIDA, testar)


def test_falha_no_envio_nao_marca_como_notificado_para_tentar_de_novo_depois():
    def testar():
        dublê = EnviadorFake(sucesso=False)  # simula sem internet / senha errada
        dados = {"alertas": {"AXIA3": 50.0}, "alertasEnviados": {}}

        enviados = notif.verificar_e_notificar_alertas(dados, {"AXIA3": 49.0}, enviar_email_fn=dublê)

        assert enviados == 0
        assert len(dublê.chamadas) == 1  # tentou
        assert dados["alertasEnviados"] == {}  # mas não marcou -> tenta de novo na próxima

    _com_config_email(_CONFIG_VALIDA, testar)


def test_varios_alertas_atingidos_ao_mesmo_tempo_notifica_todos():
    def testar():
        dublê = EnviadorFake()
        dados = {"alertas": {"AXIA3": 50.0, "BBSE3": 34.0, "CPFE3": 41.0}, "alertasEnviados": {}}

        enviados = notif.verificar_e_notificar_alertas(
            dados, {"AXIA3": 49.0, "BBSE3": 40.0, "CPFE3": 40.5}, enviar_email_fn=dublê
        )

        # AXIA3 (49<=50) e CPFE3 (40.5<=41) atingiram; BBSE3 (40>34) não.
        assert enviados == 2
        assert dados["alertasEnviados"] == {"AXIA3": True, "CPFE3": True}

    _com_config_email(_CONFIG_VALIDA, testar)


def test_enviar_email_captura_excecao_de_conexao_e_retorna_false():
    class SMTPQueBoia:
        def __init__(self, *args, **kwargs):
            raise OSError("sem internet")

    original_smtp_ssl = notif.smtplib.SMTP_SSL
    notif.smtplib.SMTP_SSL = SMTPQueBoia
    try:
        resultado = notif.enviar_email(
            destinatario="voce@gmail.com", remetente="voce@gmail.com", senha_app="xxxx",
            assunto="teste", corpo="teste",
        )
        assert resultado is False
    finally:
        notif.smtplib.SMTP_SSL = original_smtp_ssl
