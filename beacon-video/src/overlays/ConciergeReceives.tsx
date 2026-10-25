/**
 * "Concierge receives" — explanatory overlays over the Beacon hero recording.
 *
 * The recording is a background only; it does not show a concierge
 * interaction, and nothing here depicts an AI response. All copy is the
 * brief's exact wording. Timing lives in ./timing.ts.
 */
import React from 'react';
import { AbsoluteFill, Html5Audio, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { Grain } from '../components/Atmosphere';
import { C, displayVariation, FONT_DISPLAY, FONT_UI } from '../theme';
import { Footage, lerpCam, type Camera } from './Footage';
import { EASE_IN_OUT, ramp, rise, stage } from './motion';
import { CONCIERGE as T } from './timing';

const FULL = { x: 0, y: 0, w: 1920, h: 1080 };
// Island centre (source ≈ 2026, 933) sits right of centre; the hero copy on the
// left is softened under the overlays. Framing constraints at both ends of the
// slow pull-back: the whole "Illustrative scenario / Not a map…" strip (right
// edge source x ≈ 2755) stays inside the frame, the top edge stays below the
// sticky nav (source y ≈ 193) and the bottom edge above the ivory cloud band
// (source y ≈ 1730).
const ISLAND_X = 1345;
const ISLAND_Y = 517;
const islandAt = (k: number): Camera => ({ cx: 2026 - (ISLAND_X - 960) / k, cy: 933 - (ISLAND_Y - 540) / k, k });
const CAM_A = islandAt(0.725);
const CAM_B = islandAt(0.71);

const COL_X = 132;

const Eyebrow: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div
    style={{
      fontFamily: FONT_UI,
      fontSize: 24,
      fontWeight: 650,
      letterSpacing: '0.16em',
      textTransform: 'uppercase',
      color: C.mist,
      ...style,
    }}
  >
    {children}
  </div>
);

/* ---------- icons (simple line glyphs in the site's style) ---------- */
const Glyph: React.FC<{ kind: 'scenario' | 'results' | 'explain'; color: string }> = ({ kind, color }) => (
  <svg width="34" height="34" viewBox="0 0 34 34" fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round">
    {kind === 'scenario' && (
      <>
        <path d="M6 10h22M6 17h22M6 24h22" opacity=".55" />
        <circle cx="12" cy="10" r="3" fill={C.storm900} />
        <circle cx="22" cy="17" r="3" fill={C.storm900} />
        <circle cx="15" cy="24" r="3" fill={C.storm900} />
      </>
    )}
    {kind === 'results' && (
      <>
        <path d="M6 27h22" opacity=".55" />
        <path d="M9 23v-6M15 23V9M21 23v-9M27 23v-4" />
      </>
    )}
    {kind === 'explain' && (
      <>
        <path d="M7 8h20a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H15l-6 5v-5H7a3 3 0 0 1-3-3V11a3 3 0 0 1 3-3z" />
        <path d="M10 14h14M10 18.5h9" opacity=".7" />
      </>
    )}
  </svg>
);

const Node: React.FC<{
  label: string;
  kind: 'scenario' | 'results' | 'explain';
  style: React.CSSProperties;
  lit?: number;
  top: number;
}> = ({ label, kind, style, lit = 0, top }) => {
  const isOut = kind === 'explain';
  return (
    <div
      style={{
        position: 'absolute',
        left: 96,
        top,
        height: 104,
        padding: '0 34px 0 26px',
        display: 'flex',
        alignItems: 'center',
        gap: 22,
        borderRadius: 22,
        background: isOut ? `rgba(18, 49, 55, ${0.72 + lit * 0.18})` : 'rgba(8, 25, 29, 0.66)',
        border: `1.5px solid ${isOut ? `rgba(191, 227, 230, ${0.28 + lit * 0.5})` : 'rgba(191, 227, 230, 0.2)'}`,
        boxShadow: isOut
          ? `0 18px 50px rgba(0,0,0,.32), 0 0 ${48 * lit}px rgba(191, 227, 230, ${0.22 * lit})`
          : '0 14px 40px rgba(0,0,0,.28)',
        whiteSpace: 'nowrap',
        ...style,
      }}
    >
      <div
        style={{
          width: 58,
          height: 58,
          borderRadius: 99,
          display: 'grid',
          placeItems: 'center',
          background: isOut ? 'rgba(191, 227, 230, 0.12)' : 'rgba(191, 227, 230, 0.07)',
        }}
      >
        <Glyph kind={kind} color={isOut ? C.mist : C.seaglass} />
      </div>
      <div style={{ fontFamily: FONT_UI, fontSize: 38, fontWeight: 600, letterSpacing: '-0.01em', color: C.ivory }}>{label}</div>
    </div>
  );
};

