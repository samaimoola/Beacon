import React from 'react';
import { AbsoluteFill } from 'remotion';

/**
 * Static film grain (same fractal-noise recipe as the app's `.grain`). The seed is
 * fixed, so every render is identical.
 */
export const Grain: React.FC<{ opacity?: number }> = ({ opacity = 0.075 }) => (
  <AbsoluteFill style={{ pointerEvents: 'none', mixBlendMode: 'overlay', opacity }}>
    <svg width="100%" height="100%" viewBox="0 0 1920 1080" preserveAspectRatio="none">
      <filter id="bv-grain" x="0" y="0" width="100%" height="100%">
        <feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed="7" stitchTiles="stitch" />
        <feColorMatrix values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 1.1 -0.2" />
      </filter>
      <rect width="1920" height="1080" filter="url(#bv-grain)" />
    </svg>
  </AbsoluteFill>
);

/** Soft edge vignette that keeps attention in frame and text legible. */
export const Vignette: React.FC<{ strength?: number }> = ({ strength = 1 }) => (
  <AbsoluteFill
    style={{
      pointerEvents: 'none',
      opacity: strength,
      background:
        'radial-gradient(120% 95% at 60% 50%, transparent 55%, rgba(4, 13, 16, 0.55) 100%)',
    }}
  />
);

/** Beacon's mark from the app's navigation (cloud over a lit home). */
export const LogoMark: React.FC<{ size: number }> = ({ size }) => (
  <svg width={size} height={size} viewBox="0 0 40 40" aria-hidden>
    <circle cx="20" cy="20" r="19" fill="#123137" stroke="#bfe3e6" strokeOpacity=".35" />
    <path d="M9 17c0-3 2.4-5.4 5.4-5.4 1-2.4 3.3-4 6-4 3.6 0 6.5 2.9 6.5 6.5h.3c2.4 0 4.3 1.9 4.3 4.3H9z" fill="#bfe3e6" />
    <path d="M13 31v-7l7-5.5 7 5.5v7z" fill="#f6f1e6" />
    <rect x="18.3" y="25" width="3.4" height="4" rx=".6" fill="#f2b45a" />
    <path d="M10 33h20" stroke="#8fb9a8" strokeWidth="1.6" strokeLinecap="round" />
  </svg>
);
