/**
 * Clip 1 — Beacon intro (6 s).
 *  0.0–1.2  near-black teal frame; a single amber window light comes on.
 *  1.2–3.0  near clouds part and the neighborhood rises out of the dark; slow push.
 *  3.0–6.0  "Beacon", the slogan, and "HackOHI/O 2026 · AEP Challenge" arrive,
 *           then everything settles to a still frame for the cut.
 */
import React from 'react';
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import { TitleBlock } from './components/TitleBlock';
import { World } from './components/World';
import { INTRO } from './timing';

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
const EASE_OUT = Easing.bezier(0.22, 1, 0.36, 1);
const EASE_IN_OUT = Easing.bezier(0.65, 0, 0.35, 1);

export const BeaconIntro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const s = (x: number) => x * fps;
  const [r0, r1] = INTRO.reveal;
  return (
    <AbsoluteFill style={{ backgroundColor: '#050f12' }}>
      <World
        ambient={{ t, amp: interpolate(frame, [s(4.6), s(5.6)], [1, 0], { ...clamp, easing: EASE_IN_OUT }) }}
        zoom={interpolate(frame, [s(INTRO.push[0]), s(INTRO.push[1])], [1, 1.06], { ...clamp, easing: EASE_OUT })}
        canopy={0.78}
        dim={0.38}
        glow={interpolate(frame, [s(r0), s(r1)], [0.15, 1], clamp)}
        darkness={interpolate(frame, [s(r0), s(r0 + 1.5)], [1, 0], { ...clamp, easing: EASE_IN_OUT })}
        beacon={interpolate(
          frame,
          [s(INTRO.lightOn[0]), s(INTRO.lightOn[1]), s(r1 - 0.4), s(r1 + 0.6)],
          [0, 1, 1, 0.32],
          { ...clamp, easing: EASE_OUT },
        )}
        part={interpolate(frame, [s(r0), s(r1)], [0, 1], { ...clamp, easing: EASE_IN_OUT })}
        nearOpacity={interpolate(frame, [s(r0 + 0.45), s(r1)], [1, 0], { ...clamp, easing: EASE_IN_OUT })}
      />
      <TitleBlock
        top={268}
        wordmark={INTRO.wordmark}
        slogan={INTRO.slogan}
        small={{ text: 'HackOHI/O 2026 · AEP Challenge', win: INTRO.tag }}
      />
    </AbsoluteFill>
  );
};
