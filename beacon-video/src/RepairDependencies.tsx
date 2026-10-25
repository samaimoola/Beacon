/**
 * Clip 2 — Repair dependencies (14 s).
 *
 * One anonymized overhead household, medium storm, "Widespread damage", clear
 * access. ONLY the crew count changes: 1 → 2 → 3 → 10. Each stage replays the
 * engine-matched schedule for that crew count at one shared, compressed pace, so
 * shorter schedules visibly finish sooner — until the pole → conductor
 * dependency sets the limit. Restoration ranges are the engine's exact output,
 * crossfaded between stages (no counting through invented values).
 */
import React from 'react';
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import { Grain } from './components/Atmosphere';
import { CrewTruck, Check, JobIcon } from './repair/Icons';
import {
  JOBS,
  MAX_SCHEDULE,
  crewNote,
  jobState,
  stageFor,
  statusText,
  workingCount,
  type JobId,
  type JobState,
  type Stage,
} from './repair/model';
import { C, DEEP_SKY, displayVariation, FONT_DISPLAY, FONT_UI } from './theme';
import { REPAIR } from './timing';

const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
const EASE_OUT = Easing.bezier(0.22, 1, 0.36, 1);

// ---------------------------------------------------------------------------
// Layout (frame pixels)
// ---------------------------------------------------------------------------
const COL1 = 640;
const COL2 = 1300;
const CARD_W = 440;
const CARD_H = 132;
const ROWS: Record<JobId, { x: number; y: number }> = {
  poleA: { x: COL1, y: 318 },
  condA: { x: COL2, y: 318 },
  poleB: { x: COL1, y: 488 },
  condB: { x: COL2, y: 488 },
  xfmr: { x: COL1, y: 658 },
};
const BAR = { x: COL1, y: 900, w: COL2 + CARD_W - COL1, h: 14 };

// ---------------------------------------------------------------------------
// Timeline helpers
// ---------------------------------------------------------------------------
type StageWin = { index: number; crews: number; from: number; to: number };
const STAGE_WINS: StageWin[] = REPAIR.stages.map((s, index) => ({ index, ...s }));

const useClock = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const win = STAGE_WINS.find((w) => t < w.to) ?? STAGE_WINS[STAGE_WINS.length - 1];
  const prev = win.index > 0 ? STAGE_WINS[win.index - 1] : null;
  const stage = stageFor(win.crews);
  const prevStage = prev ? stageFor(prev.crews) : null;
  const rate = stageFor(REPAIR.stages[0].crews).schedule_hours / REPAIR.oneCrewPlaySeconds; // hours per second
  const local = t - win.from;
  const h = Math.min(stage.schedule_hours, Math.max(0, (local - REPAIR.playStart) * rate));
  // 0 → 1 across the crossfade at the start of every stage after the first.
  const xf = prev ? interpolate(local, [0, REPAIR.crossfade], [0, 1], { ...clamp, easing: EASE_OUT }) : 1;
  return { frame, fps, stage, prevStage, h, xf, local };
};

// ---------------------------------------------------------------------------
// Pieces
// ---------------------------------------------------------------------------
const stateStyle = (st: JobState) => {
  switch (st.kind) {
    case 'working':
      return { bg: 'rgba(242,180,90,0.14)', border: 'rgba(242,180,90,0.9)', text: C.lamp, glow: '0 0 38px rgba(242,180,90,0.28)', dash: false };
    case 'done':
      return { bg: 'rgba(143,185,168,0.14)', border: 'rgba(143,185,168,0.75)', text: C.seaglass, glow: 'none', dash: false };
    case 'waiting-dep':
      return { bg: 'rgba(246,241,230,0.025)', border: 'rgba(191,227,230,0.34)', text: 'rgba(191,227,230,0.78)', glow: 'none', dash: true };
    default:
      return { bg: 'rgba(246,241,230,0.045)', border: 'rgba(191,227,230,0.3)', text: 'rgba(246,241,230,0.72)', glow: 'none', dash: false };
  }
};

