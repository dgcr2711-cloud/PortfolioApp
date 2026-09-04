"""
Script de atualização completa em SEGUNDO PLANO (2026-08-30, canal WhatsApp
desde 2026-08-31; ampliado 2026-09-05 para fazer TUDO que o botão
"🔄 Atualizar Dados" do PC faz, não só verificar alertas — é o que elimina a
dependência do PC estar ligado para o celular continuar sincronizando).

Roda sozinho, num horário fixo, mesmo que o PC esteja desligado e ninguém
abra o app naquele dia — pelo GitHub Actions (ver
.github/workflows/verificar_alertas.yml para o agendamento). Faz, em ordem,
exatamente o que ui/acoes_comuns.py::atualizar_dados faz no PC — este script
é a versão "sem tela" da mesma lógica, reaproveitando as MESMAS funções core
já testadas, para nunca existir uma segunda implementação que possa divergir:

  1. Aplica pedidos pendentes feitos pelo celular (nova compra/venda,
     remoção de transação, cálculo de preço teto, entrada no diário de
     tese) — core/pendencias_celular.py.
  2. Busca cotações novas no Yahoo Finance (plano B: HG Brasil) para as
     posições e a watchlist, e a cotação do Ibovespa.
  3. Busca proventos anunciados pela B3 (autolimitado a 1x/dia, igual ao
     comportamento do botão no PC).
  4. Registra um snapshot de patrimônio para o gráfico de Evolução.
  5. Compara com os alertas de preço-alvo configurados e manda uma
     mensagem de WhatsApp para os que acabaram de ser atingidos.
  6. Salva tudo — local (disco efêmero do GitHub Actions, sem efeito real)
     e no Firestore, que é o que o PC e o celular realmente leem.
  7. Monta e envia o retrato resumido da carteira (snapshot) pro Firestore,
     pro app do celular ler em tempo real.

Onde ficam as credenciais aqui? Este script roda numa máquina do GitHub, não
no seu PC — não existe a pasta pessoal (~/.portfolio_b3_secrets) nem um app
Streamlit de verdade rodando. Por isso a chave do Firebase e a configuração
do WhatsApp vêm de "Secrets" do próprio repositório do GitHub (Settings ->
Secrets and variables -> Actions), expostos a este script como variáveis de
ambiente — ver core/cloud_sync.py::_obter_credenciais_dict_da_variavel_de_
ambiente e core/notificacoes_whatsapp.py::_carregar_config_da_variavel_de_
ambiente. Nunca ficam no código nem são commitados.

Nunca lança exceção "para cima": qualquer problema (sem cotação para um
ticker, Firestore fora do ar, CallMeBot fora do ar, site da B3 bloqueando
etc.) já é tratado dentro das próprias funções reaproveitadas aqui (mesmas
usadas e testadas no app principal) — este script só decide o que imprimir
no log do GitHub Actions e qual código de saída devolver.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

# Permite rodar este script diretamente (python scripts/verificar_alertas_segundo_plano.py)
# sem precisar instalar o projeto como pacote — mesmo truque usado em app.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import b3_publico, calculations as calc, cloud_sync, market_data  # noqa: E402
from core.config import INTERVALO_ATUALIZACAO_PROVENTOS_B3_SEGUNDOS  # noqa: E402
from core.data_store import carregar_dados, salvar_dados  # noqa: E402
from core.mobile_snapshot import montar_snapshot_para_celular  # noqa: E402
from core.notificacoes_whatsapp import (  # noqa: E402
    notificacoes_configuradas,
    verificar_e_notificar_alertas,
)
from core.pendencias_celular import (  # noqa: E402
    aplicar_calculos_teto_do_celular,
    aplicar_pendencias_do_celular,
    aplicar_remocoes_do_celular,
    aplicar_teses_do_celular,
)
from ui.acoes_comuns import _registrar_snapshot  # noqa: E402


def _atualizar_proventos_b3_sem_tela(dados: dict, forcar: bool = False) -> None:
    """
    Mesma lógica de ui/acoes_comuns.py::atualizar_proventos_b3, sem as
    chamadas a st.spinner/st.session_state (que exigem um app Streamlit de
    verdade rodando — travariam este script). Só altera `dados` em memória;
    quem chama salva depois (este script salva tudo de uma vez só, no
    final, em vez de a cada etapa como o botão do PC faz).
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

    anunciados, sem_conexao = b3_publico.buscar_proventos_anunciados_varios(tickers)
    if sem_conexao:
        print("[atualizar] Aviso: não consegui acessar o site da B3 agora — tento de novo na próxima execução.")
        return

    dados["proventosAnunciadosB3"] = anunciados
    dados["proventosAnunciadosB3AtualizadoEm"] = agora.isoformat()
    print(f"[atualizar] Proventos anunciados pela B3 atualizados para {len(anunciados)} ativo(s).")


