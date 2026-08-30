// Stub mínimo de React só para o harness de verificação (tsc --strict) rodar
// neste sandbox, onde `npm install` não funciona (registry bloqueado). NÃO é
// shipado com o app — o app real usa os @types/react de verdade via npm.
//
// Limitação conhecida: como este stub não replica o mecanismo real de
// "LibraryManagedAttributes" do React para JSX, o tsc acusa falsamente
// "Property 'children' is missing" em componentes que recebem children via
// JSX aninhado (em vez de via prop explícita). Isso é um falso-positivo do
// harness — não do código — reconhecível porque aparece igual em arquivos
// já revisados e inalterados (ex: NovaCompraScreen.tsx).
declare namespace React {
  type ReactNode = any;
  type FC<P = any> = (props: P) => any;
  type Dispatch<A> = (value: A) => void;
  type SetStateAction<S> = S | ((prevState: S) => S);
}

declare module 'react' {
  export type ReactNode = React.ReactNode;
  export type FC<P = any> = React.FC<P>;
  export type Dispatch<A> = React.Dispatch<A>;
  export type SetStateAction<S> = React.SetStateAction<S>;

  export function useState<S>(initial: S | (() => S)): [S, Dispatch<SetStateAction<S>>];
  export function useEffect(effect: () => void | (() => void), deps?: any[]): void;
  export function useRef<T>(initial: T): { current: T };
  export function useMemo<T>(factory: () => T, deps: any[]): T;
  export interface Context<T> {
    Provider: FC<{ value: T; children?: ReactNode }>;
    Consumer: FC<{ children: (value: T) => ReactNode }>;
  }
  export function createContext<T>(defaultValue: T): Context<T>;
  export function useContext<T>(context: Context<T>): T;

  const ReactDefault: {
    createElement: (...args: any[]) => any;
  };
  export default ReactDefault;
}
