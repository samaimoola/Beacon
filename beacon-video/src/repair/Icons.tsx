/** Simple line icons for the repair diagram, in Beacon's utility-line style. */
import React from 'react';
import type { IconKind } from './model';

const STROKE = '#f6f1e6';

export const JobIcon: React.FC<{ kind: IconKind; size?: number; accent: string }> = ({ kind, size = 76, accent }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" fill="none" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="32" cy="32" r="31" fill="rgba(191,227,230,0.06)" stroke="rgba(191,227,230,0.22)" />
    {kind === 'pole' && (
      <g stroke={STROKE} strokeWidth="2.4">
        <path d="M32 14 V52" strokeWidth="3.2" />
        <path d="M19 20 H45" />
        <path d="M22 20 v-3 M42 20 v-3" stroke={accent} />
        <path d="M24 52 H40" stroke="rgba(246,241,230,0.5)" />
      </g>
    )}
    {kind === 'conductor' && (
      <g stroke={STROKE} strokeWidth="2.4">
        <path d="M15 18 V50 M49 18 V50" strokeWidth="3" />
        <path d="M10 22 H20 M44 22 H54" />
        <path d="M15 22 Q32 34 49 22" stroke={accent} strokeWidth="2.6" />
      </g>
    )}
    {kind === 'transformer' && (
      <g stroke={STROKE} strokeWidth="2.4">
        <path d="M24 12 V52" strokeWidth="3" />
        <path d="M14 18 H34" />
        <rect x="31" y="27" width="16" height="20" rx="4" stroke={accent} />
        <path d="M35 27 v-4 M43 27 v-4" stroke={accent} />
        <path d="M24 34 H31" />
      </g>
    )}
  </svg>
);

/** Crew truck glyph (from the app's crew marker), sized for the crew pool. */
export const CrewTruck: React.FC<{ fill: string; stroke: string; lamp: string; opacity?: number; width?: number }> = ({
  fill,
  stroke,
  lamp,
  opacity = 1,
  width = 58,
}) => (
  <svg width={width} height={width * 0.62} viewBox="-15 -14 30 19" style={{ opacity }}>
    <rect x={-12} y={-9} width={16} height={10} rx={2} fill={fill} stroke={stroke} strokeWidth={0.9} />
    <path d="M4 -7 h5 l3 4 v4 h-8 Z" fill={fill} stroke={stroke} strokeWidth={0.9} />
    <rect x={-10} y={-6} width={8} height={2} fill={lamp} />
    <circle cx={-7} cy={2} r={2.6} fill="#0d2429" stroke={stroke} strokeWidth={0.6} />
    <circle cx={7} cy={2} r={2.6} fill="#0d2429" stroke={stroke} strokeWidth={0.6} />
    <circle cx={-4} cy={-11} r={1.8} fill={lamp} />
  </svg>
);

export const Check: React.FC<{ color: string; size?: number }> = ({ color, size = 22 }) => (
  <svg width={size} height={size} viewBox="0 0 20 20" fill="none">
    <circle cx="10" cy="10" r="9" stroke={color} strokeWidth="1.6" />
    <path d="M6 10.4 l2.6 2.6 L14 7.6" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);
