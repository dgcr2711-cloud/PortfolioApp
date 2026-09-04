import React, { useState } from 'react';
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { cores, espacamento } from '../theme';
import { useEspacoTopo } from '../hooks/useEspacoTopo';
import { ProventosScreen } from './ProventosScreen';
import { PrecoTetoScreen } from './PrecoTetoScreen';
import { EvolucaoScreen } from './EvolucaoScreen';
import { ImpostoRendaScreen } from './ImpostoRendaScreen';
import { SecaoSeguranca } from './SecaoSeguranca';
import { TeseScreen } from './TeseScreen';

type SubAba = 'proventos' | 'precoTeto' | 'evolucao' | 'impostoRenda' | 'tese' | 'seguranca';

type ItemMenu = { valor: SubAba; icone: string; rotulo: string; componente: React.FC };

const ITENS: ItemMenu[] = [
  { valor: 'proventos', icone: '📅', rotulo: 'Proventos', componente: ProventosScreen },
  { valor: 'precoTeto', icone: '🎯', rotulo: 'Preço Teto', componente: PrecoTetoScreen },
  { valor: 'evolucao', icone: '📊', rotulo: 'Evolução', componente: EvolucaoScreen },
  { valor: 'impostoRenda', icone: '🏛️', rotulo: 'Imposto de Renda', componente: ImpostoRendaScreen },
  { valor: 'tese', icone: '📓', rotulo: 'Diário de Tese', componente: TeseScreen },
  { valor: 'seguranca', icone: '🔒', rotulo: 'Segurança', componente: SecaoSeguranca },
];

/**
 * Junta Proventos, Preço Teto, Evolução, Imposto de Renda, Diário de Tese e
 * Segurança numa aba só ("Mais") — evita ter que espremer mais um ícone na
 * barra inferior a cada nova funcionalidade que o app do celular ganha.
 *
 * 2026-09-04 (Diego reportou "a última aba está muito bagunçada"): até
 * então, essas 6 seções dividiam um único `SegmentedControl` em 6 fatias
 * na MESMA linha — o componente foi desenhado pra 2-3 opções (é o que a
 * aba "Compras" usa, e continua funcionando bem lá — ver
 * `ui/carteira`-style docstring do próprio SegmentedControl), então com 6
 * os rótulos ("📅 Proventos", "🎯 Preço Teto" etc.) ficavam espremidos e
 * cortados numa tela de celular. Trocado por um menu de 2 níveis, padrão
 * comum em apps de verdade pra uma aba "Mais": uma lista vertical de
 * cards (ícone + nome + seta), e ao tocar, a seção abre em tela cheia com
 * um cabeçalho "‹ Mais" no topo pra voltar — mesmo espírito de
 * "divulgação progressiva" já usado no app do PC (os `st.expander`).
 * Nenhuma das 6 telas (ProventosScreen etc.) precisou mudar — todas já
 * assumiam ser renderizadas abaixo de algum cabeçalho, sem cuidar da área
 * seura do topo sozinhas.
 */
export function MaisScreen() {
  const [selecionada, setSelecionada] = useState<SubAba | null>(null);
  const espacoTopo = useEspacoTopo(espacamento.lg);

  const item = ITENS.find((i) => i.valor === selecionada);

  if (item) {
    const Tela = item.componente;
    return (
      <View style={estilos.container}>
        <View style={[estilos.cabecalho, { paddingTop: espacoTopo }]}>
          <TouchableOpacity
            onPress={() => setSelecionada(null)}
            style={estilos.botaoVoltar}
            hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          >
            <Text style={estilos.textoVoltar}>‹ Mais</Text>
          </TouchableOpacity>
          <Text style={estilos.tituloSecao} numberOfLines={1}>
            {item.icone} {item.rotulo}
          </Text>
        </View>
        <View style={estilos.conteudo}>
          <Tela />
        </View>
      </View>
    );
  }

  return (
    <ScrollView style={estilos.container} contentContainerStyle={[estilos.menu, { paddingTop: espacoTopo }]}>
      <Text style={estilos.titulo}>Mais</Text>
      <Text style={estilos.legenda}>Outras seções da sua carteira</Text>
      {ITENS.map((i) => (
        <TouchableOpacity
          key={i.valor}
          style={estilos.cardItem}
          onPress={() => setSelecionada(i.valor)}
          activeOpacity={0.7}
        >
          <Text style={estilos.iconeItem}>{i.icone}</Text>
          <Text style={estilos.rotuloItem}>{i.rotulo}</Text>
          <Text style={estilos.seta}>›</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp },
  menu: { paddingHorizontal: espacamento.lg, paddingBottom: espacamento.xl },
  titulo: { color: cores.texto, fontSize: 26, fontWeight: '700' },
  legenda: { color: cores.textoApagado, fontSize: 12, marginTop: 2, marginBottom: espacamento.lg },
  cardItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: cores.fundoCard,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: cores.borda,
    paddingVertical: espacamento.md,
    paddingHorizontal: espacamento.lg,
    marginBottom: espacamento.sm,
  },
  iconeItem: { fontSize: 20, marginRight: espacamento.md },
  rotuloItem: { flex: 1, color: cores.texto, fontSize: 15, fontWeight: '600' },
  seta: { color: cores.textoSecundario, fontSize: 18 },
  cabecalho: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: espacamento.lg,
    paddingBottom: espacamento.md,
    gap: espacamento.md,
  },
  botaoVoltar: { paddingVertical: 4, paddingRight: 4 },
  textoVoltar: { color: cores.destaque, fontSize: 15, fontWeight: '600' },
  tituloSecao: { flex: 1, color: cores.texto, fontSize: 17, fontWeight: '700' },
  conteudo: { flex: 1 },
});
