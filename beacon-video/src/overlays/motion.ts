/** Frame-driven motion helpers in seconds (t = frame / fps). Deterministic. */
import type React from 'react';
import { Easing, interpolate } from 'remotion';

export const EASE = Easing.bezier(0.22, 1, 0.36, 1); // the app's --ease-out
export const EASE_IN_OUT = Easing.bezier(0.65, 0, 0.35, 1);

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/** 0 → 1 between a and b (seconds), eased. */
export const ramp = (t: number, a: number, b: number, easing = EASE) =>
  interpolate(t, [a, Math.max(b, a + 1e-3)], [0, 1], { ...clamp, easing });

/** Fade + short upward drift starting at `start`. */
export const rise = (t: number, start: number, dur = 0.7, dist = 22): React.CSSProperties => {
  const p = ramp(t, start, start + dur);
  return { opacity: p, translate: `0px ${(1 - p) * dist}px` };
};

/** Whole-stage visibility: in at `inAt`, out (with a small lift) at `outAt`. */
export const stage = (t: number, inAt: number, outAt?: number, fade = 0.45): React.CSSProperties => {
  const a = ramp(t, inAt, inAt + 0.2);
  const b = outAt === undefined ? 0 : ramp(t, outAt, outAt + fade, EASE_IN_OUT);
  return { opacity: a * (1 - b), translate: `0px ${-b * 18}px` };
};
