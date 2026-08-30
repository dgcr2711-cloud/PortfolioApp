import React, { useState } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { usePortfolioSnapshot } from '../hooks/usePortfolioSnapshot';
import { Badge, BadgeIndicacao } from '../components/Badge';
import { BotaoOcultarValores } from '../components/BotaoOcultarValores';
import { useOcultarValores } from '../contexts/OcultarValoresContext';
import { cores, espacamento } from '../theme';
import { formatarMoeda, formatarMoedaPriv, formatarPct, mascararQtd } from '../format';
import type { Ativo, Rebalanceamento } from '../types';

/**
 * Espelha a aba "📈 Carteira" — lista de posições + empresas-alvo.
 *
 * Cada ativo é uma "lâmina": por padrão aparece só uma linha compacta
 * (ticker + o número que mais importa de relance), e expande com um toque
 * para mostrar todos os campos (Cotação, Preço Teto, Qtd, Preço Médio
 * etc.) — pedido explícito pra economizar espaço com carteiras de vários
 * ativos, sem esconder nenhuma informação que já existia.
 */
export function CarteiraScreen() {
  const { snapshot, carregando, erro } = usePortfolioSnapshot();
  const [expandidos, setExpandidos] = useState<Set<string>>(new Set());

  function alternar(ticker: string) {
    setExpandidos((atual) => {
      const novo = new Set(atual);
      if (novo.has(ticker)) {
        novo.delete(ticker);
      } else {
        novo.add(ticker);
      }
      return novo;
    });
  }

  if (carregando) {
    return (
      <View style={estilos.centralizado}>
        <ActivityIndicator color={cores.destaque} size="large" />
      </View>
    );
  }

  if (erro || !snapshot) {
    return (
      <View style={estilos.centralizado}>
        <Text style={estilos.textoErro}>{erro ?? 'Sem dados.'}</Text>
      </View>
    );
  }

  return (
    <View style={estilos.container}>
      <View style={estilos.linhaTitulo}>
        <Text style={estilos.titulo}>Carteira</Text>
        <View style={estilos.acoesTopo}>
          <TouchableOpacity onPress={() => setExpandidos(new Set(snapshot.ativos.map((a) => a.ticker)))}>
            <Text style={estilos.linkAcao}>Expandir tudo</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => setExpandidos(new Set())}>
            <Text style={estilos.linkAcao}>Recolher</Text>
          </TouchableOpacity>
          <BotaoOcultarValores />
        </View>
      </View>
      <FlatList
        data={snapshot.ativos}
        keyExtractor={(item) => item.ticker}
        contentContainerStyle={estilos.lista}
        ListHeaderComponent={<BlocoRebalanceamento rebalanceamento={snapshot.rebalanceamento ?? null} />}
        renderItem={({ item }) => (
          <CartaoAtivo ativo={item} expandido={expandidos.has(item.ticker)} aoAlternar={() => alternar(item.ticker)} />
        )}
      />
    </View>
  );
}

/**
 * Espelha a seção "🎯 Metas de Alocação & Rebalanceamento" da aba Carteira
 * do PC — mesmos desvios já calculados no snapshot (core/rebalanceamento.py),
 * nenhuma conta refeita aqui. Quem define as metas continua sendo o PC:
 * o celular só mostra o resultado.
 */
function BlocoRebalanceamento({ rebalanceamento }: { rebalanceamento: Rebalanceamento | null }) {
  const { ocultarValores } = useOcultarValores();

  if (!rebalanceamento || !rebalanceamento.temMetas) {
    return null; // sem metas definidas -> nada a mostrar, sem poluir a tela com um aviso permanente
  }

  return (
    <View style={estilos.blocoRebalanceamento}>
      <Text style={estilos.tituloRebalanceamento}>🎯 Metas de Alocação</Text>
      {rebalanceamento.desvios.map((d) => {
        const acao = d.valorAjuste < 0 ? 'Vender' : 'Comprar';
        const sinal = d.desvioPp >= 0 ? '+' : '';
        return (
          <View key={d.ticker} style={estilos.linhaRebalanceamento}>
            <View style={estilos.blocoTickerRebalanceamento}>
              <Text style={estilos.tickerRebalanceamento}>{d.ticker}</Text>
              <Text style={estilos.detalheRebalanceamento}>
                Meta {formatarPct(d.metaPct)} · Atual {formatarPct(d.atualPct)} ({sinal}
                {d.desvioPp.toFixed(1)} p.p.)
              </Text>
              <Text style={estilos.sugestaoRebalanceamento}>
                {acao} {formatarMoedaPriv(Math.abs(d.valorAjuste), ocultarValores)}
              </Text>
            </View>
            <Badge texto={d.alerta ? '⚠️ Rebalancear' : 'OK'} tipo={d.alerta ? 'warn' : 'ok'} />
          </View>
        );
      })}
    </View>
  );
}