def main() -> int:
    dados = carregar_dados()

    # 1. Pedidos pendentes do celular — mesma busca em paralelo já usada
    # pelo botão do PC (ver core/cloud_sync.py::buscar_pendencias_pendentes_varias_colecoes).
    pendencias_por_colecao = cloud_sync.buscar_pendencias_pendentes_varias_colecoes([
        cloud_sync.COLECAO_PENDENCIAS,
        cloud_sync.COLECAO_PENDENCIAS_REMOCOES,
        cloud_sync.COLECAO_PENDENCIAS_PRECO_TETO,
        cloud_sync.COLECAO_PENDENCIAS_TESE,
    ])
    aplicadas, erros_compra = aplicar_pendencias_do_celular(
        dados, salvar_dados, pendencias_por_colecao.get(cloud_sync.COLECAO_PENDENCIAS)
    )
    removidas, erros_remocao = aplicar_remocoes_do_celular(
        dados, salvar_dados, pendencias_por_colecao.get(cloud_sync.COLECAO_PENDENCIAS_REMOCOES)
    )
    calculadas, erros_calculo = aplicar_calculos_teto_do_celular(
        dados, salvar_dados, pendencias_por_colecao.get(cloud_sync.COLECAO_PENDENCIAS_PRECO_TETO)
    )
    teses_aplicadas, erros_tese = aplicar_teses_do_celular(
        dados, salvar_dados, pendencias_por_colecao.get(cloud_sync.COLECAO_PENDENCIAS_TESE)
    )
    total_celular = aplicadas + removidas + calculadas + teses_aplicadas
    total_erros_celular = erros_compra + erros_remocao + erros_calculo + erros_tese
    if total_celular:
        print(
            f"[atualizar] {total_celular} pedido(s) do celular aplicado(s) "
            f"({aplicadas} compra/venda, {removidas} remoção(ões), {calculadas} preço(s) teto, {teses_aplicadas} tese(s))."
        )
    if total_erros_celular:
        print(f"[atualizar] Aviso: {total_erros_celular} pedido(s) do celular não puderam ser aplicados (dados inválidos).")

    # 2. Cotações.
    posicoes = calc.consolidar_posicoes(dados["compras"], dados["eventos"])
    tickers_posicoes = {p["ticker"] for p in posicoes}
    tickers_alvo = [t for t in dados["watchlist"] if t not in tickers_posicoes]
    tickers = [p["ticker"] for p in posicoes] + tickers_alvo

    if not tickers:
        print("[atualizar] Nenhuma posição nem empresa-alvo na carteira — nada a atualizar.")
        salvar_dados(dados)
        return 0

    print(f"[atualizar] Buscando cotação de {len(tickers)} ativo(s) no Yahoo Finance...")
    novas_cotacoes, falhas = market_data.atualizar_cotacoes(tickers, dados["cotacoes"])
    dados["cotacoes"] = novas_cotacoes
    ibov = market_data.buscar_cotacao_ibovespa()

    if falhas:
        cotacoes_hgbrasil = market_data.buscar_cotacoes_hgbrasil(falhas)
        for ticker, cotacao in cotacoes_hgbrasil.items():
            dados["cotacoes"][ticker] = cotacao
        falhas = [t for t in falhas if t not in cotacoes_hgbrasil]
        if falhas:
            print(f"[atualizar] Aviso: sem cotação para {', '.join(falhas)} nesta tentativa.")

    taxas_economicas = market_data.buscar_taxas_economicas()
    if taxas_economicas is not None:
        dados["taxasEconomicas"] = taxas_economicas

    # 3. Proventos anunciados pela B3 (autolimitado a 1x/dia).
    _atualizar_proventos_b3_sem_tela(dados)

    # 4. Snapshot de patrimônio para o gráfico de Evolução.
    _registrar_snapshot(dados, ibov)

    # 5. Alertas de preço-alvo por WhatsApp.
    enviados = 0
    if notificacoes_configuradas() and dados.get("alertas"):
        tickers_atualizados = [t for t in tickers if t not in falhas]
        cotacao_por_ticker = {
            t: dados["cotacoes"][t]["preco"] for t in tickers_atualizados if t in dados["cotacoes"]
        }
        enviados = verificar_e_notificar_alertas(dados, cotacao_por_ticker)
        if enviados:
            plural = "s" if enviados > 1 else ""
            print(f"[atualizar] {enviados} alerta{plural} de preço enviado{plural} por WhatsApp.")

    # 6. Salva tudo — local (efêmero, sem efeito real neste ambiente) e no
    # Firestore, que é o que o PC e o celular realmente leem.
    salvar_dados(dados)

    # 7. Snapshot resumido pro celular ler em tempo real.
    if cloud_sync.sincronizacao_configurada():
        sincronizado = cloud_sync.sincronizar_snapshot(montar_snapshot_para_celular(dados))
        status = "ok" if sincronizado else "falhou (sem internet ou chave inválida)"
        print(f"[atualizar] Sincronização com o celular: {status}.")

    print("[atualizar] Execução concluída com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
