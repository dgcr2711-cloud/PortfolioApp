import React, { createContext, useContext, useEffect, useState } from 'react';
import { onAuthStateChanged, signInWithEmailAndPassword, signOut } from 'firebase/auth';
import { auth } from '../firebase';

/**
 * Login de e-mail/senha do Firebase (upgrade de segurança sobre o login
 * anônimo anterior — ver README_MOBILE.md, seção "login com e-mail e
 * senha"). Só existe UMA conta de verdade: a sua, criada por você mesmo no
 * Console do Firebase (Authentication → Users). As regras do Firestore
 * agora travam por `request.auth.uid == '<seu UID>'`, não só por "algum
 * login qualquer" — então só quem sabe o seu e-mail E a sua senha consegue
 * ler os dados, diferente do login anônimo (que qualquer pessoa conseguia
 * "criar" sozinha).
 *
 * A sessão fica salva no aparelho (mesmo AsyncStorage de antes, configurado
 * em src/firebase.ts) — você loga uma vez e o app lembra depois disso, até
 * você tocar em "Sair" (Mais → 🔒) ou desinstalar o app.
 *
 * Enquanto ninguém estiver logado, a navegação e as telas da carteira não
 * chegam a montar — mesmo princípio já usado pela trava de PIN — assim
 * nenhuma tela tenta ler o Firestore antes da hora.
 */

interface AuthContextType {
  carregando: boolean;
  autenticado: boolean;
  entrar: (email: string, senha: string) => Promise<void>;
  sair: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [carregando, setCarregando] = useState(true);
  const [autenticado, setAutenticado] = useState(false);

  useEffect(() => {
    // onAuthStateChanged dispara assim que a sessão salva no aparelho (se
    // houver) é restaurada — por isso não existe nenhum "login automático"
    // aqui: se não houver sessão salva, o usuário fica null e a TelaLogin
    // é quem assume a partir daí.
    const cancelarInscricao = onAuthStateChanged(auth, (usuario) => {
      setAutenticado(!!usuario);
      setCarregando(false);
    });

    return () => cancelarInscricao();
  }, []);

  async function entrar(email: string, senha: string): Promise<void> {
    await signInWithEmailAndPassword(auth, email.trim(), senha);
  }

  async function sair(): Promise<void> {
    await signOut(auth);
  }

  return (
    <AuthContext.Provider value={{ carregando, autenticado, entrar, sair }}>{children}</AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const contexto = useContext(AuthContext);
  if (!contexto) {
    throw new Error('useAuth precisa ser usado dentro de um AuthProvider');
  }
  return contexto;
}
