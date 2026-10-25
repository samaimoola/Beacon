/**
 * "Distinction matters" — the real Reading panel from the recording, framed in
 * a branded window, with two callouts in a dedicated left margin.
 *
 * Every number on screen is the app's own displayed engine output. The opening
 * holds one clean frame of the unchanged starting state (the recording has a
 * cursor and text selections there), then plays one continuous, real-time
 * segment of the recording (crew count 10 → 1).
 * Nothing is drawn over the values, their labels or the disclaimers; the
 * callouts sit outside the window and only outline the groups they refer to.
 */
import React from 'react';
import { AbsoluteFill, Freeze, Html5Audio, Sequence, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { Grain } from '../components/Atmosphere';
import { C, displayVariation, FONT_DISPLAY, FONT_UI } from '../theme';
import { Footage, lerpCam, project, type Camera, type Win } from './Footage';
import { EASE_IN_OUT, ramp, rise } from './motion';
import { DISTINCTION as T } from './timing';

/** Branded window for the footage (video px). */
const WIN: Win = { x: 640, y: 64, w: 1216, h: 952 };

/**
 * Reading-panel crop in source px: "02 · The reading" through the three result
 * columns (x 1272–2736, y 198–1309). The pull-back widens it to also show the
 * "Why this risk band" / "What drives the range" headings below.
 */
// Top edge stays just below the app's sticky nav (source y ≈ 194) in both cameras.
const CAM_A: Camera = { cx: 2004, cy: 776, k: 1216 / 1480 };
const CAM_B: Camera = { cx: 2030, cy: 839, k: 0.74 };

/** Result groups in source px (label + value + bar / caption), measured from the recording. */
const RANGE_BOX = { x0: 1288, y0: 404, x1: 2722, y1: 868 };
const RISK_BOX = { x0: 1288, y0: 986, x1: 1748, y1: 1238 };

const MARGIN_X = 96;
const MARGIN_W = 470;

type Tone = { line: string; glow: string; text: string };
const MIST: Tone = { line: C.mist, glow: 'rgba(191, 227, 230, 0.32)', text: C.mist };
const AMBER: Tone = { line: C.lamp, glow: 'rgba(242, 180, 90, 0.34)', text: C.lampWarm };

const Callout: React.FC<{
  head: string;
  body: React.ReactNode;
  /** Vertical centre of the callout (video px) — tracks its result group. */
  cy: number;
  tone: Tone;
  t: number;
  at: number;
}> = ({ head, body, cy, tone, t, at }) => (
  // Outer div centres the block on its leader; the inner div carries the
  // reveal (rise() sets its own `translate`, so the two must not share a node).
  <div style={{ position: 'absolute', left: MARGIN_X, top: cy, width: MARGIN_W, translate: '0px -50%' }}>
    <div style={rise(t, at, 0.75, 18)}>
    <div
      style={{
        fontFamily: FONT_DISPLAY,
        fontVariationSettings: displayVariation(70),
        fontWeight: 420,
        fontSize: 64,
        lineHeight: 1,
        letterSpacing: '-0.02em',
        color: tone.text,
      }}
    >
      {head}
    </div>
    <div
      style={{
        marginTop: 16,
        fontFamily: FONT_UI,
        fontSize: 38,
        fontWeight: 500,
        lineHeight: 1.22,
        letterSpacing: '-0.01em',
        color: C.ivory,
      }}
    >
      {body}
    </div>
    </div>
  </div>
);

/** Outline around a result group (drawn outside its content) plus a leader to the margin. */
const Marker: React.FC<{
  box: typeof RANGE_BOX;
  cam: Camera;
  tone: Tone;
  t: number;
  at: number;
}> = ({ box, cam, tone, t, at }) => {
  const a = project(cam, WIN, box.x0, box.y0);
  const b = project(cam, WIN, box.x1, box.y1);
  const pad = 14;
  const x0 = a.x - pad;
  const y0 = a.y - pad;
  const x1 = Math.min(b.x + pad, WIN.x + WIN.w - 10);
  const y1 = b.y + pad;
  const midY = (y0 + y1) / 2;
  const draw = ramp(t, at + 0.15, at + 0.95, EASE_IN_OUT);
  const ring = ramp(t, at + 0.55, at + 1.25);
  const leaderX0 = MARGIN_X + MARGIN_W + 4;
  return (
    <svg width="1920" height="1080" style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>
      <defs>
        <filter id={`glow-${box.y0}`} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="6" />
        </filter>
      </defs>
      <path
        d={`M ${leaderX0} ${midY} H ${x0}`}
        stroke={tone.line}
        strokeWidth="2.5"
        strokeLinecap="round"
        fill="none"
        pathLength={1}
        strokeDasharray="1"
        strokeDashoffset={1 - draw}
      />
      <circle cx={leaderX0} cy={midY} r={6} fill={tone.line} opacity={ramp(t, at, at + 0.3)} />
      <rect x={x0} y={y0} width={x1 - x0} height={y1 - y0} rx={18} fill="none" stroke={tone.glow} strokeWidth="8" filter={`url(#glow-${box.y0})`} opacity={ring} />
      <rect x={x0} y={y0} width={x1 - x0} height={y1 - y0} rx={18} fill="none" stroke={tone.line} strokeWidth="2.5" opacity={ring * 0.95} />
    </svg>
  );
};

export const DistinctionMatters: React.FC<{ narration: boolean }> = ({ narration }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const holdFrames = Math.round((T.holdSource - T.sourceOffset) * fps);

  const pull = ramp(t, T.pullBack[0], T.pullBack[1], EASE_IN_OUT);
  // A slow push during the body, then the pull-back for the final sentence.
  const push = ramp(t, 2.6, T.pullBack[0], EASE_IN_OUT);
  const camPushed: Camera = { ...CAM_A, k: CAM_A.k * (1 + 0.018 * push) };
  const cam = lerpCam(camPushed, CAM_B, pull);

  const veil = 1 - ramp(t, T.footageClear[0], T.footageClear[1], EASE_IN_OUT);
  const titleOut = ramp(t, 2.15, 2.6, EASE_IN_OUT);
  const headIn = ramp(t, 2.45, 3.05);

  const rangeCy = (project(cam, WIN, 0, RANGE_BOX.y0).y + project(cam, WIN, 0, RANGE_BOX.y1).y) / 2;
  const riskCy = (project(cam, WIN, 0, RISK_BOX.y0).y + project(cam, WIN, 0, RISK_BOX.y1).y) / 2;

  return (
    <AbsoluteFill style={{ background: 'linear-gradient(180deg, #0a1f24 0%, #0d2429 50%, #11303a 100%)' }}>
      <AbsoluteFill
        style={{
          background:
            'radial-gradient(40% 50% at 14% 30%, rgba(191, 227, 230, 0.07), transparent 70%),' +
            'radial-gradient(40% 50% at 14% 80%, rgba(242, 180, 90, 0.05), transparent 70%)',
        }}
      />

      {/* Footage window */}
      <div
        style={{
          position: 'absolute',
          left: WIN.x,
          top: WIN.y,
          width: WIN.w,
          height: WIN.h,
          borderRadius: 28,
          overflow: 'hidden',
          background: C.ivory,
          boxShadow: '0 40px 90px rgba(0, 0, 0, 0.45), 0 0 0 1.5px rgba(191, 227, 230, 0.18)',
          opacity: ramp(t, 0, 0.45),
        }}
      >
        {/* Held clean frame, then real-time playback from that same frame (seamless). */}
        <Sequence durationInFrames={holdFrames} layout="none">
          <Freeze frame={0}>
            <Footage src={T.video} sourceStart={T.holdSource} cam={cam} win={WIN} />
          </Freeze>
        </Sequence>
        <Sequence from={holdFrames} layout="none">
          <Footage src={T.video} sourceStart={T.holdSource} cam={cam} win={WIN} />
        </Sequence>
        <AbsoluteFill style={{ background: `rgba(8, 25, 29, ${0.78 * veil})` }} />
      </div>

      {/* Opening title over the veiled footage */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'grid',
          placeItems: 'center',
          opacity: (1 - titleOut) * ramp(t, T.title, T.title + 0.7),
          translate: `0px ${(1 - ramp(t, T.title, T.title + 0.8)) * 22 - titleOut * 16}px`,
        }}
      >
        <div
          style={{
            fontFamily: FONT_DISPLAY,
            fontVariationSettings: displayVariation(80),
            fontWeight: 400,
            fontSize: 132,
            letterSpacing: '-0.03em',
            color: C.ivory,
            textShadow: '0 6px 40px rgba(0,0,0,.35)',
          }}
        >
          Two different <span style={{ fontStyle: 'italic', color: C.mist }}>questions.</span>
        </div>
      </div>

      {/* Margin heading */}
      <div style={{ position: 'absolute', left: MARGIN_X, top: 92, width: MARGIN_W, opacity: headIn, translate: `0px ${(1 - headIn) * 14}px` }}>
        <div style={{ fontFamily: FONT_UI, fontSize: 24, fontWeight: 650, letterSpacing: '0.16em', textTransform: 'uppercase', color: C.mist }}>
          Beacon reading
        </div>
        <div
          style={{
            marginTop: 14,
            fontFamily: FONT_DISPLAY,
            fontVariationSettings: displayVariation(80),
            fontWeight: 400,
            fontSize: 52,
            lineHeight: 1.05,
            letterSpacing: '-0.02em',
            color: C.ivory,
          }}
        >
          Two different <span style={{ fontStyle: 'italic', color: C.mist }}>questions.</span>
        </div>
      </div>

      <Marker box={RANGE_BOX} cam={cam} tone={AMBER} t={t} at={T.repair} />
      <Marker box={RISK_BOX} cam={cam} tone={MIST} t={t} at={T.risk} />
      <Callout head="Risk:" body={<>storm, network,<br />simulated damage</>} cy={riskCy} tone={MIST} t={t} at={T.risk} />
      <Callout head="Repair time:" body="jobs, crews, access" cy={rangeCy} tone={AMBER} t={t} at={T.repair} />

      <div
        style={{
          position: 'absolute',
          left: MARGIN_X,
          bottom: 64,
          width: MARGIN_W,
          fontFamily: FONT_UI,
          fontSize: 24,
          fontWeight: 500,
          lineHeight: 1.35,
          color: 'rgba(191, 227, 230, 0.72)',
          opacity: headIn,
        }}
      >
        Recorded from the Beacon prototype
        <br />
        Simulated scenario · Heuristic ranges
      </div>

      <Grain opacity={0.045} />
      {narration && <Html5Audio src={staticFile(T.audio)} />}
    </AbsoluteFill>
  );
};
