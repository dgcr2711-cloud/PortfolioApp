/**
 * Escuta o documento do Firestore em tempo real (onSnapshot) — assim que o
 * PC clica em "Atualizar Dados" e envia um novo retrato, o celular atualiza
 * a tela sozinho, sem precisar puxar pra atualizar.
 */
import { useEffect, useState } from 'react';
import { doc, onSnapshot } from 'firebase/firestore';
import { db, COLECAO_FIRESTORE, DOCUMENTO_FIRESTORE } from '../firebase';
import type { PortfolioSnapshot } from '../types';

interface EstadoSnapshot {
  snapshot: PortfolioSnapshot | null;
  carregando: boolean;
  erro: string | null;
}

export function usePortfolioSnapshot(): EstadoSnapshot {
  const [estado, setEstado] = useState<EstadoSnapshot>({ snapshot: null, carregando: true, erro: null });

  useEffect(() => {
    const referenciaDocumento = doc(db, COLECAO_FIRESTORE, DOCUMENTO_FIRESTORE);

    const cancelarInscricao = onSnapshot(
      referenciaDocumento,
      (documento) => {
        if (!documento.exists()) {
          setEstado({
            snapshot: null,
            carregando: false,
            erro: 'Nenhum dado sincronizado ainda. Abra o app no PC e clique em "🔄 Atualizar Dados" pelo menos uma vez.',
          });
          return;
        }
        setEstado({ snapshot: documento.data() as PortfolioSnapshot, carregando: false, erro: null });
      },
      (erro) => {
        setEstado({ snapshot: null, carregando: false, erro: `Não foi possível conectar: ${erro.message}` });
      }
    );

    return () => cancelarInscricao();
  }, []);

  return estado;
}
