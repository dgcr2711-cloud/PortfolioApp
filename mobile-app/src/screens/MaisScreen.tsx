import React, { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { SegmentedControl } from '../components/SegmentedControl';
import { cores, espacamento } from '../theme';
import { useEspacoTopo } from '../hooks/useEspacoTopo';
import { ProventosScreen } from './ProventosScreen';
import { PrecoTetoScreen } from './PrecoTetoScreen';
import { EvolucaoScreen } from './EvolucaoScreen';
import { ImpostoRendaScreen } from './ImpostoRendaScreen';
import { SecaoSeguranca } from './SecaoSeguranca';
import { TeseScreen } from './TeseScreen';

type SubAba = 'proventos' | 'precoTeto' | 'evolucao' | 'impostoRenda' | 'tese' | 'seguranca';

/**
 * Junta Proventos, Preço Teto, Evolução e Imposto de Renda numa aba só
 * ("Mais"), alternando por um controle segmentado — mesma ideia da aba
 * Compras, pra manter a barra inferior com só 5 ícones mesmo com mais
 * funcionalidades.
 */
export function MaisScreen() {
  const [subAba, setSubAba] = useState<SubAba>('proventos');
  const espacoTopo = useEspacoTopo(espacamento.lg);

  return (
    <View style={estilos.container}>
      <View style={[estilos.seletor, { paddingTop: espacoTopo }]}>
        <SegmentedControl
          opcoes={[
            { valor: 'proventos', rotulo: '📅 Proventos' },
            { valor: 'precoTeto', rotulo: '🎯 Preço Teto' },
            { valor: 'evolucao', rotulo: '📊 Evolução' },
            { valor: 'impostoRenda', rotulo: '🏛️ IR' },
            { valor: 'tese', rotulo: '📓' },
            { valor: 'seguranca', rotulo: '🔒' },
          ]}
          selecionada={subAba}
          aoSelecionar={setSubAba}
        />
      </View>
      <View style={estilos.conteudo}>
        {subAba === 'proventos' && <ProventosScreen />}
        {subAba === 'precoTeto' && <PrecoTetoScreen />}
        {subAba === 'evolucao' && <EvolucaoScreen />}
        {subAba === 'impostoRenda' && <ImpostoRendaScreen />}
        {subAba === 'tese' && <TeseScreen />}
        {subAba === 'seguranca' && <SecaoSeguranca />}
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp },
  seletor: { paddingHorizontal: espacamento.lg, paddingBottom: espacamento.sm },
  conteudo: { flex: 1 },
});