/* ---------- Stage 1: context becomes an explanation ---------- */
const StageFlow: React.FC<{ t: number }> = ({ t }) => {
  const yA = 330;
  const yB = 470;
  const yC = 676;
  const spineX = 52;
  const midA = yA + 52;
  const midB = yB + 52;
  const midC = yC + 52;
  // Branches draw once their node is in; the trunk draws as results arrive.
  const drawA = ramp(t, T.scenario + 0.25, T.scenario + 1.0);
  const drawB = ramp(t, T.results + 0.15, T.results + 0.7);
  const drawTrunk = ramp(t, T.results + 0.35, T.explanationLit + 0.25, EASE_IN_OUT);
  const lit = ramp(t, T.explanationLit, T.explanationLit + 0.6);
  // Soft pulses travelling down the trunk after it is drawn (deterministic in t).
  const pulses = [0, 0.5].map((o) => {
    const p = ((t - T.explanationLit - o) / 1.1) % 1;
    return t > T.explanationLit + o ? p : -1;
  });
  const branch = (y: number) => `M 96 ${y} H ${spineX + 22} Q ${spineX} ${y} ${spineX} ${y + 22}`;
  const trunkLen = midC - midA;
  return (
    <div style={{ position: 'absolute', left: COL_X, top: 0, width: 900, height: 1080, ...stage(t, T.stage1.in, T.stage1.out) }}>
      <Eyebrow style={{ position: 'absolute', left: 0, top: 196, ...rise(t, T.stage1.in, 0.7, 14) }}>What the concierge receives</Eyebrow>
      <svg width="900" height="1080" style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible' }}>
        <path d={branch(midA)} stroke={C.mist} strokeOpacity=".5" strokeWidth="2.5" fill="none" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - drawA} />
        <path d={branch(midB)} stroke={C.mist} strokeOpacity=".5" strokeWidth="2.5" fill="none" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - drawB} />
        <path
          d={`M ${spineX} ${midA + 22} V ${midC - 22} Q ${spineX} ${midC} ${spineX + 22} ${midC} H 84`}
          stroke={C.mist}
          strokeOpacity=".62"
          strokeWidth="2.5"
          fill="none"
          pathLength={1}
          strokeDasharray="1"
          strokeDashoffset={1 - drawTrunk}
        />
        <path d={`M 76 ${midC - 8} L 88 ${midC} L 76 ${midC + 8}`} stroke={C.mist} strokeWidth="2.5" fill="none" strokeLinecap="round" opacity={ramp(t, T.explanationLit, T.explanationLit + 0.3)} />
        {pulses.map((p, i) =>
          p >= 0 ? (
            <circle key={i} cx={spineX} cy={midA + 22 + p * (trunkLen - 44)} r={5} fill={C.lamp} opacity={Math.sin(Math.PI * p) * 0.9 * lit} />
          ) : null,
        )}
      </svg>
      <Node label="Selected scenario" kind="scenario" top={yA} style={rise(t, T.scenario, 0.7, 18)} />
      <Node label="Calculated engine results" kind="results" top={yB} style={rise(t, T.results, 0.7, 18)} />
      <Node label="AI explanation" kind="explain" top={yC} lit={lit} style={{ opacity: 0.5 * ramp(t, T.explanation, T.explanation + 0.8) + 0.5 * lit }} />
    </div>
  );
};

/* ---------- Stage 2: what the structured context excludes ---------- */
const Excluded: React.FC<{ text: string; style: React.CSSProperties }> = ({ text, style }) => (
  <div style={{ display: 'flex', alignItems: 'center', gap: 26, height: 84, ...style }}>
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none" aria-hidden>
      <circle cx="20" cy="20" r="16" stroke={C.lamp} strokeOpacity=".85" strokeWidth="2.4" />
      <path d="M9 31 31 9" stroke={C.lamp} strokeOpacity=".85" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
    <div style={{ fontFamily: FONT_UI, fontSize: 46, fontWeight: 500, letterSpacing: '-0.012em', color: C.ivory }}>{text}</div>
  </div>
);

const ITEMS = ['Raw addresses', 'Meter identifiers', 'Employee details', 'Precise coordinates'] as const;

