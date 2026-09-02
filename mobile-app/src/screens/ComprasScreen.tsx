import React, { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { SegmentedControl } from '../components/SegmentedControl';
import { cores, espacamento } from '../theme';
import { useEspacoTopo } from '../hooks/useEspacoTopo';
import { NovaCompraScreen } from './NovaCompraScreen';
import { HistoricoScreen } from './HistoricoScreen';

type SubAba = 'nova' | 'historico';

/**
 * Junta "Nova Compra" e "Histórico" numa aba só, alternando por um
 * controle segmentado — evita ter que espremer mais um ícone na barra
 * inferior a cada nova funcionalidade que o app do celular ganha.
 */
export function ComprasScreen() {
  const [subAba, setSubAba] = useState<SubAba>('nova');
  const espacoTopo = useEspacoTopo(espacamento.lg);

  return (
    <View style={estilos.container}>
      <View style={[estilos.seletor, { paddingTop: espacoTopo }]}>
        <SegmentedControl
          opcoes={[
            { valor: 'nova', rotulo: '➕ Nova' },
            { valor: 'historico', rotulo: '🧾 Histórico' },
          ]}
          selecionada={subAba}
          aoSelecionar={setSubAba}
        />
      </View>
      <View style={estilos.conteudo}>
        {subAba === 'nova' ? <NovaCompraScreen /> : <HistoricoScreen />}
      </View>
    </View>
  );
}

const estilos = StyleSheet.create({
  container: { flex: 1, backgroundColor: cores.fundoApp },
  seletor: { paddingHorizontal: espacamento.lg, paddingBottom: espacamento.sm },
  conteudo: { flex: 1 },
});
