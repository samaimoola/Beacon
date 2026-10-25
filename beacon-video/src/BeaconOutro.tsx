/**
 * Clip 3 — Beacon outro (5 s).
 * Opens on the neighborhood and its warm window light. The camera eases back,
 * the storm canopy lifts and thins, and the cloud sea rises into place. The
 * lockup arrives with "Understand the scenario. Make a plan." and the frame
 * comes fully to rest by ~2.8 s, leaving open space at lower left for team names.
 */
import React from 'react';
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import { TitleBlock } from './components/TitleBlock';
import { World } from './components/World';
import { OUTRO } from './timing';

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
const EASE_OUT = Easing.bezier(0.22, 1, 0.36, 1);
const EASE_IN_OUT = Easing.bezier(0.65, 0, 0.35, 1);

export const BeaconOutro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const s = (x: number) => x * fps;
  const [a0, a1] = OUTRO.settle;
  const settle = { ...clamp, easing: EASE_OUT };
  return (
    <AbsoluteFill style={{ backgroundColor: '#050f12' }}>
      <World
        ambient={{ t, amp: interpolate(frame, [s(1.6), s(2.8)], [1, 0], { ...clamp, easing: EASE_IN_OUT }) }}
        zoom={interpolate(frame, [s(a0), s(a1)], [1.11, 1.02], settle)}
        canopy={interpolate(frame, [s(a0), s(a1)], [0.8, 0.42], settle)}
        canopyLift={interpolate(frame, [s(a0), s(a1)], [0, 46], settle)}
        seaRise={interpolate(frame, [s(a0), s(a1)], [70, 0], settle)}
        dim={interpolate(frame, [s(a0), s(a1)], [0.38, 0.22], settle)}
        glow={1}
        darkness={interpolate(frame, [0, s(0.5)], [0.55, 0], clamp)}
        beacon={interpolate(frame, [0, s(a1)], [0.75, 0.34], settle)}
        part={interpolate(frame, [s(a0), s(2.2)], [0.55, 1], settle)}
        nearOpacity={interpolate(frame, [s(a0), s(2.0)], [0.85, 0], clamp)}
      />
      <TitleBlock
        top={196}
        wordmark={OUTRO.wordmark}
        slogan={OUTRO.slogan}
        support={{ text: 'Understand the scenario. Make a plan.', win: OUTRO.support }}
      />
    </AbsoluteFill>
  );
};
