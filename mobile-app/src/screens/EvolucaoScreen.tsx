import React, { useState } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from 'react-native';
import { usePortfolioSnapshot } from '../hooks/usePortfolioSnapshot';
import { cores, espacamento } from '../theme';
import { formatarData, formatarMoeda, formatarPct } from '../format';
import type { PontoHistorico, Risco } from '../types';

/**
 * Espelha a aba 📊 Evolução do PC: patrimônio ao longo do tempo e o
 * comparativo com o Ibovespa (TWR aproximado).
 *
 * Além da lista de snapshots (que continua existindo, com o valor exato de
 * cada dia), agora tem um gráfico de linha do patrimônio no topo — pedido
 * explícito pra visualizar a tendência de relance, sem precisar rolar a
 * lista inteira. Construído só com <View> posicionadas e rotacionadas (o
 * mesmo truque usado em várias libs de gráfico "sem SVG"), para não
 * precisar adicionar nenhuma dependência nova (tipo react-native-svg) ao
 * projeto — o app continua exatamente com as mesmas dependências de antes.
 */
export function EvolucaoScreen() {
  const { snapshot, carregando, erro } = usePortfolioSnapshot();

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

  // Fallback pro formato antigo do snapshot (antes desta funcionalidade existir) — evita
  // tela quebrada enquanto o PC ainda não rodou "🔄 Atualizar Dados" com o código novo.
  // Já vem do PC em ordem cronológica crescente (mais antigo primeiro) — é
  // exatamente a ordem que o gráfico de linha precisa (esquerda = passado).
  const historicoBruto = snapshot.historico ?? [];
  const historico = [...historicoBruto].reverse(); // mais recente primeiro, para a lista abaixo do gráfico
  const maiorValor = Math.max(1, ...historicoBruto.map((h) => Math.max(h.totalAtual, h.totalInvestido)));
  const comparativo = snapshot.twrVsIbovespa ?? null;
  const risco = snapshot.risco ?? null;

  return (
    <FlatList
      style={estilos.container}
      contentContainerStyle={estilos.lista}
      data={historico}
      keyExtractor={(item: PontoHistorico) => item.data}
      ListHeaderComponent={
        <>
          <Text style={estilos.titulo}>Evolução Patrimonial</Text>
          <Text style={estilos.legenda}>Um snapshot é salvo automaticamente sempre que o PC atualiza cotações.</Text>

          <Text style={estilos.subtitulo}>🆚 Comparativo com o Ibovespa</Text>
          {comparativo ? (
            <View style={estilos.blocoComparativo}>
              <View style={estilos.cardComparativo}>
                <Text style={estilos.rotuloComparativo}>SUA CARTEIRA (TWR APROX.)</Text>
                <Text style={[estilos.valorComparativo, { color: comparativo.rentCarteiraPct >= 0 ? cores.positivo : cores.negativo }]}>
                  {formatarPct(comparativo.rentCarteiraPct)}
                </Text>
              </View>
              <View style={estilos.cardComparativo}>
                <Text style={estilos.rotuloComparativo}>IBOVESPA NO PERÍODO</Text>
                <Text style={[estilos.valorComparativo, { color: comparativo.rentIbovPct >= 0 ? cores.positivo : cores.negativo }]}>
                  {formatarPct(comparativo.rentIbovPct)}
                </Text>
              </View>
            </View>
          ) : (
            <Text style={estilos.aviso}>Atualize as cotações em ao menos 2 dias diferentes para ver este comparativo.</Text>
          )}
          {comparativo && (
            <Text style={estilos.legendaPeriodo}>
              Período: {formatarData(comparativo.dataInicio)} até {formatarData(comparativo.dataFim)}
            </Text>
          )}

          <Text style={estilos.subtitulo}>Patrimônio ao longo do tempo</Text>
          <View style={estilos.legendaBarras}>
            <LegendaCor cor={cores.positivo} texto="Total Atual" />
            <LegendaCor cor={cores.neutro} texto="Total Investido" />
          </View>
          <GraficoLinhaPatrimonio historico={historicoBruto} />

          <Text style={estilos.subtitulo}>📐 Risco da Carteira (Beta e Sharpe)</Text>
          <BlocoRisco risco={risco} />
        </>
      }
      ListEmptyComponent={<Text style={estilos.aviso}>Ainda não há snapshots suficientes. Atualize as cotações em dias diferentes para começar a ver a evolução aqui.</Text>}
      renderItem={({ item }: { item: PontoHistorico }) => <BarraSnapshot ponto={item} maiorValor={maiorValor} />}
    />
  );
}

function LegendaCor({ cor, texto }: { cor: string; texto: string }) {
  return (
    <View style={estilos.itemLegenda}>
      <View style={[estilos.pontoLegenda, { backgroundColor: cor }]} />
      <Text style={estilos.textoLegenda}>{texto}</Text>
    </View>
  );
}