/** The parts of a card that change with state (rendered per stage, crossfaded). */
const CardDynamic: React.FC<{ id: JobId; st: JobState; opacity: number }> = ({ id, st, opacity }) => {
  const { x, y } = ROWS[id];
  const s = stateStyle(st);
  const progress = st.kind === 'working' ? st.progress : st.kind === 'done' ? 1 : 0;
  return (
    <div style={{ position: 'absolute', left: x, top: y, width: CARD_W, height: CARD_H, opacity }}>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          borderRadius: 26,
          background: s.bg,
          border: `2px ${s.dash ? 'dashed' : 'solid'} ${s.border}`,
          boxShadow: s.glow,
        }}
      />
      <div style={{ position: 'absolute', left: 124, top: 78, display: 'flex', alignItems: 'center', gap: 10, fontFamily: FONT_UI, fontSize: 25, fontWeight: 560, color: s.text }}>
        {st.kind === 'done' && <Check color={C.seaglass} size={24} />}
        {st.kind === 'working' && <span style={{ width: 12, height: 12, borderRadius: 99, background: C.lamp, boxShadow: `0 0 14px ${C.lamp}` }} />}
        {statusText(st)}
      </div>
      <div style={{ position: 'absolute', left: 28, right: 28, bottom: 14, height: 5, borderRadius: 9, background: 'rgba(246,241,230,0.08)' }}>
        <div
          style={{
            width: `${progress * 100}%`,
            height: '100%',
            borderRadius: 9,
            background: st.kind === 'done' ? C.seaglass : C.lamp,
          }}
        />
      </div>
      {st.kind === 'working' && (
        <div style={{ position: 'absolute', right: 26, top: 74 }}>
          <CrewTruck fill={C.lamp} stroke="#0d2429" lamp="#fff3d6" width={56} />
        </div>
      )}
    </div>
  );
};

const CardStatic: React.FC<{ id: JobId }> = ({ id }) => {
  const { x, y } = ROWS[id];
  const job = JOBS.find((j) => j.id === id)!;
  return (
    <div style={{ position: 'absolute', left: x, top: y, width: CARD_W, height: CARD_H }}>
      <div style={{ position: 'absolute', left: 26, top: 28 }}>
        <JobIcon kind={job.icon} accent={C.mist} />
      </div>
      <div style={{ position: 'absolute', left: 124, top: 26, fontFamily: FONT_UI, fontSize: 31, fontWeight: 620, color: C.ivory, letterSpacing: '-0.01em', whiteSpace: 'nowrap' }}>
        {job.label}
      </div>
    </div>
  );
};

/** Pole → conductor link: dashed while the pole is unfinished, solid once it is. */
const Link: React.FC<{ from: JobId; satisfied: number; highlight: number }> = ({ from, satisfied, highlight }) => {
  const y = ROWS[from].y + CARD_H / 2;
  const x0 = COL1 + CARD_W + 14;
  const x1 = COL2 - 18;
  const color = highlight > 0.01 ? C.lamp : C.mist;
  return (
    <svg style={{ position: 'absolute', left: 0, top: 0 }} width={1920} height={1080}>
      <path d={`M${x0} ${y} H${x1}`} stroke={C.mist} strokeOpacity={0.32 * (1 - satisfied)} strokeWidth={3} strokeDasharray="10 10" />
      <path d={`M${x0} ${y} H${x1}`} stroke={color} strokeOpacity={0.35 + 0.6 * Math.max(satisfied, highlight)} strokeWidth={3} strokeDasharray={`${(x1 - x0) * satisfied} 9999`} />
      <path d={`M${x1 - 14} ${y - 10} L${x1} ${y} L${x1 - 14} ${y + 10}`} fill="none" stroke={color} strokeOpacity={0.5 + 0.5 * Math.max(satisfied, highlight)} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round" />
      <text x={(x0 + x1) / 2} y={y - 18} textAnchor="middle" fill={C.mist} fillOpacity={0.75} style={{ fontFamily: FONT_UI, fontSize: 21, fontWeight: 560 }}>
        must finish first
      </text>
    </svg>
  );
};

const Fade: React.FC<{ children: React.ReactNode; opacity: number; style?: React.CSSProperties }> = ({ children, opacity, style }) => (
  <div style={{ position: 'absolute', opacity, ...style }}>{children}</div>
);

