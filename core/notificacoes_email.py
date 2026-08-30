"""
Envia um e-mail quando a cotação de um ativo CAI até (ou abaixo d)o preço
que você configurou em "⚙️ Configurações → Alertas de Preço-Alvo" — mesmo
critério do selo 🔔/🔕 já usado em ui/styles.py:badge_alerta (ver o comentário
lá para o motivo da direção da comparação).

Por quê e-mail, e não notificação nativa do celular? Notificação push de
verdade em iPhone exige o mesmo custo do login do Google (Programa de
Desenvolvedor Apple, US$99/ano — ver README_MOBILE.md), então optamos por um
e-mail, que chega no celular na hora (a maioria dos celulares já notifica
e-mail novo) sem custo nenhum e sem depender de loja de aplicativo.

Configuração: um arquivo `email_alertas.json` em PASTA_SEGREDOS (mesma pasta,
fora do projeto, onde já fica a chave do Firebase — ver core/cloud_sync.py),
com o formato:
    {
        "remetente": "voce@gmail.com",
        "senha_app": "xxxx xxxx xxxx xxxx",
        "destinatario": "voce@gmail.com",
        "servidor_smtp": "smtp.gmail.com",   (opcional, padrão Gmail)
        "porta_smtp": 465                     (opcional, padrão Gmail)
    }
Se o arquivo não existir, a notificação é silenciosamente ignorada — igual
ao padrão já usado para a sincronização com o celular: ninguém é obrigado a
configurar isso, e o app continua funcionando 100% normalmente sem e-mail.

IMPORTANTE: a senha aqui é uma "senha de app" do Gmail (não a senha normal
da conta — o Gmail exige isso pra acesso de programas desde 2022), e este
arquivo fica FORA da pasta do projeto, no mesmo lugar da chave do Firebase,
justamente pra nunca ser copiada/enviada por engano junto com o projeto.
"""

from __future__ import annotations

import json
import smtplib
from email.mime.text import MIMEText
from typing import Any, Callable

from core.config import PASTA_SEGREDOS

CAMINHO_CONFIG_EMAIL = PASTA_SEGREDOS / "email_alertas.json"

_SERVIDOR_SMTP_PADRAO = "smtp.gmail.com"
_PORTA_SMTP_PADRAO = 465


def notificacoes_configuradas() -> bool:
    """Existe um `email_alertas.json` válido? Se não, todo o resto vira no-op."""
    return _carregar_config() is not None


def _carregar_config() -> dict[str, Any] | None:
    if not CAMINHO_CONFIG_EMAIL.exists():
        return None
    try:
        with open(CAMINHO_CONFIG_EMAIL, "r", encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not config.get("remetente") or not config.get("senha_app") or not config.get("destinatario"):
        return None
    return config


def enviar_email(destinatario: str, remetente: str, senha_app: str, assunto: str, corpo: str,
                  servidor_smtp: str = _SERVIDOR_SMTP_PADRAO, porta_smtp: int = _PORTA_SMTP_PADRAO) -> bool:
    """
    Envia um e-mail simples via SMTP (SSL). Nunca lança exceção — uma falha
    de e-mail (sem internet, senha de app errada, etc.) não pode derrubar o
    resto de "Atualizar Dados"; só retorna False, e o alerta é tentado de
    novo na próxima atualização de cotações.
    """
    try:
        mensagem = MIMEText(corpo, "plain", "utf-8")
        mensagem["Subject"] = assunto
        mensagem["From"] = remetente
        mensagem["To"] = destinatario
        with smtplib.SMTP_SSL(servidor_smtp, porta_smtp, timeout=15) as servidor:
            servidor.login(remetente, senha_app)
            servidor.sendmail(remetente, [destinatario], mensagem.as_string())
        return True
    except Exception:
        return False


def _tickers_com_alerta_atingido(alertas: dict[str, float], cotacao_por_ticker: dict[str, float | None]) -> set[str]:
    """
    Mesmo critério de ui/styles.py:badge_alerta — "atingido" quando a
    cotação CAI até o preço-alvo (ou abaixo), não quando sobe acima dele.
    """
    atingidos = set()
    for ticker, alvo in alertas.items():
        cot = cotacao_por_ticker.get(ticker)
        if cot is not None and cot <= alvo:
            atingidos.add(ticker)
    return atingidos


def _montar_corpo_email(ticker: str, alvo: float, cotacao_atual: float) -> str:
    return (
        f"O preço de {ticker} caiu para R$ {cotacao_atual:.2f}, "
        f"atingindo (ou passando) o seu alvo de R$ {alvo:.2f}.\n\n"
        "Este e-mail é gerado automaticamente pelo Meu Portfólio B3 sempre "
        "que você clica em \"Atualizar Dados\" e um novo alerta de preço é "
        "atingido — não é uma recomendação de compra."
    )


def verificar_e_notificar_alertas(
    dados: dict[str, Any],
    cotacao_por_ticker: dict[str, float | None],
    enviar_email_fn: Callable[..., bool] = enviar_email,
) -> int:
    """
    Compara os alertas configurados (dados["alertas"]) com as cotações mais
    recentes e envia um e-mail para cada alerta que ACABOU de ser atingido
    (isto é, que não estava marcado em dados["alertasEnviados"] ainda).

    Um alerta cuja cotação volta a subir acima do preço-alvo é removido de
    "alertasEnviados", pra poder notificar de novo numa queda futura — sem
    isso, o e-mail seria reenviado a cada "Atualizar Dados" enquanto o preço
    permanecesse abaixo do alvo.

    Retorna quantos e-mails foram enviados com sucesso nesta chamada. Se as
    notificações não estiverem configuradas, não faz nada e retorna 0 —
    quem não configurar o e-mail continua com o app funcionando normalmente
    (só sem o aviso por e-mail).
    """
    config = _carregar_config()
    if config is None:
        return 0

    alertas: dict[str, float] = dados.get("alertas", {})
    ja_notificados: dict[str, bool] = dados.setdefault("alertasEnviados", {})
    atingidos_agora = _tickers_com_alerta_atingido(alertas, cotacao_por_ticker)

    # Reseta quem voltou a subir acima do alvo, pra poder notificar de novo.
    for ticker in list(ja_notificados.keys()):
        if ticker not in atingidos_agora:
            del ja_notificados[ticker]

    enviados = 0
    for ticker in sorted(atingidos_agora):
        if ja_notificados.get(ticker):
            continue
        alvo = alertas[ticker]
        cot = cotacao_por_ticker[ticker]
        sucesso = enviar_email_fn(
            destinatario=config["destinatario"],
            remetente=config["remetente"],
            senha_app=config["senha_app"],
            assunto=f"🔔 {ticker} atingiu o preço-alvo de R$ {alvo:.2f}",
            corpo=_montar_corpo_email(ticker, alvo, cot),
            servidor_smtp=config.get("servidor_smtp", _SERVIDOR_SMTP_PADRAO),
            porta_smtp=config.get("porta_smtp", _PORTA_SMTP_PADRAO),
        )
        if sucesso:
            ja_notificados[ticker] = True
            enviados += 1
        # Se falhar, não marca como notificado — tenta de novo na próxima
        # atualização (ex: sem internet momentaneamente).

    return enviados
