"""
Ações compartilhadas entre abas — hoje, só a atualização de cotações.

Ficou num módulo à parte porque tanto o botão "🔄 Atualizar Dados" da barra
lateral (visível em qualquer aba) quanto o botão "🔄 Atualizar Cotações" da
aba Carteira disparam exatamente a mesma busca no Yahoo Finance. Manter
uma função só evita ter a mesma lógica duplicada em dois arquivos.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from core import altman, b3_publico, calculations as calc, piotroski
from core import cloud_sync, fundamentals, market_data, notificacoes_whatsapp, setores
from core.config import INTERVALO_ATUALIZACAO_PROVENTOS_B3_SEGUNDOS
from core.mobile_snapshot import montar_snapshot_para_celular
from core.pendencias_celular import (
    aplicar_calculos_teto_do_celular,
    aplicar_pendencias_do_celular,
    aplicar_remocoes_do_celular,
    aplicar_teses_do_celular,
)
from ui.ativos import montar_lista_ativos


def atualizar_dados(dados: dict, salvar) -> None:
    """
    Aplica pedidos feitos pelo celular (nova compra/venda, remoção de
    transação, cálculo de preço teto — se houver), busca cotações novas no
    Yahoo Finance para todas as posições da carteira e empresas-alvo da
    watchlist, salva um snapshot de patrimônio para o gráfico de Evolução,
    e persiste tudo em disco.
    """
    aplicadas_do_celular, erros_do_celular = aplicar_pendencias_do_celular(dados, salvar)
    removidas_do_celular, erros_remocao_celular = aplicar_remocoes_do_celular(dados, salvar)
    calculadas_do_celular, erros_calculo_celular = aplicar_calculos_teto_do_celular(dados, salvar)
    teses_do_celular, erros_tese_celular = aplicar_teses_do_celular(dados, salvar)

    posicoes = calc.consolidar_posicoes(dados["compras"], dados["eventos"])
    tickers_posicoes = {p["ticker"] for p in posicoes}
    tickers_alvo = [t for t in dados["watchlist"] if t not in tickers_posicoes]
    tickers = [p["ticker"] for p in posicoes] + tickers_alvo

    if not tickers:
        st.session_state["status_cotacoes"] = (
            'Registre ao menos uma compra na aba "Compras & Vendas" (ou adicione uma empresa alvo) '
            "antes de atualizar os dados."
        )
        return

    # Ignora o cache de 5 minutos e força uma busca nova — é justamente para
    # isso que o botão existe (requisito 4 do projeto: forçar nova busca).
    market_data.limpar_cache_cotacoes()
    with st.spinner(f"Buscando cotações de {len(tickers)} ativo(s) no Yahoo Finance..."):
        novas_cotacoes, falhas = market_data.atualizar_cotacoes(tickers, dados["cotacoes"])
        dados["cotacoes"] = novas_cotacoes
        ibov = market_data.buscar_cotacao_ibovespa()

    # HG Brasil (2026-09-03) — plano B só para os tickers que o Yahoo
    # Finance não conseguiu, e fonte das taxas SELIC/CDI (que o Yahoo não
    # tem). Ver core/market_data.py para o porquê dessa divisão de papéis.
    # Se a chave da HG Brasil não estiver configurada (caso normal, até
    # Diego configurá-la), as duas chamadas abaixo só devolvem "sem
    # resultado" silenciosamente — nada muda no comportamento de hoje.
    cobertas_pela_hgbrasil: list[str] = []
    if falhas:
        cotacoes_hgbrasil = market_data.buscar_cotacoes_hgbrasil(falhas)
        for ticker, cotacao in cotacoes_hgbrasil.items():
            dados["cotacoes"][ticker] = cotacao
            cobertas_pela_hgbrasil.append(ticker)
        falhas = [t for t in falhas if t not in cotacoes_hgbrasil]

    taxas_economicas = market_data.buscar_taxas_economicas()
    if taxas_economicas is not None:
        dados["taxasEconomicas"] = taxas_economicas
    # Se taxas_economicas vier None (chave não configurada, ou falha
    # passageira), mantém o último valor bom conhecido em
    # dados["taxasEconomicas"] — de propósito, não apaga o que já tinha.

    _registrar_snapshot(dados, ibov)

    # Alerta de preço-alvo por WhatsApp (core/notificacoes_whatsapp.py) —
    # só faz algo de verdade se você configurou whatsapp_alertas.json; do
    # contrário é um no-op silencioso, igual à sincronização com o celular
    # acima. (Substituiu o alerta por e-mail em 2026-08-31 — ver
    # core/notificacoes_email.py, mantido no projeto mas sem uso ativo.)
    cotacao_por_ticker = {a["ticker"]: a["cotacao_atual"] for a in montar_lista_ativos(dados)}
    alertas_notificados_agora = notificacoes_whatsapp.verificar_e_notificar_alertas(dados, cotacao_por_ticker)

    salvar(dados)

    # Envia o retrato mais recente da carteira pro Firestore, pro app do
    # celular ler — só acontece de verdade se o celular já foi configurado
    # (ver README_MOBILE.md); do contrário isso é um "no-op" silencioso.
    sincronizado_com_celular = False
    if cloud_sync.sincronizacao_configurada():
        sincronizado_com_celular = cloud_sync.sincronizar_snapshot(montar_snapshot_para_celular(dados))

    agora = datetime.now().strftime("%H:%M:%S")
    sufixo_celular = ""
    if cloud_sync.sincronizacao_configurada():
        sufixo_celular = " 📱 Sincronizado com o celular." if sincronizado_com_celular else " ⚠️ Falha ao sincronizar com o celular (sem internet ou chave inválida)."
    if aplicadas_do_celular:
        sufixo_celular += f" ➕ {aplicadas_do_celular} transação(ões) registrada(s) pelo celular foram aplicadas."
    if removidas_do_celular:
        sufixo_celular += f" 🗑️ {removidas_do_celular} transação(ões) removida(s) pelo celular."
    if calculadas_do_celular:
        sufixo_celular += f" 🎯 {calculadas_do_celular} preço(s) teto calculado(s) pelo celular."
    if teses_do_celular:
        sufixo_celular += f" 📓 {teses_do_celular} entrada(s) do diário de tese escrita(s) pelo celular."
    total_erros_celular = erros_do_celular + erros_remocao_celular + erros_calculo_celular + erros_tese_celular
    if total_erros_celular:
        sufixo_celular += f" ⚠️ {total_erros_celular} pedido(s) do celular não puderam ser aplicados (dados inválidos)."
    if alertas_notificados_agora:
        plural = "s" if alertas_notificados_agora > 1 else ""
        sufixo_celular += f" 💬 {alertas_notificados_agora} alerta{plural} de preço enviado{plural} por WhatsApp."

    sufixo_hgbrasil = ""
    if cobertas_pela_hgbrasil:
        sufixo_hgbrasil = f" 🔁 {len(cobertas_pela_hgbrasil)} ativo(s) resolvido(s) pela HG Brasil (plano B): {', '.join(cobertas_pela_hgbrasil)}."

    if falhas:
        st.session_state["status_cotacoes"] = (
            f"Atualizado às {agora}. {len(tickers) - len(falhas)} de {len(tickers)} ativo(s) ok, "
            f"mesmo após nova tentativa. Sem dados para: {', '.join(falhas)}. "
            "É comum ser passageiro (o Yahoo Finance às vezes recusa uma consulta no meio de uma rajada) "
            "— clique em \"🔄 Atualizar Dados\" de novo em alguns segundos." + sufixo_hgbrasil + sufixo_celular
        )
        st.session_state["status_cotacoes_falhou"] = True
    else:
        st.session_state["status_cotacoes"] = f"Dados atualizados às {agora} — Yahoo Finance (yfinance)." + sufixo_hgbrasil + sufixo_celular
        st.session_state["status_cotacoes_falhou"] = False

    # Proventos anunciados pela B3 (aba Proventos → Mapa de Dividendos e
    # Próximos Dividendos) — automático, mas autolimitado a 1x/dia (ver
    # atualizar_proventos_b3) pra não deixar "Atualizar Dados" mais lento
    # a cada clique.
    atualizar_proventos_b3(dados, salvar)


def atualizar_dados_fundamentalistas(dados: dict, salvar) -> None:
    """
    Busca indicadores fundamentalistas (P/L, P/VP, Dividend Yield, ROE...)
    para as posições da carteira e a watchlist. Separado do botão de preço
    porque `.info` do yfinance é uma chamada bem mais pesada — não faz
    sentido repeti-la toda vez que só se quer atualizar uma cotação.
    """
    posicoes = calc.consolidar_posicoes(dados["compras"], dados["eventos"])
    tickers_posicoes = {p["ticker"] for p in posicoes}
    tickers_alvo = [t for t in dados["watchlist"] if t not in tickers_posicoes]
    tickers = [p["ticker"] for p in posicoes] + tickers_alvo

    if not tickers:
        st.session_state["status_fundamentos"] = (
            'Registre ao menos uma compra ou adicione uma empresa alvo antes de buscar fundamentos.'
        )
        return

    fundamentals.limpar_cache_fundamentos()
    with st.spinner(f"Buscando indicadores fundamentalistas de {len(tickers)} ativo(s)..."):
        novos_fundamentos, falhas = fundamentals.atualizar_fundamentos(tickers, dados.get("fundamentos", {}))
        dados["fundamentos"] = novos_fundamentos

    # Sugere automaticamente (sem nunca sobrescrever uma escolha manual) o
    # setor dos ativos que ainda não têm um definido, a partir do setor que
    # o Yahoo devolveu junto com os fundamentos — ver core/setores.py.
    setores_sugeridos = setores.preencher_setores_sugeridos(dados)

    salvar(dados)

    agora = datetime.now().strftime("%H:%M:%S")
    sufixo_setores = f" 🏷️ Setor sugerido automaticamente para {setores_sugeridos} ativo(s) novo(s) (revise em ⚙️ na aba Carteira, se quiser)." if setores_sugeridos else ""
    if falhas:
        st.session_state["status_fundamentos"] = (
            f"Fundamentos atualizados às {agora}. {len(tickers) - len(falhas)} de {len(tickers)} ativo(s) ok. "
            f"Sem dados para: {', '.join(falhas)} — tente novamente em alguns segundos." + sufixo_setores
        )
        st.session_state["status_fundamentos_falhou"] = True
    else:
        st.session_state["status_fundamentos"] = f"Fundamentos atualizados às {agora} — Yahoo Finance (yfinance)." + sufixo_setores
        st.session_state["status_fundamentos_falhou"] = False


def atualizar_analise_avancada(dados: dict, salvar) -> None:
    """
    Busca e calcula o Piotroski F-Score e o Altman Z-Score das posições da
    carteira e da watchlist. Separado do botão "🔄 Atualizar Fundamentos"
    porque exige buscar as demonstrações financeiras ANUAIS completas
    (balanço, DRE e DFC de vários anos) — bem mais pesado que só o `.info`
    usado para P/L, ROE etc., então não faz sentido repetir isso toda vez
    que só se quer atualizar os fundamentos básicos.

    Cada ticker é tratado de forma independente: se o Piotroski não deu
    certo para um ativo mas o Altman deu (ou vice-versa), o que funcionou é
    salvo normalmente — um não trava o outro.

    2026-09-03: a busca de todos os tickers agora roda em paralelo, e
    Piotroski+Altman do mesmo ticker compartilham a mesma busca de
    demonstrações anuais nos bastidores — ver
    core.fundamentals.buscar_analise_avancada_varios().
    """
    posicoes = calc.consolidar_posicoes(dados["compras"], dados["eventos"])
    tickers_posicoes = {p["ticker"] for p in posicoes}
    tickers_alvo = [t for t in dados["watchlist"] if t not in tickers_posicoes]
    tickers = [p["ticker"] for p in posicoes] + tickers_alvo

    if not tickers:
        st.session_state["status_analise_avancada"] = (
            "Registre ao menos uma compra ou adicione uma empresa alvo antes de buscar a análise avançada."
        )
        return

    fundamentals.limpar_cache_piotroski()
    fundamentals.limpar_cache_altman()

    falhas_piotroski = []
    falhas_altman = []
    agora = datetime.now().strftime("%d/%m/%Y %H:%M")

    with st.spinner(f"Buscando Piotroski F-Score e Altman Z-Score de {len(tickers)} ativo(s) — isso demora um pouco mais que o normal..."):
        piotroski_por_ticker, altman_por_ticker = fundamentals.buscar_analise_avancada_varios(tickers)

    for ticker in tickers:
        dados_brutos_piotroski = piotroski_por_ticker.get(ticker)
        if dados_brutos_piotroski is not None:
            resultado = piotroski.calcular_piotroski(dados_brutos_piotroski)
            dados["piotroski"][ticker] = {
                "pontos": resultado.pontos,
                "totalAvaliado": resultado.total_avaliado,
                "classificacao": resultado.classificacao,
                "criterios": [
                    {"chave": c.chave, "rotulo": c.rotulo, "grupo": c.grupo, "passou": c.passou}
                    for c in resultado.criterios
                ],
                "atualizadoEm": agora,
            }
        else:
            falhas_piotroski.append(ticker)

        dados_brutos_altman = altman_por_ticker.get(ticker)
        if dados_brutos_altman is not None:
            resultado_altman = altman.calcular_altman(dados_brutos_altman)
            dados["altman"][ticker] = {
                "zScore": resultado_altman.z_score,
                "classificacao": resultado_altman.classificacao,
                "atualizadoEm": agora,
            }
        else:
            falhas_altman.append(ticker)

    salvar(dados)

    partes = [f"Análise avançada atualizada às {agora.split(' ')[1]}."]
    partes.append(f"Piotroski: {len(tickers) - len(falhas_piotroski)} de {len(tickers)} ativo(s) ok.")
    partes.append(f"Altman: {len(tickers) - len(falhas_altman)} de {len(tickers)} ativo(s) ok.")
    if falhas_piotroski:
        partes.append(f"Sem Piotroski para: {', '.join(falhas_piotroski)}.")
    if falhas_altman:
        partes.append(f"Sem Altman para: {', '.join(falhas_altman)}.")
    st.session_state["status_analise_avancada"] = " ".join(partes)
    st.session_state["status_analise_avancada_falhou"] = bool(falhas_piotroski or falhas_altman)


def atualizar_proventos_b3(dados: dict, salvar, forcar: bool = False) -> None:
    """
    Busca, direto no site oficial da B3 (core/b3_publico.py), os
    dividendos/JCP/rendimentos já anunciados pelas empresas da carteira +
    watchlist. Usada de dois jeitos:

    - Automaticamente dentro de atualizar_dados() ("🔄 Atualizar Dados"),
      com `forcar=False`: só busca de verdade se já se passou
      INTERVALO_ATUALIZACAO_PROVENTOS_B3_SEGUNDOS desde a última vez que
      funcionou (ver b3_publico.precisa_atualizar) — evita bater no site
      da B3 a cada clique, já que um novo provento anunciado é raro.
    - Sob demanda pelo botão dedicado na aba Proventos, com `forcar=True`:
      ignora esse intervalo e busca na hora, sempre.

    Falha (sem_conexao) NÃO apaga o que já estava salvo em
    dados["proventosAnunciadosB3"] nem atualiza o timestamp — o Mapa de
    Dividendos continua mostrando o último resultado que funcionou, e a
    próxima tentativa automática já acontece no PRÓXIMO "Atualizar Dados"
    (não espera o intervalo cheio de novo depois de uma falha).
    """
    agora = datetime.now()
    if not forcar and not b3_publico.precisa_atualizar(
        dados.get("proventosAnunciadosB3AtualizadoEm"), agora, INTERVALO_ATUALIZACAO_PROVENTOS_B3_SEGUNDOS
    ):
        return

    posicoes = calc.consolidar_posicoes(dados["compras"], dados["eventos"])
    tickers_posicoes = {p["ticker"] for p in posicoes}
    tickers_alvo = [t for t in dados["watchlist"] if t not in tickers_posicoes]
    tickers = [p["ticker"] for p in posicoes] + tickers_alvo
    if not tickers:
        return

    with st.spinner(f"Buscando proventos anunciados pela B3 para {len(tickers)} ativo(s)..."):
        anunciados, sem_conexao = b3_publico.buscar_proventos_anunciados_varios(tickers)

    if sem_conexao:
        st.session_state["status_proventos_b3"] = (
            "Não consegui acessar o site da B3 agora (pode ser bloqueio temporário do site ou falta "
            "de internet). O Mapa de Dividendos automático continua mostrando o resultado da última "
            "busca que funcionou — vou tentar de novo automaticamente na próxima vez que você clicar "
            "em \"🔄 Atualizar Dados\"."
        )
        st.session_state["status_proventos_b3_falhou"] = True
        return

    dados["proventosAnunciadosB3"] = anunciados
    dados["proventosAnunciadosB3AtualizadoEm"] = agora.isoformat()
    salvar(dados)
    st.session_state["status_proventos_b3"] = f"Proventos anunciados pela B3 atualizados às {agora.strftime('%H:%M:%S')}."
    st.session_state["status_proventos_b3_falhou"] = False


def exibir_status_proventos_b3() -> None:
    """Equivalente a exibir_status_cotacoes(), para a busca automática de proventos anunciados pela B3."""
    if "status_proventos_b3" not in st.session_state:
        return
    if st.session_state.get("status_proventos_b3_falhou"):
        st.warning(st.session_state["status_proventos_b3"])
    else:
        st.caption(st.session_state["status_proventos_b3"])


def exibir_status_analise_avancada() -> None:
    """Equivalente a exibir_status_cotacoes(), para a busca de Piotroski/Altman."""
    if "status_analise_avancada" not in st.session_state:
        return
    if st.session_state.get("status_analise_avancada_falhou"):
        st.warning(st.session_state["status_analise_avancada"])
    else:
        st.caption(st.session_state["status_analise_avancada"])


def exibir_status_cotacoes() -> None:
    """
    Mostra o resultado da última atualização de preços. Usa um aviso mais
    visível (st.warning) quando algum ticker falhou — antes ficava só num
    texto pequeno e cinza (st.caption), fácil de passar despercebido —
    para não dar a falsa impressão de que "está tudo certo" quando alguma
    empresa-alvo, por exemplo, não teve a cotação atualizada.
    """
    if "status_cotacoes" not in st.session_state:
        return
    if st.session_state.get("status_cotacoes_falhou"):
        st.warning(st.session_state["status_cotacoes"])
    else:
        st.caption(st.session_state["status_cotacoes"])


def exibir_status_fundamentos() -> None:
    """Equivalente a exibir_status_cotacoes(), para a busca de fundamentos."""
    if "status_fundamentos" not in st.session_state:
        return
    if st.session_state.get("status_fundamentos_falhou"):
        st.warning(st.session_state["status_fundamentos"])
    else:
        st.caption(st.session_state["status_fundamentos"])


def _registrar_snapshot(dados: dict, ibov: float | None) -> None:
    """Salva um snapshot diário de patrimônio para o gráfico de Evolução (1 por dia)."""
    posicoes = calc.calcular_posicoes_completas(dados["compras"], dados["eventos"], dados["cotacoes"])
    if not posicoes:
        return
    total_investido = sum(p["valor_total_investido"] for p in posicoes)
    total_atual = sum(p["atual"] for p in posicoes)
    hoje = datetime.now().strftime("%Y-%m-%d")
    existente = next((h for h in dados["historico"] if h["data"] == hoje), None)
    if existente:
        existente["totalInvestido"] = total_investido
        existente["totalAtual"] = total_atual
        if ibov:
            existente["ibov"] = ibov
    else:
        dados["historico"].append({"data": hoje, "totalInvestido": total_investido, "totalAtual": total_atual, "ibov": ibov})
    dados["historico"].sort(key=lambda h: h["data"])
