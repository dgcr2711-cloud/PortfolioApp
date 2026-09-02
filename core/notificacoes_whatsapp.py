"""
Envia uma mensagem de WhatsApp quando a cotação de um ativo CAI até (ou
abaixo d)o preço que você configurou em "⚙️ Configurações → Alertas de
Preço-Alvo" — mesmo critério do selo 🔔/🔕 já usado em ui/styles.py:badge_alerta
(ver o comentário lá para o motivo da direção da comparação).

Substituiu o alerta por e-mail (core/notificacoes_email.py — mantido no
projeto, mas sem uso ativo) em 2026-08-31, a pedido do usuário: configurar
o WhatsApp é mais rápido (uma mensagem de ativação, sem mexer em
"verificação em duas etapas" nem "senha de app" do Google).

Por trás dos panos, isto usa o CallMeBot (https://www.callmebot.com/) — um
serviço GRATUITO e de TERCEIROS (não é do WhatsApp/Meta nem do Google) que
manda mensagens de WhatsApp através de um link (sem precisar de nenhuma
biblioteca extra, só a internet). Vale saber: por ser um serviço gratuito e
informal, ele pode ocasionalmente ficar fora do ar (o próprio CallMeBot já
teve situações assim no passado) — se um dia os alertas pararem de chegar
sem nenhuma mudança sua, vale suspeitar disso antes de qualquer outra
coisa.

Configuração: um arquivo `whatsapp_alertas.json` em PASTA_SEGREDOS (mesma
pasta, fora do projeto, onde já fica a chave do Firebase — ver
core/cloud_sync.py), com o formato:
    {
        "numero": "+5511999999999",
        "apikey": "123456"
    }

IMPORTANTE sobre o formato do "numero" (descoberto 2026-09-01 com um caso
real): o CallMeBot aceita o pedido normalmente e ainda assim não entrega a
mensagem se o número tiver o "9" extra que os celulares brasileiros
ganharam há alguns anos — ou seja, use +55DDDNÚMERO com só 8 dígitos depois
do DDD (ex: +553197001985), NÃO +55DDD9NÚMERO com 9 dígitos
(+5531997001985). Isso não gera nenhum erro visível (o CallMeBot confirma
"enviado" do mesmo jeito) — só descobre-se porque a mensagem nunca chega no
WhatsApp de verdade.
Se o arquivo não existir, a notificação é silenciosamente ignorada — igual
ao padrão já usado para a sincronização com o celular e o e-mail: ninguém é
obrigado a configurar isso, e o app continua funcionando 100% normalmente
sem WhatsApp.

Como conseguir "numero" e "apikey" (ver README_ALERTAS_SEGUNDO_PLANO.md
para o passo a passo completo com prints):
    1. Salve o número +34 694 23 41 84 nos contatos do seu celular (o
       "robô" do CallMeBot).
    2. Mande para ele, pelo WhatsApp, exatamente esta mensagem:
       "I allow callmebot to send me messages"
    3. Em até 2 minutos ele responde com a sua "apikey".
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable

from core.config import PASTA_SEGREDOS

CAMINHO_CONFIG_WHATSAPP = PASTA_SEGREDOS / "whatsapp_alertas.json"

_URL_BASE_CALLMEBOT = "https://api.callmebot.com/whatsapp.php"


def notificacoes_configuradas() -> bool:
    """Existe uma configuração de WhatsApp válida (arquivo local, variável de ambiente ou Secrets do Streamlit)? Se não, todo o resto vira no-op."""
    return _carregar_config() is not None


def _config_tem_campos_obrigatorios(config: dict[str, Any]) -> bool:
    return bool(config.get("numero") and config.get("apikey"))


def _carregar_config() -> dict[str, Any] | None:
    """
    Carrega a configuração do WhatsApp, nesta ordem: (1) do arquivo local
    (uso normal no seu PC), (2) das variáveis de ambiente (script de
    segundo plano no GitHub Actions — ver
    _carregar_config_da_variavel_de_ambiente), (3) dos "Secrets" do
    Streamlit Cloud (uso hospedado — ver _carregar_config_do_streamlit).
    """
    config = _carregar_config_do_arquivo()
    if config is not None:
        return config
    config = _carregar_config_da_variavel_de_ambiente()
    if config is not None:
        return config
    return _carregar_config_do_streamlit()


def _carregar_config_do_arquivo() -> dict[str, Any] | None:
    if not CAMINHO_CONFIG_WHATSAPP.exists():
        return None
    try:
        with open(CAMINHO_CONFIG_WHATSAPP, "r", encoding="utf-8") as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    if not _config_tem_campos_obrigatorios(config):
        return None
    return config


def _carregar_config_da_variavel_de_ambiente() -> dict[str, Any] | None:
    """
    Fallback usado pelo script de segundo plano do GitHub Actions
    (ver scripts/verificar_alertas_segundo_plano.py e
    .github/workflows/verificar_alertas.yml): lá não existe nem a pasta
    pessoal do PC nem um app Streamlit de verdade rodando, então a
    configuração vem de "Secrets" do próprio repositório do GitHub
    (Settings -> Secrets and variables -> Actions), expostos ao script
    como variáveis de ambiente — nunca no código, nunca commitado:

        WHATSAPP_ALERTA_NUMERO
        WHATSAPP_ALERTA_APIKEY

    Retorna None sem erro nenhum se as duas variáveis não estiverem ambas
    presentes (uso normal no PC ou num app hospedado).
    """
    numero = os.environ.get("WHATSAPP_ALERTA_NUMERO")
    apikey = os.environ.get("WHATSAPP_ALERTA_APIKEY")
    if not (numero and apikey):
        return None
    return {"numero": numero, "apikey": apikey}


def _carregar_config_do_streamlit() -> dict[str, Any] | None:
    """
    Fallback usado quando este código roda HOSPEDADO no Streamlit Community
    Cloud — lá não existe a pasta pessoal do seu PC
    (~/.portfolio_b3_secrets), então a configuração do WhatsApp é colada no
    painel "Secrets" do próprio app, no site do Streamlit Cloud (nunca no
    código, nunca no GitHub), sob a chave [whatsapp_alertas]. Ver
    README_HOSPEDAGEM.md para o passo a passo de como colar isso lá.

    Retorna None sem erro nenhum em qualquer um destes casos: rodando no
    PC (a configuração já veio do arquivo, acima), rodando fora de um app
    Streamlit de verdade (ex: um script de segundo plano no GitHub
    Actions), streamlit nem estando instalado, ou a chave não estar
    configurada/completa nos Secrets.
    """
    try:
        import streamlit as st

        if "whatsapp_alertas" in st.secrets:
            config = dict(st.secrets["whatsapp_alertas"])
            if _config_tem_campos_obrigatorios(config):
                return config
    except Exception:
        pass
    return None


def enviar_whatsapp(numero: str, apikey: str, mensagem: str) -> bool:
    """
    Envia uma mensagem de WhatsApp via CallMeBot (ver docstring do módulo).
    Nunca lança exceção — uma falha (sem internet, apikey errada, CallMeBot
    fora do ar etc.) não pode derrubar o resto de "Atualizar Dados"; só
    retorna False, e o alerta é tentado de novo na próxima atualização de
    cotações.

    O CallMeBot não documenta um formato de erro estruturado — tratamos
    como sucesso qualquer resposta HTTP "de sucesso" (200-299; na prática o
    CallMeBot às vezes responde 201 em vez de 200 pro mesmo caso de
    sucesso — descoberto em 2026-09-01 com um alerta real do usuário que
    nunca chegava por causa disso) cujo corpo não contenha a palavra
    "error" (comparação sem diferenciar maiúsculas/minúsculas); qualquer
    outra coisa (erro de conexão, HTTP de erro, "error" no corpo) conta
    como falha.
    """
    try:
        url = (
            f"{_URL_BASE_CALLMEBOT}"
            f"?phone={urllib.parse.quote(numero)}"
            f"&text={urllib.parse.quote(mensagem)}"
            f"&apikey={urllib.parse.quote(apikey)}"
        )
        with urllib.request.urlopen(url, timeout=15) as resposta:
            status = resposta.status
            corpo = resposta.read().decode("utf-8", errors="ignore")
            if not (200 <= status < 300):
                # Lê e mostra o corpo mesmo em erro (antes só mostrava o
                # status) — se um dia aparecer outro status "estranho" como
                # o 201, o texto do corpo já vem no log, sem precisar de
                # mais uma rodada de teste só pra descobrir o que ele diz.
                print(f"[alertas] Falha ao enviar WhatsApp: CallMeBot respondeu HTTP {status}: {corpo.strip()[:200]}")
                return False
            sucesso = "error" not in corpo.lower()
            if sucesso:
                if status != 200:
                    # Caso do HTTP 201 descoberto em 2026-09-01: mostra o
                    # corpo mesmo no sucesso, pra confirmar visivelmente
                    # (no log) que a mensagem foi mesmo aceita pelo CallMeBot.
                    print(f"[alertas] WhatsApp enviado (CallMeBot respondeu HTTP {status}): {corpo.strip()[:200]}")
            else:
                print(f"[alertas] Falha ao enviar WhatsApp: CallMeBot respondeu com um erro: {corpo.strip()[:200]}")
            return sucesso
    except (urllib.error.URLError, OSError, ValueError) as erro:
        # Não expõe numero/apikey (só o tipo/motivo do erro) — ajuda a diagnosticar
        # sem internet, apikey errada, certificado, DNS bloqueado etc.
        print(f"[alertas] Falha ao enviar WhatsApp: {type(erro).__name__}: {erro}")
        return False


def _tickers_com_alerta_atingido(alertas: dict[str, float], cotacao_por_ticker: dict[str, float | None]) -> set[str]:
    """
    Mesmo critério de ui/styles.py:badge_alerta e de
    core/notificacoes_email.py — "atingido" quando a cotação CAI até o
    preço-alvo (ou abaixo), não quando sobe acima dele.
    """
    atingidos = set()
    for ticker, alvo in alertas.items():
        cot = cotacao_por_ticker.get(ticker)
        if cot is not None and cot <= alvo:
            atingidos.add(ticker)
    return atingidos


def _montar_mensagem_whatsapp(ticker: str, alvo: float, cotacao_atual: float) -> str:
    return (
        f"🔔 {ticker} atingiu o preço-alvo!\n"
        f"O preço caiu para R$ {cotacao_atual:.2f}, atingindo (ou passando) "
        f"o seu alvo de R$ {alvo:.2f}.\n\n"
        "Mensagem automática do Meu Portfólio B3 — não é uma recomendação de compra."
    )


def verificar_e_notificar_alertas(
    dados: dict[str, Any],
    cotacao_por_ticker: dict[str, float | None],
    enviar_whatsapp_fn: Callable[..., bool] = enviar_whatsapp,
) -> int:
    """
    Compara os alertas configurados (dados["alertas"]) com as cotações mais
    recentes e manda uma mensagem de WhatsApp para cada alerta que ACABOU
    de ser atingido (isto é, que não estava marcado em
    dados["alertasEnviados"] ainda) — mesma lógica de
    core/notificacoes_email.py::verificar_e_notificar_alertas, só trocando
    o canal de envio; ver lá para os detalhes do reset ao subir de novo.

    Retorna quantas mensagens foram enviadas com sucesso nesta chamada. Se
    as notificações não estiverem configuradas, não faz nada e retorna 0.
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
        sucesso = enviar_whatsapp_fn(
            numero=config["numero"],
            apikey=config["apikey"],
            mensagem=_montar_mensagem_whatsapp(ticker, alvo, cot),
        )
        if sucesso:
            ja_notificados[ticker] = True
            enviados += 1
        # Se falhar, não marca como notificado — tenta de novo na próxima
        # atualização (ex: sem internet momentaneamente, ou CallMeBot fora do ar).

    return enviados
