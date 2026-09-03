declare module 'react-native-svg' {
  import { Component } from 'react';
  import { ViewStyle } from 'react-native';

  export interface SvgProps {
    width?: number | string;
    height?: number | string;
    viewBox?: string;
    style?: ViewStyle | ViewStyle[];
    children?: any;
  }

  export default class Svg extends Component<SvgProps> {}

  export interface CircleProps {
    cx?: number | string;
    cy?: number | string;
    r?: number | string;
    stroke?: string;
    strokeWidth?: number | string;
    strokeDasharray?: string | number[];
    strokeDashoffset?: number | string;
    strokeLinecap?: 'butt' | 'round' | 'square';
    fill?: string;
  }

  export class Circle extends Component<CircleProps> {}
  export class G extends Component<any> {}
  export class Path extends Component<any> {}
  export class Rect extends Component<any> {}
  export class Text extends Component<any> {}
}
