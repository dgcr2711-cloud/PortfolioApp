// Stub mínimo de firebase/auth para o harness de verificação — ver nota em
// ../react/index.d.ts. Só a API realmente usada no projeto (login com
// e-mail/senha + persistência em React Native via AsyncStorage), com o
// mesmo formato baseado em Promises/callbacks da biblioteca real.
declare module 'firebase/auth' {
  export interface User {
    uid: string;
  }
  export interface Auth {
    currentUser: User | null;
  }
  export function initializeAuth(app: any, options?: { persistence?: any }): Auth;
  export function getAuth(app: any): Auth;
  export function getReactNativePersistence(storage: any): any;
  export function signInAnonymously(auth: Auth): Promise<{ user: User }>;
  export function signInWithEmailAndPassword(auth: Auth, email: string, senha: string): Promise<{ user: User }>;
  export function signOut(auth: Auth): Promise<void>;
  export function onAuthStateChanged(auth: Auth, onNext: (usuario: User | null) => void): () => void;
}