function CartaoAtivo({
  ativo,
  expandido,
  aoAlternar,
}: {
  ativo: Ativo;
  expandido: boolean;
  aoAlternar: () => void;
}) {
  const { ocultarValores } = useOcultarValores();
  const corResultado = (ativo.lucroReais ?? 0) >= 0 ? cores.positivo : cores.negativo;
  const sinal = (ativo.lucroReais ?? 0) >= 0 ? '+' : '';

  return (
    <TouchableOpacity
      activeOpacity={0.7}
      onPress={aoAlternar}
      style={[estilos.cartao, ativo.ehAlvo && estilos.cartaoAlvo]}
    >
      <View style={estilos.linhaTopo}>
        <View style={estilos.blocoTicker}>
          <Text style={estilos.seta}>{expandido ? '▾' : '▸'}</Text>
          <Text style={estilos.ticker}>
            {ativo.ticker} {ativo.ehAlvo ? '🎯' : ''}
          </Text>
        </View>

        {!expandido && (
          <View style={estilos.resumoColapsado}>
            {ativo.ehAlvo ? (
              <BadgeIndicacao indicacao={ativo.indicacao} />
            ) : (
              <>
                <Text style={estilos.valorResumo}>{formatarMoedaPriv(ativo.atual, ocultarValores)}</Text>
                <Text style={[estilos.valorResumoSecundario, { color: corResultado }]}>
                  {sinal}
                  {formatarPct(ativo.lucroPct)}
                </Text>
              </>
            )}
          </View>
        )}
      </View>

      {expandido && (
        <>
          <View style={estilos.linhaSetorBadge}>
            {ativo.setor ? <Text style={estilos.setor}>{ativo.setor}</Text> : <View />}
            <BadgeIndicacao indicacao={ativo.indicacao} />
          </View>

          <View style={estilos.grade}>
            <Campo rotulo="Cotação" valor={formatarMoeda(ativo.cotacaoAtual)} />
            <Campo rotulo="Preço Teto" valor={ativo.precoTeto ? formatarMoeda(ativo.precoTeto) : '— sem preço teto'} />
            {!ativo.ehAlvo && (
              <>
                <Campo rotulo="Qtd" valor={mascararQtd(ativo.qtdTotal, ocultarValores)} />
                <Campo rotulo="Preço Médio" valor={formatarMoedaPriv(ativo.precoMedio, ocultarValores)} />
                <Campo rotulo="Total Atual" valor={formatarMoedaPriv(ativo.atual, ocultarValores)} />
                <Campo
                  rotulo="Resultado"
                  valor={`${sinal}${formatarMoedaPriv(ativo.lucroReais, ocultarValores)} (${sinal}${formatarPct(ativo.lucroPct)})`}
                  cor={corResultado}
                />
              </>
            )}
          </View>
        </>
      )}
    </TouchableOpacity>
  );
}

function Campo({ rotulo, valor, cor = cores.texto }: { rotulo: string; valor: string; cor?: string }) {
  return (
    <View style={estilos.campo}>
      <Text style={estilos.rotuloCampo}>{rotulo}</Text>
      <Text style={[estilos.valorCampo, { color: cor }]}>{valor}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp, paddingTop: espacamento.xl },
  centralizado: { flex: 1, backgroundColor: cores.fundoApp, alignItems: 'center', justifyContent: 'center', padding: espacamento.xl },
  textoErro: { color: cores.textoSecundario, textAlign: 'center', fontSize: 14 },
  linhaTitulo: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: espacamento.lg,
    marginBottom: espacamento.md,
  },
  titulo: { color: cores.texto, fontSize: 26, fontWeight: '700' },
  acoesTopo: { flexDirection: 'row', alignItems: 'center', gap: espacamento.md },
  linkAcao: { color: cores.destaque, fontSize: 12, fontWeight: '600' },
  lista: { paddingHorizontal: espacamento.lg, paddingBottom: espacamento.xl },
  cartao: {
    backgroundColor: cores.fundoCard,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.lg,
    marginBottom: espacamento.sm,
  },
  cartaoAlvo: { borderLeftWidth: 3, borderLeftColor: cores.info },
  linhaTopo: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  blocoTicker: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  seta: { color: cores.textoApagado, fontSize: 12 },
  ticker: { color: cores.texto, fontSize: 16, fontWeight: '700' },
  resumoColapsado: { flexDirection: 'row', alignItems: 'baseline', gap: 8 },
  valorResumo: { color: cores.texto, fontSize: 14, fontWeight: '700' },
  valorResumoSecundario: { fontSize: 12, fontWeight: '600' },
  linhaSetorBadge: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: espacamento.sm,
  },
  setor: { color: cores.textoSecundario, fontSize: 11 },
  grade: { flexDirection: 'row', flexWrap: 'wrap', gap: espacamento.md, marginTop: espacamento.md },
  campo: { minWidth: '40%' },
  rotuloCampo: { color: cores.textoApagado, fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.3 },
  valorCampo: { fontSize: 14, fontWeight: '600', marginTop: 2 },
  blocoRebalanceamento: {
    backgroundColor: cores.fundoCard,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: cores.borda,
    padding: espacamento.lg,
    marginBottom: espacamento.md,
  },
  tituloRebalanceamento: { color: cores.destaque, fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: espacamento.sm },
  linhaRebalanceamento: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: espacamento.xs,
    borderTopWidth: 1,
    borderTopColor: cores.borda,
  },
  blocoTickerRebalanceamento: { flex: 1, paddingRight: espacamento.sm },
  tickerRebalanceamento: { color: cores.texto, fontSize: 14, fontWeight: '700' },
  detalheRebalanceamento: { color: cores.textoSecundario, fontSize: 11, marginTop: 2 },
  sugestaoRebalanceamento: { color: cores.textoApagado, fontSize: 11, marginTop: 2, fontWeight: '600' },
});