const StageExcluded: React.FC<{ t: number }> = ({ t }) => (
  <div style={{ position: 'absolute', left: COL_X, top: 0, width: 900, ...stage(t, T.stage2.in, T.stage2.out) }}>
    <div
      style={{
        position: 'absolute',
        top: 214,
        width: 760,
        fontFamily: FONT_DISPLAY,
        fontVariationSettings: displayVariation(70),
        fontWeight: 400,
        fontSize: 66,
        lineHeight: 1.08,
        letterSpacing: '-0.02em',
        color: C.ivory,
        ...rise(t, T.stage2.in, 0.8, 20),
      }}
    >
      Excluded from the
      <br />
      <span style={{ fontStyle: 'italic', color: C.mist }}>structured context</span>
    </div>
    <div
      style={{
        position: 'absolute',
        top: 404,
        width: 120,
        height: 2,
        background: C.lamp,
        opacity: 0.8,
        transformOrigin: 'left',
        scale: `${ramp(t, T.stage2.in + 0.3, T.stage2.in + 1.0)} 1`,
      }}
    />
    <div style={{ position: 'absolute', top: 452 }}>
      {ITEMS.map((txt, i) => (
        <Excluded key={txt} text={txt} style={{ marginBottom: 14, ...rise(t, T.excluded[i], 0.6, 16) }} />
      ))}
    </div>
  </div>
);

/* ---------- Stage 3: division of responsibility ---------- */
const StageRoles: React.FC<{ t: number }> = ({ t }) => (
  <div style={{ position: 'absolute', left: COL_X, top: 0, width: 960, ...stage(t, T.stage3.in) }}>
    <div
      style={{
        position: 'absolute',
        top: 330,
        fontFamily: FONT_DISPLAY,
        fontVariationSettings: displayVariation(80),
        fontWeight: 400,
        fontSize: 86,
        lineHeight: 1.08,
        letterSpacing: '-0.025em',
        color: C.ivory,
        whiteSpace: 'nowrap',
      }}
    >
      <div style={rise(t, T.engineLine, 0.8, 22)}>The engine calculates.</div>
      <div style={{ ...rise(t, T.conciergeLine, 0.8, 22), fontStyle: 'italic', fontWeight: 360, color: C.mist }}>The concierge explains.</div>
    </div>
    <div
      style={{
        position: 'absolute',
        top: 600,
        display: 'flex',
        alignItems: 'center',
        gap: 18,
        fontFamily: FONT_UI,
        fontSize: 40,
        fontWeight: 500,
        color: 'rgba(246, 241, 230, 0.9)',
        ...rise(t, T.support, 0.8, 14),
      }}
    >
      <span style={{ width: 12, height: 12, borderRadius: 99, background: C.lamp, boxShadow: `0 0 18px ${C.lamp}` }} />
      Sources and limitations stay visible.
    </div>
  </div>
);

export const ConciergeReceives: React.FC<{ narration: boolean }> = ({ narration }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const t = frame / fps;
  const cam = lerpCam(CAM_A, CAM_B, ramp(t, 0, durationInFrames / fps, EASE_IN_OUT));
  const fadeIn = ramp(t, 0, 0.5);
  return (
    <AbsoluteFill style={{ background: C.night }}>
      <AbsoluteFill style={{ opacity: fadeIn }}>
        <Footage src={T.video} sourceStart={T.sourceStart} cam={cam} win={FULL} filter="brightness(0.8) saturate(0.92)" />
        {/* Soften and darken the hero copy behind the overlay column; keep the island crisp. */}
        <AbsoluteFill
          style={{
            backdropFilter: 'blur(16px)',
            WebkitMaskImage: 'linear-gradient(90deg, #000 0%, #000 38%, transparent 50%)',
            maskImage: 'linear-gradient(90deg, #000 0%, #000 38%, transparent 50%)',
          }}
        />
        <AbsoluteFill
          style={{
            background:
              'linear-gradient(90deg, rgba(5,15,18,0.9) 0%, rgba(6,18,22,0.82) 34%, rgba(8,25,29,0.42) 54%, rgba(8,25,29,0.08) 72%, transparent 100%),' +
              'linear-gradient(180deg, rgba(5,15,18,0.35) 0%, transparent 22%, transparent 78%, rgba(5,15,18,0.4) 100%)',
          }}
        />
      </AbsoluteFill>
      <StageFlow t={t} />
      <StageExcluded t={t} />
      <StageRoles t={t} />
      <div
        style={{
          position: 'absolute',
          left: COL_X,
          bottom: 64,
          fontFamily: FONT_UI,
          fontSize: 24,
          fontWeight: 500,
          color: 'rgba(191, 227, 230, 0.72)',
          opacity: ramp(t, 0.6, 1.4),
        }}
      >
        Explanatory graphic · Beacon prototype
      </div>
      <Grain opacity={0.05} />
      {narration && <Html5Audio src={staticFile(T.audio)} />}
    </AbsoluteFill>
  );
};
