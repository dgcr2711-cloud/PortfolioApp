import React, { createContext, useContext, useState } from 'react';

interface OcultarValoresContextType {
  ocultarValores: boolean;
  alternarOcultarValores: () => void;
}

const OcultarValoresContext = createContext<OcultarValoresContextType | undefined>(undefined);

/**
 * Espelha o toggle "👁️ Ocultar valores" da barra lateral do PC — lá é um
 * `st.toggle` guardado em `st.session_state`; aqui é um Context do React,
 * compartilhado por todas as telas, pra dar pra ligar/desligar de qualquer
 * aba sem precisar navegar até uma tela de configurações. Não precisa
 * persistir em disco: assim como no PC (que reseta ao reiniciar o app), o
 * valor volta a "mostrando" toda vez que o app do celular é reaberto —
 * pensado pra ligar na hora de mostrar a tela pra alguém, não como uma
 * preferência permanente.
 */
export function OcultarValoresProvider({ children }: { children: React.ReactNode }) {
  const [ocultarValores, setOcultarValores] = useState(false);

  function alternarOcultarValores() {
    setOcultarValores((atual) => !atual);
  }

  return (
    <OcultarValoresContext.Provider value={{ ocultarValores, alternarOcultarValores }}>
      {children}
    </OcultarValoresContext.Provider>
  );
}

export function useOcultarValores(): OcultarValoresContextType {
  const contexto = useContext(OcultarValoresContext);
  if (!contexto) {
    throw new Error('useOcultarValores precisa ser usado dentro de um OcultarValoresProvider');
  }
  return contexto;
}
