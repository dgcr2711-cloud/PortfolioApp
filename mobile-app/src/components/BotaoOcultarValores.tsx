import React from 'react';
import { StyleSheet, Text, TouchableOpacity } from 'react-native';
import { useOcultarValores } from '../contexts/OcultarValoresContext';
import { cores } from '../theme';

/**
 * Botão pequeno (ícone de olho) repetido no topo das telas que mostram
 * valores em R$ — mesma função do toggle "👁️ Ocultar valores" da barra
 * lateral do PC, útil pra quando o Diego quiser mostrar o app pra alguém
 * (mostrar o trabalho) sem expor quanto ele tem investido.
 */
export function BotaoOcultarValores() {
  const { ocultarValores, alternarOcultarValores } = useOcultarValores();
  return (
    <TouchableOpacity
      style={estilos.botao}
      onPress={alternarOcultarValores}
      hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
      accessibilityLabel={ocultarValores ? 'Mostrar valores' : 'Ocultar valores'}
    >
      <Text style={estilos.icone}>{ocultarValores ? '🙈' : '👁️'}</Text>
    </TouchableOpacity>
  );
}

const estilos = StyleSheet.create({
  botao: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: cores.fundoCard,
    borderWidth: 1,
    borderColor: cores.borda,
    alignItems: 'center',
    justifyContent: 'center',
  },
  icone: { fontSize: 16 },
});
