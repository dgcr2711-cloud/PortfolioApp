import React from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';
import { usePortfolioSnapshot } from '../hooks/usePortfolioSnapshot';
import { Expansor } from '../components/Expansor';
import { GraficoLinhaSvg } from '../components/GraficoLinhaSvg';
import { cores, espacamento } from '../theme';
import { formatarDataCompacta, formatarMoeda, formatarPct } from '../format';
import type { PontoHistorico, Risco } from '../types';

/**
 * Espelha a aba 📊 Evolução do PC: patrimônio ao longo do tempo e o
 * comparativo com o Ibovespa (TWR aproximado).
 *
 * 2026-09-04 (Diego reportou "o gráfico está muito ruim, fazer um
 * semelhante ao do site"): três mudanças —
 *   1. O gráfico de patrimônio trocou o desenho manual com `<View>`
 *      giradas (`GraficoLinhaPatrimonio`, sem nenhuma lib) por
 *      `GraficoLinhaSvg` (react-native-svg, já usado no donut de
 *      Alocação) — linha + sombra em degradê sob "Total Atual", no
 *      mesmo espírito visual do gráfico do site.
 *   2. A lista de snapshots com barrinhas no fim da aba (`BarraSnapshot`)
 *      foi removida — Diego apontou que não tinha necessidade (o gráfico
 *      acima já mostra a tendência, e é exatamente essa a mesma estrutura
 *      do site: gráfico → comparativo → risco, sem nenhuma lista de
 *      snapshots embaixo).
 *   3. A seção de Risco da Carteira ganhou a MESMA explicação em texto
 *      que o site já tinha (`st.expander("O que isso significa?")`,
 *      ui/evolucao.py), agora dentro de um `Expansor` fechado por padrão
 *      — e os valores de Beta/Sharpe ganharam uma cor explícita
 *      (`cores.texto`), que faltava antes (o texto ficava sem cor
 *      definida, ilegível sobre o fundo escuro do card).
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
  const historico = snapshot.historico ?? [];
  const comparativo = snapshot.twrVsIbovespa ?? null;
  const risco = snapshot.risco ?? null;

  return (
    <ScrollView style={estilos.container} contentContainerStyle={estilos.lista}>
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
          Período: {formatarDataCompacta(comparativo.dataInicio)} até {formatarDataCompacta(comparativo.dataFim)}
        </Text>
      )}

      <Text style={estilos.subtitulo}>Patrimônio ao longo do tempo</Text>
      <View style={estilos.legendaBarras}>
        <LegendaCor cor={cores.positivo} texto="Total Atual" />
        <LegendaCor cor={cores.neutro} texto="Total Investido" />
      </View>
      <GraficoPatrimonio historico={historico} />

      <Text style={estilos.subtitulo}>📐 Risco da Carteira (Beta e Sharpe)</Text>
      <BlocoRisco risco={risco} />
    </ScrollView>
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

function GraficoPatrimonio({ historico }: { historico: PontoHistorico[] }) {
  if (historico.length < 2) {
    return (
      <Text style={estilos.aviso}>
        Atualize as cotações em ao menos 2 dias diferentes para ver o gráfico de evolução aqui.
      </Text>
    );
  }

  return (
    <GraficoLinhaSvg
      series={[
        { valores: historico.map((h) => h.totalAtual), cor: cores.positivo, preencher: true },
        { valores: historico.map((h) => h.totalInvestido), cor: cores.neutro, tracejada: true },
      ]}
      rotulosX={historico.map((h) => formatarDataCompacta(h.data))}
      altura={170}
      formatarValor={formatarMoeda}
    />
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
    <>
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

      <Expansor titulo="O que isso significa?">
        <Text style={estilos.textoExplicacao}>
          <Text style={estilos.negrito}>Beta</Text>: o quanto a carteira costuma se mover em relação ao Ibovespa. 1 = se
          move junto; acima de 1 = mais volátil que o mercado; abaixo de 1 = menos volátil; negativo = tende a se mover
          na direção oposta (raro).
        </Text>
        <Text style={[estilos.textoExplicacao, { marginTop: espacamento.sm }]}>
          <Text style={estilos.negrito}>Sharpe</Text>: retorno em excesso sobre a taxa livre de risco, dividido pela
          volatilidade da carteira. Quanto maior, melhor o retorno obtido por unidade de risco assumido — não é a mesma
          coisa que "quanto rendeu".
        </Text>
      </Expansor>
    </>
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
  valorComparativo: { fontSize: 20, fontWeight: '700', marginTop: 4, color: cores.texto },
  legendaPeriodo: { color: cores.textoApagado, fontSize: 11, marginTop: espacamento.sm },
  legendaBarras: { flexDirection: 'row', gap: espacamento.lg, marginBottom: espacamento.sm },
  itemLegenda: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  pontoLegenda: { width: 8, height: 8, borderRadius: 4 },
  textoLegenda: { color: cores.textoSecundario, fontSize: 11 },
  textoExplicacao: { color: cores.textoSecundario, fontSize: 12, lineHeight: 18 },
  negrito: { fontWeight: '700', color: cores.texto },
});