// ---------------------------------------------------------------------------
// Composition
// ---------------------------------------------------------------------------
export const RepairDependencies: React.FC = () => {
  const { fps, frame, stage, prevStage, h, xf, local } = useClock();
  const s = (x: number) => x * fps;
  const intro = interpolate(frame, [s(REPAIR.headingIn[0]), s(REPAIR.headingIn[1])], [0, 1], { ...clamp, easing: EASE_OUT });
  const emphasis = interpolate(frame, [s(REPAIR.emphasisAt), s(REPAIR.emphasisAt + 0.5)], [0, 1], { ...clamp, easing: EASE_OUT });
  const prevEnd = prevStage ? prevStage.schedule_hours : 0;
  const sameRange = !!prevStage && prevStage.restoration_window === stage.restoration_window;

  const dyn = (st: Stage, hh: number, op: number) =>
    JOBS.map((j) => <CardDynamic key={`${st.crews}-${j.id}`} id={j.id} st={jobState(st, j.id, hh)} opacity={op} />);

  const satisfied = (pole: JobId) => {
    const cur = jobState(stage, pole, h).kind === 'done' ? 1 : 0;
    const prev = prevStage && jobState(prevStage, pole, prevEnd).kind === 'done' ? 1 : 0;
    return prev * (1 - xf) + cur * xf;
  };

  // Crew pool: slots light up for available crews; amber for crews on a job.
  const working = workingCount(stage, h);
  const prevAvail = prevStage ? prevStage.crews : 0;

  // Schedule bar (illustrative; proportional to the engine schedule, no numbers).
  const barLen = (prevStage ? interpolate(xf, [0, 1], [prevStage.schedule_hours, stage.schedule_hours]) : stage.schedule_hours) / MAX_SCHEDULE;
  const played = h / MAX_SCHEDULE;
  const cpX = (stage.critical_path_hours / MAX_SCHEDULE) * BAR.w;
  const limitStrong = stage.dependency_limited ? 1 : 0.35;

  return (
    <AbsoluteFill style={{ background: DEEP_SKY, color: C.ivory, fontFamily: FONT_UI }}>
      {/* fine utility-line detail across the top */}
      <svg style={{ position: 'absolute', inset: 0 }} width={1920} height={1080}>
        <g stroke={C.mist} strokeOpacity={0.09} strokeWidth={1.4} fill="none">
          <path d="M-20 262 Q 480 300 980 262 T 1960 262" />
          <path d="M-20 274 Q 480 312 980 274 T 1960 274" />
        </g>
        {[60, 980, 1900].map((x) => (
          <g key={x} stroke={C.mist} strokeOpacity={0.12} strokeWidth={2}>
            <path d={`M${x} 250 V300`} />
            <path d={`M${x - 16} 262 H${x + 16}`} />
          </g>
        ))}
      </svg>

      {/* Heading → final emphasis */}
      <div style={{ position: 'absolute', left: 120, top: 92, opacity: intro, translate: `0px ${(1 - intro) * 16}px` }}>
        <div style={{ fontSize: 23, fontWeight: 650, letterSpacing: '0.16em', textTransform: 'uppercase', color: C.mist }}>
          How Beacon models restoration
        </div>
        <div style={{ position: 'relative', marginTop: 18, height: 100, width: 1150 }}>
          {[
            { text: <>Some repairs have to happen first.</>, op: 1 - emphasis },
            {
              text: (
                <>
                  More crews <em style={{ color: C.lamp, fontWeight: 360 }}>can&apos;t skip</em> repair dependencies.
                </>
              ),
              op: emphasis,
            },
          ].map((h1, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                inset: 0,
                opacity: h1.op,
                fontFamily: FONT_DISPLAY,
                fontVariationSettings: displayVariation(70),
                fontWeight: 400,
                fontSize: 78,
                lineHeight: 1.05,
                letterSpacing: '-0.02em',
                whiteSpace: 'nowrap',
              }}
            >
              {h1.text}
            </div>
          ))}
        </div>
      </div>

      {/* Engine restoration range (exact values, crossfaded) */}
      <div style={{ position: 'absolute', right: 120, top: 92, width: 460, textAlign: 'right', opacity: intro }}>
        <div style={{ fontSize: 23, fontWeight: 650, letterSpacing: '0.16em', textTransform: 'uppercase', color: C.mist }}>Modeled restoration</div>
        <div style={{ position: 'relative', height: 96, marginTop: 10 }}>
          {prevStage && !sameRange && (
            <Fade opacity={1 - xf} style={{ right: 0, top: 0, translate: `0px ${-12 * xf}px` }}>
              <RangeText value={prevStage.restoration_window} />
            </Fade>
          )}
          <Fade opacity={sameRange ? 1 : xf} style={{ right: 0, top: 0, translate: `0px ${sameRange ? 0 : 12 * (1 - xf)}px` }}>
            <RangeText value={stage.restoration_window} />
          </Fade>
        </div>
        <div style={{ position: 'relative', height: 32, marginTop: 6, fontSize: 22, color: 'rgba(246,241,230,0.72)' }}>
          <Fade opacity={sameRange ? 1 - xf : 1} style={{ right: 0, top: 0, whiteSpace: 'nowrap' }}>Engine output · heuristic range</Fade>
          {sameRange && (
            <Fade opacity={xf} style={{ right: 0, top: 0, whiteSpace: 'nowrap', color: C.lamp, fontWeight: 600 }}>
              Unchanged from {prevStage!.crews} crews
            </Fade>
          )}
        </div>
      </div>

      {/* Crew pool */}
      <div style={{ position: 'absolute', left: 120, top: 318, width: 400 }}>
        <div style={{ fontSize: 23, fontWeight: 650, letterSpacing: '0.16em', textTransform: 'uppercase', color: C.mist }}>Crews available</div>
        <div style={{ position: 'relative', height: 150, marginTop: 4 }}>
          {prevStage && (
            <Fade opacity={1 - xf} style={{ left: 0, top: 0 }}>
              <CrewNumber n={prevStage.crews} />
            </Fade>
          )}
          <Fade opacity={xf} style={{ left: 0, top: 0 }}>
            <CrewNumber n={stage.crews} />
          </Fade>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 64px)', gap: '16px 12px', marginTop: 14 }}>
          {Array.from({ length: 10 }, (_, i) => {
            const availNow = i < stage.crews ? 1 : 0;
            const avail = prevStage ? (i < prevAvail ? 1 : 0) * (1 - xf) + availNow * xf : availNow;
            const busy = i < working && xf > 0.99;
            return (
              <div key={i} style={{ position: 'relative', width: 64, height: 40 }}>
                <div style={{ position: 'absolute', inset: 0, opacity: 0.16 }}>
                  <CrewTruck fill="transparent" stroke={C.mist} lamp="transparent" width={64} />
                </div>
                <div style={{ position: 'absolute', inset: 0, opacity: avail }}>
                  <CrewTruck
                    fill={busy ? C.lamp : 'rgba(246,241,230,0.9)'}
                    stroke="#0d2429"
                    lamp={busy ? '#fff3d6' : C.mist}
                    width={64}
                  />
                </div>
              </div>
            );
          })}
        </div>
        <div style={{ display: 'flex', gap: 22, marginTop: 20, fontSize: 21, color: 'rgba(246,241,230,0.72)' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 12, height: 12, borderRadius: 3, background: C.lamp }} /> on a job
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 12, height: 12, borderRadius: 3, background: 'rgba(246,241,230,0.9)' }} /> free
          </span>
        </div>
        <div style={{ position: 'relative', marginTop: 26, height: 70, width: 400 }}>
          {prevStage && (
            <Fade opacity={1 - xf} style={{ left: 0, top: 0, width: 400 }}>
              <Note text={crewNote(prevStage)} />
            </Fade>
          )}
          <Fade opacity={xf} style={{ left: 0, top: 0, width: 400 }}>
            <Note text={crewNote(stage)} />
          </Fade>
        </div>
      </div>

      {/* Dependency chains (highlighted for the final emphasis) */}
      {(['poleA', 'poleB'] as const).map((p) => (
        <div
          key={p}
          style={{
            position: 'absolute',
            left: COL1 - 16,
            top: ROWS[p].y - 16,
            width: COL2 + CARD_W - COL1 + 32,
            height: CARD_H + 32,
            borderRadius: 36,
            border: `2px solid rgba(242,180,90,${0.65 * emphasis})`,
            background: `rgba(242,180,90,${0.05 * emphasis})`,
          }}
        />
      ))}

      {/* Cards: per-stage state (crossfaded), then static labels on top */}
      {prevStage && dyn(prevStage, prevEnd, 1 - xf)}
      {dyn(stage, h, xf)}
      {JOBS.map((j) => (
        <CardStatic key={j.id} id={j.id} />
      ))}
      <Link from="poleA" satisfied={satisfied('poleA')} highlight={emphasis} />
      <Link from="poleB" satisfied={satisfied('poleB')} highlight={emphasis} />
      <div
        style={{
          position: 'absolute',
          left: COL2,
          top: ROWS.xfmr.y + 22,
          width: CARD_W,
          fontSize: 24,
          lineHeight: 1.35,
          color: 'rgba(191,227,230,0.82)',
        }}
      >
        <span style={{ fontWeight: 650, color: C.mist }}>No dependency.</span> Starts as soon as a crew is free.
      </div>

      {/* Illustrative schedule bar with the dependency limit */}
      <div style={{ position: 'absolute', left: BAR.x, top: BAR.y - 52, width: BAR.w, display: 'flex', justifyContent: 'space-between', fontSize: 22 }}>
        <span style={{ color: 'rgba(246,241,230,0.8)', fontWeight: 560 }}>Illustrative schedule length</span>
      </div>
      <svg style={{ position: 'absolute', left: BAR.x, top: BAR.y - 60 }} width={BAR.w + 40} height={110}>
        <rect x={0} y={60} width={BAR.w} height={BAR.h} rx={7} fill="rgba(246,241,230,0.08)" />
        <rect x={0} y={60} width={BAR.w * barLen} height={BAR.h} rx={7} fill="rgba(191,227,230,0.3)" />
        <rect x={0} y={60} width={Math.min(BAR.w * barLen, BAR.w * played)} height={BAR.h} rx={7} fill={local < REPAIR.playStart ? 'transparent' : C.lamp} />
        <line x1={cpX} y1={40} x2={cpX} y2={92} stroke={emphasis > 0.01 ? C.lamp : C.mist} strokeOpacity={0.4 + 0.6 * Math.max(limitStrong, emphasis)} strokeWidth={3} strokeDasharray="6 6" />
        <text
          x={cpX + 14}
          y={52}
          fill={emphasis > 0.01 ? C.lamp : C.mist}
          fillOpacity={0.55 + 0.45 * Math.max(limitStrong, emphasis)}
          style={{ fontFamily: FONT_UI, fontSize: 22, fontWeight: 620 }}
        >
          Dependency limit: pole, then conductor
        </text>
      </svg>

      {/* Persistent caption */}
      <div
        style={{
          position: 'absolute',
          left: 120,
          right: 120,
          bottom: 52,
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 24,
          color: 'rgba(246,241,230,0.8)',
        }}
      >
        <span>Illustrative sequence · Simulated damage · Heuristic estimates</span>
        <span style={{ color: 'rgba(191,227,230,0.75)' }}>Same household, storm, damage, and access · only crews change</span>
      </div>
      <Grain opacity={0.06} />
    </AbsoluteFill>
  );
};