/**
 * Espelha a seção "📐 Risco da Carteira" da aba Evolução do PC — mesmo
 * cálculo (core/risco.py), já resolvido no snapshot, sem nenhuma conta
 * refeita aqui. 'risco' vem ausente/null em snapshots antigos (de antes
 * desta funcionalidade) — tratado igual a "sem dados suficientes ainda".
 */
function BlocoRisco({ risco }: { risco: Risco | null }) {
  if (!risco || risco.aviso) {
    return (
      <Text style={estilos.aviso}>
        {risco?.aviso ?? 'Atualize as cotações em ao menos 4 dias diferentes no PC para ver Beta e Sharpe aqui.'}
      </Text>
    );
  }

  return (
    <View style={estilos.blocoComparativo}>
      <View style={estilos.cardComparativo}>
        <Text style={estilos.rotuloComparativo}>BETA (VS. IBOVESPA)</Text>
        <Text style={estilos.valorComparativo}>{risco.beta !== null ? risco.beta.toFixed(2) : '—'}</Text>
      </View>
      <View style={estilos.cardComparativo}>
        <Text style={estilos.rotuloComparativo}>SHARPE (ANUALIZADO)</Text>
        <Text style={estilos.valorComparativo}>{risco.sharpeAnualizado !== null ? risco.sharpeAnualizado.toFixed(2) : '—'}</Text>
      </View>
    </View>
  );
}

// ==========================================================================
// Gráfico de linha (sem nenhuma lib de gráfico — só Views posicionadas)
// ==========================================================================

const ALTURA_GRAFICO = 150;
const TAMANHO_PONTO = 6;
const ESPESSURA_LINHA = 2;

type PontoTela = { x: number; y: number };

function GraficoLinhaPatrimonio({ historico }: { historico: PontoHistorico[] }) {
  const [largura, setLargura] = useState(0);

  if (historico.length < 2) {
    return (
      <Text style={estilos.aviso}>
        Atualize as cotações em ao menos 2 dias diferentes para ver o gráfico de evolução aqui.
      </Text>
    );
  }

  const valoresAtual = historico.map((h) => h.totalAtual);
  const valoresInvestido = historico.map((h) => h.totalInvestido);
  // Eixo Y sempre começa em 0 (nunca no menor valor da série) — do contrário
  // pequenas variações pareceriam desproporcionalmente grandes no gráfico.
  const valorMax = Math.max(...valoresAtual, ...valoresInvestido);
  const amplitude = Math.max(1, valorMax);

  function paraPontosTela(valores: number[]): PontoTela[] {
    return valores.map((valor, i) => ({
      x: (i / (historico.length - 1)) * largura,
      y: ALTURA_GRAFICO - (valor / amplitude) * ALTURA_GRAFICO,
    }));
  }

  const pontosInvestido = largura > 0 ? paraPontosTela(valoresInvestido) : [];
  const pontosAtual = largura > 0 ? paraPontosTela(valoresAtual) : [];

  return (
    <View>
      <View style={estilos.areaGrafico} onLayout={(evento: { nativeEvent: { layout: { width: number } } }) => setLargura(evento.nativeEvent.layout.width)}>
        {largura > 0 && (
          <>
            <Text style={estilos.rotuloTopoGrafico}>{formatarMoeda(valorMax)}</Text>
            <Text style={estilos.rotuloBaseGrafico}>R$ 0</Text>
            <LinhaSerie pontos={pontosInvestido} cor={cores.neutro} />
            <LinhaSerie pontos={pontosAtual} cor={cores.positivo} />
          </>
        )}
      </View>
      <View style={estilos.linhaEixoX}>
        <Text style={estilos.rotuloEixoX}>{formatarData(historico[0].data)}</Text>
        <Text style={estilos.rotuloEixoX}>{formatarData(historico[historico.length - 1].data)}</Text>
      </View>
    </View>
  );
}

function LinhaSerie({ pontos, cor }: { pontos: PontoTela[]; cor: string }) {
  return (
    <>
      {pontos.slice(0, -1).map((p1, i) => {
        const p2 = pontos[i + 1];
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const distancia = Math.sqrt(dx * dx + dy * dy);
        const angulo = (Math.atan2(dy, dx) * 180) / Math.PI;
        const meioX = (p1.x + p2.x) / 2;
        const meioY = (p1.y + p2.y) / 2;
        return (
          <View
            key={`segmento-${i}`}
            style={[
              estilos.segmentoLinha,
              {
                width: distancia,
                left: meioX - distancia / 2,
                top: meioY - ESPESSURA_LINHA / 2,
                backgroundColor: cor,
                transform: [{ rotate: `${angulo}deg` }],
              },
            ]}
          />
        );
      })}
      {pontos.map((p, i) => (
        <View
          key={`ponto-${i}`}
          style={[estilos.pontoLinha, { left: p.x - TAMANHO_PONTO / 2, top: p.y - TAMANHO_PONTO / 2, backgroundColor: cor }]}
        />
      ))}
    </>
  );
}

