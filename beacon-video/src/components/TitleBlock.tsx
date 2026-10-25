/**
 * Beacon's title lockup: mark + wordmark, the exact slogan, and one small line.
 * Each piece takes its own [start, end] window (seconds) for a calm, staggered
 * rise — frame-driven, no CSS animation.
 */
import React from 'react';
import { Easing, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import { C, displayVariation, FONT_DISPLAY, FONT_UI } from '../theme';
import { LogoMark } from './Atmosphere';

const EASE = Easing.bezier(0.22, 1, 0.36, 1); // the app's --ease-out

type Win = readonly [number, number];

const useRise = (win: Win, distance = 26) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // An unused element passes an empty window; give it a valid (instant) range.
  const range = [win[0] * fps, Math.max(win[1] * fps, win[0] * fps + 1)];
  const opts = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE } as const;
  return {
    opacity: interpolate(frame, range, [0, 1], opts),
    translate: `0px ${interpolate(frame, range, [distance, 0], opts)}px`,
  };
};

export const TitleBlock: React.FC<{
  top: number;
  wordmark: Win;
  slogan: Win;
  small?: { text: string; win: Win };
  support?: { text: string; win: Win };
}> = ({ top, wordmark, slogan, small, support }) => {
  const w = useRise(wordmark, 30);
  const s1 = useRise(slogan, 22);
  const s2 = useRise([slogan[0] + 0.18, slogan[1] + 0.18], 22);
  const sm = useRise(small?.win ?? [0, 0], 14);
  const sp = useRise(support?.win ?? [0, 0], 16);
  return (
    <div style={{ position: 'absolute', left: 150, top, width: 820, color: C.ivory }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 34, ...w }}>
        <LogoMark size={128} />
        <div
          style={{
            fontFamily: FONT_DISPLAY,
            fontVariationSettings: displayVariation(70),
            fontWeight: 420,
            fontSize: 196,
            lineHeight: 1,
            letterSpacing: '-0.025em',
            marginTop: -14,
          }}
        >
          Beacon
        </div>
      </div>
      <div
        style={{
          marginTop: 52,
          fontFamily: FONT_DISPLAY,
          fontVariationSettings: displayVariation(80),
          fontWeight: 380,
          fontSize: 76,
          lineHeight: 1.04,
          letterSpacing: '-0.02em',
        }}
      >
        <div style={s1}>When the lights go out,</div>
        <div style={{ ...s2, fontStyle: 'italic', fontWeight: 340, color: C.mist }}>your plan doesn&apos;t</div>
      </div>
      {support && (
        <div
          style={{
            ...sp,
            marginTop: 44,
            fontFamily: FONT_UI,
            fontSize: 38,
            fontWeight: 450,
            letterSpacing: '-0.005em',
            color: 'rgba(246, 241, 230, 0.9)',
          }}
        >
          {support.text}
        </div>
      )}
      {small && (
        <div
          style={{
            ...sm,
            marginTop: 56,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 14,
            fontFamily: FONT_UI,
            fontSize: 30,
            fontWeight: 560,
            letterSpacing: '0.02em',
            color: 'rgba(246, 241, 230, 0.86)',
          }}
        >
          <span style={{ width: 10, height: 10, borderRadius: 99, background: C.lamp, boxShadow: `0 0 18px ${C.lamp}` }} />
          {small.text}
        </div>
      )}
    </div>
  );
};