const RangeText: React.FC<{ value: string }> = ({ value }) => (
  <div
    style={{
      fontFamily: FONT_DISPLAY,
      fontVariationSettings: displayVariation(50),
      fontWeight: 380,
      fontSize: 88,
      lineHeight: 1,
      letterSpacing: '-0.02em',
      fontVariantNumeric: 'tabular-nums',
      whiteSpace: 'nowrap',
    }}
  >
    {value.replace(/ h$/, '')}
    <span style={{ fontFamily: FONT_UI, fontSize: 34, fontWeight: 500, marginLeft: 12, color: 'rgba(246,241,230,0.75)' }}>hours</span>
  </div>
);

const CrewNumber: React.FC<{ n: number }> = ({ n }) => (
  <div style={{ display: 'flex', alignItems: 'baseline', gap: 16, whiteSpace: 'nowrap' }}>
    <span style={{ fontFamily: FONT_DISPLAY, fontVariationSettings: displayVariation(50), fontWeight: 400, fontSize: 150, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
      {n}
    </span>
    <span style={{ fontSize: 34, fontWeight: 560, color: 'rgba(246,241,230,0.8)' }}>{n === 1 ? 'crew' : 'crews'}</span>
  </div>
);

const Note: React.FC<{ text: string }> = ({ text }) => (
  <div style={{ fontSize: 26, lineHeight: 1.35, color: C.ivory, fontWeight: 480 }}>{text}</div>
);