function BarraSnapshot({ ponto, maiorValor }: { ponto: PontoHistorico; maiorValor: number }) {
  const larguraAtual = `${Math.max(2, (ponto.totalAtual / maiorValor) * 100)}%` as const;
  const larguraInvestido = `${Math.max(2, (ponto.totalInvestido / maiorValor) * 100)}%` as const;
  const lucro = ponto.totalAtual - ponto.totalInvestido;

  return (
    <View style={estilos.cartaoSnapshot}>
      <View style={estilos.linhaTopoSnapshot}>
        <Text style={estilos.dataSnapshot}>{formatarData(ponto.data)}</Text>
        <Text style={[estilos.lucroSnapshot, { color: lucro >= 0 ? cores.positivo : cores.negativo }]}>
          {lucro >= 0 ? '+' : ''}{formatarMoeda(lucro)}
        </Text>
      </View>
      <View style={estilos.trilhaBarra}>
        <View style={[estilos.barra, { width: larguraAtual, backgroundColor: cores.positivo }]} />
      </View>
      <Text style={estilos.valorBarra}>{formatarMoeda(ponto.totalAtual)}</Text>
      <View style={estilos.trilhaBarra}>
        <View style={[estilos.barra, { width: larguraInvestido, backgroundColor: cores.neutro }]} />
      </View>
      <Text style={estilos.valorBarra}>{formatarMoeda(ponto.totalInvestido)}</Text>
    </View>
  );
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp },
  centralizado: { flex: 1, backgroundColor: cores.fundoApp, alignItems: 'center', justifyContent: 'center', padding: espacamento.xl },
  textoErro: { color: cores.textoSecundario, textAlign: 'center', fontSize: 14 },
  lista: { paddingHorizontal: espacamento.lg, paddingTop: espacamento.xl, paddingBottom: espacamento.xl },
  titulo: { color: cores.texto, fontSize: 26, fontWeight: '700' },
  legenda: { color: cores.textoApagado, fontSize: 12, marginTop: 2, marginBottom: espacamento.lg, lineHeight: 17 },
  subtitulo: { color: cores.destaque, fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.6, marginTop: espacamento.md, marginBottom: espacamento.sm },
  aviso: { color: cores.neutro, fontSize: 13, lineHeight: 19, marginBottom: espacamento.md },
  blocoComparativo: { flexDirection: 'row', gap: espacamento.sm },
  cardComparativo: { flex: 1, backgroundColor: cores.fundoCard, borderRadius: 12, borderWidth: 1, borderColor: cores.borda, padding: espacamento.md },
  rotuloComparativo: { color: cores.textoApagado, fontSize: 10, letterSpacing: 0.2 },
  valorComparativo: { fontSize: 20, fontWeight: '700', marginTop: 4 },
  legendaPeriodo: { color: cores.textoApagado, fontSize: 11, marginTop: espacamento.sm },
  legendaBarras: { flexDirection: 'row', gap: espacamento.lg, marginBottom: espacamento.sm },
  itemLegenda: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  pontoLegenda: { width: 8, height: 8, borderRadius: 4 },
  textoLegenda: { color: cores.textoSecundario, fontSize: 11 },
  areaGrafico: {
    height: ALTURA_GRAFICO,
    marginTop: espacamento.xs,
    marginBottom: espacamento.sm,
    position: 'relative',
    backgroundColor: cores.fundoCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: cores.borda,
    overflow: 'hidden',
  },
  segmentoLinha: { position: 'absolute' as const, height: ESPESSURA_LINHA, borderRadius: 1 },
  pontoLinha: { position: 'absolute' as const, width: TAMANHO_PONTO, height: TAMANHO_PONTO, borderRadius: TAMANHO_PONTO / 2 },
  rotuloTopoGrafico: { position: 'absolute' as const, top: 4, left: 6, color: cores.textoApagado, fontSize: 10 },
  rotuloBaseGrafico: { position: 'absolute' as const, bottom: 4, left: 6, color: cores.textoApagado, fontSize: 10 },
  linhaEixoX: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: espacamento.sm },
  rotuloEixoX: { color: cores.textoApagado, fontSize: 10 },
  cartaoSnapshot: { backgroundColor: cores.fundoCard, borderRadius: 12, borderWidth: 1, borderColor: cores.borda, padding: espacamento.md, marginBottom: espacamento.sm },
  linhaTopoSnapshot: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: espacamento.sm },
  dataSnapshot: { color: cores.texto, fontWeight: '600', fontSize: 13 },
  lucroSnapshot: { fontWeight: '700', fontSize: 13 },
  trilhaBarra: { height: 8, borderRadius: 4, backgroundColor: 'rgba(156,163,175,0.15)', overflow: 'hidden', marginTop: 4 },
  barra: { height: 8, borderRadius: 4 },
  valorBarra: { color: cores.textoSecundario, fontSize: 11, marginTop: 2 },
});
