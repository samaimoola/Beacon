/**
 * The floating-neighborhood "world" used by the intro and outro, framed for
 * 1920×1080 with the island on the right two-thirds and open space on the left
 * for type (the same split as the app's hero).
 *
 * Everything is a pure function of props, so callers drive it from frames.
 */
import React from 'react';
import { AbsoluteFill } from 'remotion';
import {
  type Ambient,
  BEACON_WINDOW,
  Canopy,
  Cloud,
  FarClouds,
  FarIslets,
  Island,
  PUFF_A,
  PUFF_C,
  SceneDefs,
  SeaBack,
  SeaFront,
  TONE,
} from '../art/Neighborhood';
import { HERO_SKY } from '../theme';
import { Grain, Vignette } from './Atmosphere';

/** Scene point the camera is anchored on, and where it lands in the frame. */
const ANCHOR = { sx: 560, sy: 520, fx: 1255, fy: 610 } as const;
export const BASE_SCALE = 1.06;

export type WorldProps = {
  ambient: Ambient;
  /** Camera zoom multiplier on top of BASE_SCALE (1 = framing used for the title). */
  zoom: number;
  /** Small camera pan in frame pixels (positive = scene moves right/down). */
  panX?: number;
  panY?: number;
  /** Storm canopy opacity (0–1) and how far it has lifted (scene units). */
  canopy: number;
  canopyLift?: number;
  /** Vertical offset of the front cloud bank (scene units; 0 = resting). */
  seaRise?: number;
  /** Window glow intensity of the neighborhood (0–1). */
  glow: number;
  /** Full-frame near-black overlay (1 = the opening dark frame). */
  darkness: number;
  /** The first amber window light, drawn above the darkness (0–1). */
  beacon: number;
  /** Near-camera cloud banks: 0 = closed over the island, 1 = fully parted. */
  part: number;
  /** Opacity of those near banks. */
  nearOpacity: number;
  /** Dusk dimming toward the top of frame (like the app's medium-storm dim). */
  dim: number;
};

const camera = (zoom: number, panX: number, panY: number) => {
  const s = BASE_SCALE * zoom;
  return `translate(${ANCHOR.fx + panX} ${ANCHOR.fy + panY}) scale(${s}) translate(${-ANCHOR.sx} ${-ANCHOR.sy})`;
};

export const World: React.FC<WorldProps> = ({
  ambient: a,
  zoom,
  panX = 0,
  panY = 0,
  canopy,
  canopyLift = 0,
  seaRise = 0,
  glow,
  darkness,
  beacon,
  part,
  nearOpacity,
  dim,
}) => {
  const cam = camera(zoom, panX, panY);
  // Near banks slide out to the sides as they part (film space, parallax > scene).
  const leftX = -260 - 980 * part;
  const rightX = 1180 + 980 * part;
  const midY = 560 + 260 * part;
  return (
    <AbsoluteFill style={{ background: HERO_SKY }}>
      <svg width={1920} height={1080} viewBox="0 0 1920 1080" style={{ position: 'absolute', inset: 0 }}>
        <SceneDefs />
        <defs>
          <filter id="bv-soft" x="-20%" y="-40%" width="140%" height="180%">
            <feGaussianBlur stdDeviation="18" />
          </filter>
          <filter id="bv-softer" x="-20%" y="-40%" width="140%" height="180%">
            <feGaussianBlur stdDeviation="34" />
          </filter>
          <linearGradient id="bv-dim" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#051013" stopOpacity="0.85" />
            <stop offset="0.7" stopColor="#051013" stopOpacity="0.2" />
            <stop offset="1" stopColor="#051013" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="bv-textside" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#081a1f" stopOpacity="0.72" />
            <stop offset="0.38" stopColor="#081a1f" stopOpacity="0.34" />
            <stop offset="0.62" stopColor="#081a1f" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="bv-floor" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor="#3c7473" stopOpacity="0" />
            <stop offset="1" stopColor="#3c7473" stopOpacity="0.55" />
          </linearGradient>
        </defs>

        {/* Scene, through the camera */}
        <g transform={cam}>
          {/* The far-left islet and cloud would sit behind the title, so they're omitted. */}
          <FarIslets a={a} clearLeft />
          <FarClouds a={a} clearLeft />
          <SeaBack a={a} />
          <Island a={a} glow={glow} />
          <Canopy a={a} opacity={canopy} lift={canopyLift} />
          <SeaFront a={a} rise={seaRise} />
        </g>

        {/* Dusk dim + low horizon light + legibility gradient behind the type */}
        <rect width={1920} height={1080} fill="url(#bv-dim)" opacity={dim} />
        <rect y={760} width={1920} height={320} fill="url(#bv-floor)" />
        <rect width={1920} height={1080} fill="url(#bv-textside)" />

        {/* Near-camera cloud banks (blurred for depth), parting to reveal */}
        <g opacity={nearOpacity}>
          <g filter="url(#bv-softer)">
            <Cloud x={leftX + 380} y={300 - 120 * part} s={4.2} puffs={PUFF_C} tone={TONE.night} drift="d2" a={a} driftPx={30} />
            <Cloud x={rightX + 260} y={330 - 100 * part} s={4.4} puffs={PUFF_C} tone={TONE.night} drift="d4" a={a} driftPx={30} />
          </g>
          <g filter="url(#bv-soft)">
            <Cloud x={leftX + 160} y={760} s={3.6} puffs={PUFF_A} tone={TONE.heavy} drift="d1" a={a} driftPx={34} />
            <Cloud x={rightX + 160} y={780} s={3.8} puffs={PUFF_C} tone={TONE.heavy} drift="d3" a={a} driftPx={34} />
            <Cloud x={980} y={midY + 260} s={3.2} puffs={PUFF_A} tone={TONE.storm} drift="d2" a={a} driftPx={26} opacity={1 - part} />
          </g>
        </g>

        {/* The opening dark frame */}
        <rect width={1920} height={1080} fill="#050f12" opacity={darkness} />

        {/* The first light: the main home's attic window, above the darkness */}
        <g transform={cam} opacity={beacon}>
          <circle cx={BEACON_WINDOW.x} cy={BEACON_WINDOW.y} r={120} fill="url(#bv-beacon)" opacity={0.55} />
          <circle cx={BEACON_WINDOW.x} cy={BEACON_WINDOW.y} r={34} fill="url(#bv-beacon)" />
          <circle cx={BEACON_WINDOW.x} cy={BEACON_WINDOW.y} r={6.5} fill="#ffe2a6" />
        </g>
      </svg>
      <Vignette />
      <Grain />
    </AbsoluteFill>
  );
};
