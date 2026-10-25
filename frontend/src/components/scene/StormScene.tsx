'use client';

/**
 * StormScene — original, code-generated illustration of a small neighborhood on a
 * floating island above the clouds. ILLUSTRATIVE ONLY: not a map, not live weather,
 * not outage status. Window lights and power lines are decorative and constant.
 *
 * Responds gently to scenario inputs:
 *   severity      -> storm-cloud density + rain
 *   accessBlocked -> highlighted access route with a fallen tree and barrier
 *   crews         -> N symbolic crew markers in the crew yard
 *
 * Performance: flat fills (no blur filters), CSS transform/opacity animations,
 * paused offscreen / in hidden tabs, disabled under prefers-reduced-motion.
 * All "random" placement is seeded at module scope, so SSR and client match.
 */
import { memo, useRef, type CSSProperties, type RefObject } from 'react';
import {
  AnimatePresence,
  motion,
  useReducedMotion,
  useScroll,
  useTransform,
  type MotionValue,
} from 'framer-motion';
import type { Severity } from '@/lib/scenario';
import { usePauseWhenHidden } from '@/hooks/usePauseWhenHidden';

const LINE = '#21393a';

// ---------------------------------------------------------------------------
// Seeded, module-level geometry (deterministic → no hydration mismatch)
// ---------------------------------------------------------------------------

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const r1 = (n: number) => Math.round(n * 10) / 10;
const r2 = (n: number) => Math.round(n * 100) / 100;

const RAIN_TILE = 640;
const RAIN_DX = 160;
const RAIN_DROPS = (() => {
  const rnd = mulberry32(20261024);
  return Array.from({ length: 96 }, () => {
    const x = r1(-40 + rnd() * 1300);
    const y = r1(140 + rnd() * RAIN_TILE);
    const len = r1(14 + rnd() * 18);
    const edge = Math.max(0, Math.min(1, (Math.abs(x - 600) - 400) / 260));
    const o = r2((0.35 + rnd() * 0.45) * (1 - 0.85 * edge));
    return { x, y, len, o };
  });
})();


// ---------------------------------------------------------------------------
// High-storm rain: three depth layers drawn as ONE <path> each (cheap to paint).
// Streaks are longer, faster and more wind-slanted than Low/Medium rain.
// Deterministic (seeded) so SSR and client markup match exactly.
// ---------------------------------------------------------------------------
interface RainSpec {
  id: 'back' | 'mid' | 'front';
  visible: number; // streaks visible at once (before tiling overhead)
  len: [number, number];
  slant: number; // horizontal travel per unit of fall (wind)
  tile: number; // vertical tile height for seamless looping
  dur: string;
  width: number;
  opacity: number;
  seed: number;
}
const HIGH_RAIN: RainSpec[] = [
  { id: 'back', visible: 95, len: [12, 20], slant: 0.4, tile: 560, dur: '1.9s', width: 1.1, opacity: 0.4, seed: 7001 },
  { id: 'mid', visible: 110, len: [20, 32], slant: 0.52, tile: 640, dur: '1.05s', width: 1.5, opacity: 0.58, seed: 7002 },
  { id: 'front', visible: 40, len: [38, 60], slant: 0.6, tile: 700, dur: '0.78s', width: 2, opacity: 0.3, seed: 7003 },
];
const HIGH_RAIN_LAYERS = HIGH_RAIN.map((spec) => {
  const rnd = mulberry32(spec.seed);
  const dx = Math.round(spec.slant * spec.tile);
  const width = 1240 + dx;
  const n = Math.round((spec.visible * width) / 1200);
  let d = '';
  for (let i = 0; i < n; i++) {
    const x = r1(-40 + rnd() * width);
    const y = r1(140 + rnd() * spec.tile);
    const len = r1(spec.len[0] + rnd() * (spec.len[1] - spec.len[0]));
    const run = r1(-spec.slant * len);
    d += `M${x} ${y}l${run} ${len}M${r1(x + dx)} ${r1(y - spec.tile)}l${run} ${len}`;
  }
  return { ...spec, dx, d };
});

function HighRain({ p, layer }: { p: string; layer: 'back' | 'front' }) {
  // back: behind the island (depth). front: mid + foreground streaks over it.
  const layers = HIGH_RAIN_LAYERS.filter((l) => (layer === 'back' ? l.id === 'back' : l.id !== 'back'));
  return (
    <g clipPath={`url(#${p}-rain)`}>
      {layers.map((l) => (
        <g
          key={l.id}
          className="rain-v"
          style={{ '--tx': `${l.dx}px`, '--ty': `${l.tile}px`, '--dur': l.dur } as CSSProperties}
        >
          <path d={l.d} stroke="#cfe9ec" strokeOpacity={l.opacity} strokeWidth={l.width} strokeLinecap="round" fill="none" />
        </g>
      ))}
    </g>
  );
}

const SEVERITY = {
  low: { rain: 22, dur: '2.9s', canopy: 0.5, bank2: 0, bank3: 0, birds: 1 },
  medium: { rain: 52, dur: '2.1s', canopy: 0.85, bank2: 0.9, bank3: 0, birds: 0.75 },
  high: { rain: 96, dur: '1.5s', canopy: 1, bank2: 1, bank3: 1, birds: 0 },
} as const;

// Crew-yard slots (two rows of five)
const CREW_SLOTS: [number, number][] = [
  [182, 520], [212, 520], [242, 520], [272, 520], [302, 520],
  [197, 538], [227, 538], [257, 538], [287, 538], [317, 538],
];

// ---------------------------------------------------------------------------
// Paths
// ---------------------------------------------------------------------------

const GRASS =
  'M120 520 C170 470 300 440 420 446 C520 451 560 424 640 428 C780 434 880 452 975 452 C1035 452 1075 480 1085 520 C1050 556 960 574 840 578 C690 584 520 586 360 580 C250 576 160 562 120 520 Z';
const SOIL =
  'M120 520 C160 562 250 576 360 580 C520 586 690 584 840 578 C960 574 1050 556 1085 520 C1084 542 1070 562 1048 576 C990 606 880 616 760 618 C600 622 430 620 300 608 C210 600 150 582 124 550 C121 540 120 530 120 520 Z';
const UNDERSIDE =
  'M124 550 C150 582 210 600 300 608 C430 620 600 622 760 618 C880 616 990 606 1048 576 C1036 604 1004 628 962 648 C928 664 912 692 874 708 C838 724 812 724 784 744 C752 768 716 770 690 792 C668 810 640 814 616 808 C590 802 572 782 548 772 C510 756 486 762 452 740 C420 720 410 698 372 686 C330 672 300 668 266 644 C230 618 196 608 164 586 C146 574 132 564 124 550 Z';
const HILL_A = 'M150 525 C200 430 280 392 360 400 C430 407 470 380 530 384 C590 388 620 420 652 442 L652 525 Z';
const HILL_B = 'M600 525 C650 420 730 380 820 386 C900 392 940 410 990 430 C1030 446 1062 482 1076 525 Z';
const ROAD = 'M128 552 C190 560 244 574 320 576 C392 578 452 568 520 570 C566 571 604 566 634 560';

const STRATA = [
  'M190 600 C280 630 380 640 470 646',
  'M330 660 C420 676 520 690 600 690',
  'M640 650 C720 652 820 646 900 630',
  'M500 722 C560 742 620 750 680 744',
  'M760 692 C800 692 840 682 880 670',
  'M232 622 C252 628 272 634 292 642',
];
const ROOTS = [
  'M260 606 C254 630 262 650 256 676',
  'M318 612 C326 640 314 660 322 690',
  'M402 618 C396 646 408 668 400 704',
  'M560 622 C566 650 556 676 562 712',
  'M705 620 C700 648 712 674 706 700',
  'M850 615 C858 640 846 664 852 690',
  'M940 606 C934 628 944 646 938 668',
  'M480 620 C478 636 486 644 482 660',
];

// ---------------------------------------------------------------------------
// Primitives
// ---------------------------------------------------------------------------

type Puff = readonly [number, number, number];
const PUFF_A: readonly Puff[] = [[0, 0, 46], [48, -20, 56], [106, -8, 50], [150, 8, 36], [-40, 10, 32]];
const PUFF_B: readonly Puff[] = [[0, 0, 34], [36, -14, 42], [82, -4, 38], [116, 8, 26]];
const PUFF_C: readonly Puff[] = [[0, 0, 58], [64, -26, 70], [140, -10, 62], [198, 10, 44], [-54, 14, 40]];

interface Tone {
  fill: string;
  shade: string;
  light: string;
}
const TONE: Record<'far' | 'storm' | 'heavy' | 'thunder' | 'sea' | 'seaBack', Tone> = {
  far: { fill: '#b6d3d1', shade: '#9cbfbd', light: '#d6eae6' },
  storm: { fill: '#2a5056', shade: '#1c3a40', light: '#3a666b' },
  heavy: { fill: '#1f3f47', shade: '#132c33', light: '#2c545a' },
  // High storm only: the darkest, most substantial upper cloud deck.
  thunder: { fill: '#17333a', shade: '#0d242a', light: '#27494f' },
  sea: { fill: '#e4f0ec', shade: '#c7dcd8', light: '#f6fbf7' },
  seaBack: { fill: '#cfe2de', shade: '#b5cfcb', light: '#e3efeb' },
};

function Cloud({
  x,
  y,
  s = 1,
  puffs,
  tone,
  drift = 'd1',
  opacity,
}: {
  x: number;
  y: number;
  s?: number;
  puffs: readonly Puff[];
  tone: Tone;
  drift?: string;
  opacity?: number;
}) {
  const minX = Math.min(...puffs.map(([cx, , r]) => cx - r));
  const maxX = Math.max(...puffs.map(([cx, , r]) => cx + r));
  const w = maxX - minX - 36;
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`} opacity={opacity}>
      <g className={`drift ${drift}`}>
        {puffs.map(([cx, cy, r], i) => (
          <circle key={`s${i}`} cx={cx} cy={cy + 8} r={r} fill={tone.shade} />
        ))}
        <rect x={minX + 18} y={0} width={w} height={36} rx={18} fill={tone.shade} />
        {puffs.map(([cx, cy, r], i) => (
          <circle key={`f${i}`} cx={cx} cy={cy} r={r} fill={tone.fill} />
        ))}
        <rect x={minX + 18} y={-8} width={w} height={32} rx={16} fill={tone.fill} />
        {/* soft top-light: one gentle sheen per cloud rather than per puff */}
        <ellipse
          cx={(puffs[1][0] + puffs[2][0]) / 2}
          cy={Math.min(...puffs.map(([, cy, r]) => cy - r)) + 22}
          rx={(maxX - minX) * 0.3}
          ry={14}
          fill={tone.light}
          opacity={0.32}
        />
      </g>
    </g>
  );
}

function Tree({ x, y, s = 1, delay = 0, tone = '#4c7f70', light = '#6f9f8c' }: {
  x: number; y: number; s?: number; delay?: number; tone?: string; light?: string;
}) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <ellipse cx={0} cy={1} rx={14} ry={3} fill="#2f5a4f" opacity={0.25} />
      <g className="sway" style={{ animationDelay: `${delay}s` }}>
        <rect x={-2.5} y={-18} width={5} height={19} rx={2} fill="#5b4a3a" />
        <circle cx={0} cy={-31} r={16} fill={tone} />
        <circle cx={-11} cy={-22} r={11} fill={tone} />
        <circle cx={11} cy={-23} r={12} fill={tone} />
        <circle cx={-4} cy={-37} r={7} fill={light} opacity={0.85} />
        <circle cx={7} cy={-28} r={4} fill={light} opacity={0.6} />
      </g>
    </g>
  );
}

function Conifer({ x, y, s = 1, fill = '#35645a' }: { x: number; y: number; s?: number; fill?: string }) {
  return (
    <path
      transform={`translate(${x} ${y}) scale(${s})`}
      d="M0 -34 L10 -16 L5 -16 L13 -2 L2 -2 L2 2 L-2 2 L-2 -2 L-13 -2 L-5 -16 L-10 -16 Z"
      fill={fill}
    />
  );
}

function House({ x, y, w = 56, h = 40, roof = '#3a6a66', wall = '#efe4cc', flip = false }: {
  x: number; y: number; w?: number; h?: number; roof?: string; wall?: string; flip?: boolean;
}) {
  const top = y - h;
  const peak = top - w * 0.42;
  const winX = flip ? x + w * 0.58 : x + w * 0.18;
  const doorX = flip ? x + w * 0.2 : x + w * 0.62;
  return (
    <g>
      <ellipse cx={x + w / 2} cy={y + 2} rx={w * 0.64} ry={5} fill="#4f7f6d" opacity={0.35} />
      <rect x={x} y={top} width={w} height={h} fill={wall} stroke={LINE} strokeWidth={1.2} />
      <path
        d={`M${x - 6} ${top + 2} L${x + w / 2} ${peak} L${x + w + 6} ${top + 2} Z`}
        fill={roof}
        stroke={LINE}
        strokeWidth={1.2}
        strokeLinejoin="round"
      />
      <circle cx={winX + w * 0.12} cy={top + h * 0.42} r={18} fill="url(#sr-windowGlow)" />
      <rect x={winX} y={top + h * 0.26} width={w * 0.24} height={h * 0.32} rx={1.5} fill="#f6c76c" stroke={LINE} strokeWidth={1} />
      <line x1={winX + w * 0.12} y1={top + h * 0.26} x2={winX + w * 0.12} y2={top + h * 0.58} stroke={LINE} strokeWidth={0.8} />
      <rect x={doorX} y={y - h * 0.55} width={w * 0.2} height={h * 0.55} rx={w * 0.08} fill="#3d6d60" stroke={LINE} strokeWidth={1} />
    </g>
  );
}

function Pole({ x, y, h }: { x: number; y: number; h: number }) {
  const top = y - h;
  return (
    <g>
      <line x1={x} y1={y} x2={x} y2={top} stroke="#3a3f39" strokeWidth={3.6} strokeLinecap="round" />
      <line x1={x - 16} y1={top + 8} x2={x + 16} y2={top + 8} stroke="#3a3f39" strokeWidth={2.6} strokeLinecap="round" />
      {[-12, 12].map((dx) => (
        <rect key={dx} x={x + dx - 1.6} y={top + 2} width={3.2} height={6} rx={1.2} fill="#cfe3d9" stroke={LINE} strokeWidth={0.6} />
      ))}
      <circle cx={x} cy={top} r={1.8} fill="#cfe3d9" stroke={LINE} strokeWidth={0.6} />
    </g>
  );
}

type Pt = { x: number; y: number };
const POLES = [
  { x: 392, y: 476, h: 82 },
  { x: 520, y: 468, h: 84 },
  { x: 742, y: 466, h: 84 },
  { x: 880, y: 474, h: 80 },
  { x: 1004, y: 484, h: 74 },
];
const span = (a: Pt, b: Pt) => {
  const sag = Math.hypot(b.x - a.x, b.y - a.y) * 0.075;
  return `M${a.x} ${a.y} Q${(a.x + b.x) / 2} ${(a.y + b.y) / 2 + sag} ${b.x} ${b.y}`;
};
const WIRES: string[] = (() => {
  const out: string[] = [];
  const tops = POLES.map((p) => ({ x: p.x, y: p.y - p.h }));
  // substation gantry to first pole
  out.push(span({ x: 330, y: 436 }, { x: tops[0].x - 12, y: tops[0].y + 4 }));
  out.push(span({ x: 318, y: 436 }, { x: tops[0].x + 12, y: tops[0].y + 4 }));
  for (let i = 0; i < tops.length - 1; i++) {
    const a = tops[i];
    const b = tops[i + 1];
    out.push(span({ x: a.x - 12, y: a.y + 4 }, { x: b.x - 12, y: b.y + 4 }));
    out.push(span({ x: a.x + 12, y: a.y + 4 }, { x: b.x + 12, y: b.y + 4 }));
    out.push(span(a, b));
  }
  // service drops
  out.push(span({ x: tops[1].x + 12, y: tops[1].y + 4 }, { x: 586, y: 470 }));
  out.push(span({ x: tops[3].x - 12, y: tops[3].y + 4 }, { x: 812, y: 506 }));
  out.push(span({ x: tops[0].x + 12, y: tops[0].y + 4 }, { x: 440, y: 498 }));
  return out;
})();

function CrewMarker({ x, y }: { x: number; y: number }) {
  return (
    <g transform={`translate(${x} ${y})`}>
      <ellipse cx={0} cy={4} rx={13} ry={2.6} fill="#20363a" opacity={0.25} />
      <rect x={-12} y={-9} width={16} height={10} rx={2} fill="#2f5754" stroke={LINE} strokeWidth={0.9} />
      <path d="M4 -7 h5 l3 4 v4 h-8 Z" fill="#f1e6cd" stroke={LINE} strokeWidth={0.9} />
      <rect x={-10} y={-6} width={8} height={2} fill="#f2b45a" />
      <circle cx={-7} cy={2} r={2.6} fill="#1b2829" />
      <circle cx={7} cy={2} r={2.6} fill="#1b2829" />
      <circle cx={-4} cy={-11} r={1.8} fill="#f2b45a" />
    </g>
  );
}

// ---------------------------------------------------------------------------
// Composite layers
// ---------------------------------------------------------------------------

function Defs({ p, rainY }: { p: string; rainY: number }) {
  return (
    <defs>
      <linearGradient id={`${p}-grass`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#a9cdb6" />
        <stop offset="1" stopColor="#6c9d8a" />
      </linearGradient>
      <linearGradient id={`${p}-hillA`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#4f7f73" />
        <stop offset="1" stopColor="#3b665c" />
      </linearGradient>
      <linearGradient id={`${p}-hillB`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#62917f" />
        <stop offset="1" stopColor="#4a776b" />
      </linearGradient>
      <linearGradient id={`${p}-soil`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#8a735a" />
        <stop offset="1" stopColor="#6a5644" />
      </linearGradient>
      <linearGradient id={`${p}-rock`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#5b5246" />
        <stop offset="0.6" stopColor="#3b4141" />
        <stop offset="1" stopColor="#253538" />
      </linearGradient>
      <linearGradient id={`${p}-water`} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#dff2f2" stopOpacity="0.95" />
        <stop offset="1" stopColor="#bfe3e6" stopOpacity="0" />
      </linearGradient>
      <radialGradient id={`${p}-mist`}>
        <stop offset="0" stopColor="#e6f2ef" stopOpacity="0.85" />
        <stop offset="1" stopColor="#e6f2ef" stopOpacity="0" />
      </radialGradient>
      <radialGradient id="sr-windowGlow">
        <stop offset="0" stopColor="#f6c76c" stopOpacity="0.6" />
        <stop offset="1" stopColor="#f6c76c" stopOpacity="0" />
      </radialGradient>
      <clipPath id={`${p}-rain`}>
        <rect x={-120} y={rainY} width={1440} height={700} />
      </clipPath>
    </defs>
  );
}

function FarIslets() {
  return (
    <g fill="#2f5c5d" opacity={0.62}>
      <g className="bob b1">
        <path d="M48 300 C80 284 150 282 210 296 C200 312 170 318 140 340 C120 352 100 344 88 330 C72 318 56 312 48 300 Z" />
        <path d="M106 282 L119 270 L132 282 Z" />
        <rect x={110} y={281} width={18} height={13} />
        <rect x={115} y={285} width={4} height={4} fill="#f2b45a" opacity={0.85} />
        <circle cx={152} cy={280} r={9} />
        <rect x={151} y={284} width={2} height={9} />
      </g>
      <g className="bob b2">
        <path d="M1010 252 C1050 238 1120 238 1160 250 C1150 266 1124 270 1100 290 C1084 300 1066 294 1056 282 C1040 270 1020 264 1010 252 Z" />
        <path d="M1078 250 L1080.4 196 L1082.6 196 L1085 250 Z" />
        <g className="rotor">
          <circle cx={1081.5} cy={196} r={28} fill="transparent" />
          <circle cx={1081.5} cy={196} r={2.6} />
          {[0, 120, 240].map((a) => (
            <path key={a} transform={`rotate(${a} 1081.5 196)`} d="M1081.5 196 L1083.6 171 L1079.4 171 Z" />
          ))}
        </g>
      </g>
    </g>
  );
}

function Birds({ opacity }: { opacity: number }) {
  return (
    <g className="storm-layer" style={{ opacity }}>
      <g className="glide">
        {[
          [300, 252, 1, ''],
          [330, 238, 0.8, 'f2'],
          [354, 258, 0.7, 'f3'],
        ].map(([x, y, s, f]) => (
          <g key={`${x}`} transform={`translate(${x} ${y}) scale(${s})`}>
            <path
              className={`flap ${f}`}
              d="M0 0 q6 -6 12 0 q6 -6 12 0"
              stroke={LINE}
              strokeWidth={1.7}
              fill="none"
              strokeLinecap="round"
            />
          </g>
        ))}
      </g>
    </g>
  );
}

function Substation() {
  return (
    <g>
      <ellipse cx={268} cy={486} rx={80} ry={10} fill="#c8bea6" opacity={0.9} />
      {/* equipment */}
      {[214, 254].map((x) => (
        <g key={x}>
          <rect x={x} y={456} width={30} height={27} rx={3} fill="#93aca5" stroke={LINE} strokeWidth={1} />
          {[4, 9, 14, 19, 24].map((d) => (
            <line key={d} x1={x + d + 1} y1={460} x2={x + d + 1} y2={479} stroke="#6f8a84" strokeWidth={1} />
          ))}
          {[7, 22].map((d) => (
            <g key={d}>
              <rect x={x + d - 2} y={446} width={4} height={10} fill="#cfe3d9" stroke={LINE} strokeWidth={0.7} />
              <circle cx={x + d} cy={445} r={2} fill="#cfe3d9" stroke={LINE} strokeWidth={0.7} />
            </g>
          ))}
        </g>
      ))}
      {/* gantry */}
      <g stroke="#3a3f39" strokeWidth={2.2} strokeLinecap="round">
        <line x1={300} y1={486} x2={300} y2={430} />
        <line x1={332} y1={486} x2={332} y2={430} />
        <line x1={294} y1={436} x2={338} y2={436} />
      </g>
      {[306, 318, 330].map((x) => (
        <rect key={x} x={x - 1.5} y={437} width={3} height={7} rx={1} fill="#cfe3d9" stroke={LINE} strokeWidth={0.6} />
      ))}
      <path d="M244 445 C262 428 284 428 306 442" stroke={LINE} strokeWidth={0.9} fill="none" />
      <path d="M276 445 C290 434 306 432 318 442" stroke={LINE} strokeWidth={0.9} fill="none" />
      {/* fence */}
      <rect x={200} y={452} width={142} height={33} fill="none" stroke={LINE} strokeWidth={1} opacity={0.75} />
      {Array.from({ length: 10 }, (_, i) => 200 + i * 15.8).map((x) => (
        <line key={x} x1={x} y1={452} x2={x} y2={485} stroke={LINE} strokeWidth={0.7} opacity={0.55} />
      ))}
      <line x1={200} y1={457} x2={342} y2={457} stroke={LINE} strokeWidth={0.6} opacity={0.5} />
      {/* windsock */}
      <line x1={184} y1={492} x2={184} y2={446} stroke="#3a3f39" strokeWidth={1.8} strokeLinecap="round" />
      <g className="flutter">
        <path d="M184 448 L206 451 L206 459 L184 461 Z" fill="#f8ddd5" stroke={LINE} strokeWidth={0.8} />
        <path d="M191 449 L191 460 M198 450 L198 459.5" stroke="#e0735f" strokeWidth={2.4} />
      </g>
    </g>
  );
}

function MainHome() {
  return (
    <g>
      <ellipse cx={644} cy={551} rx={96} ry={7} fill="#4f7f6d" opacity={0.35} />
      {/* chimney + wisps */}
      <rect x={670} y={420} width={16} height={36} fill="#7a5d48" stroke={LINE} strokeWidth={1.2} />
      <rect x={667} y={415} width={22} height={6} rx={1.5} fill="#5e4636" stroke={LINE} strokeWidth={1} />
      <g fill="none" stroke="#e8f1ee" strokeWidth={3} strokeLinecap="round">
        <path className="wisp w1" d="M678 408 c-6 -8 6 -14 0 -22" />
        <path className="wisp w2" d="M680 408 c6 -8 -6 -14 0 -22" />
      </g>
      {/* body */}
      <rect x={578} y={468} width={124} height={80} fill="#f1e6cd" stroke={LINE} strokeWidth={1.4} />
      {[484, 500, 516, 532].map((y) => (
        <line key={y} x1={579} y1={y} x2={701} y2={y} stroke="#dccca9" strokeWidth={0.8} />
      ))}
      {/* roof */}
      <path d="M564 472 L640 410 L716 472 Z" fill="#2f5754" stroke={LINE} strokeWidth={1.4} strokeLinejoin="round" />
      <path d="M592 452 L688 452 M614 434 L666 434" stroke="#40706b" strokeWidth={1} />
      <line x1={561} y1={472} x2={719} y2={472} stroke={LINE} strokeWidth={2.2} strokeLinecap="round" />
      {/* attic window */}
      <circle cx={640} cy={447} r={16} fill="url(#sr-windowGlow)" />
      <circle cx={640} cy={447} r={7} fill="#f6c76c" stroke={LINE} strokeWidth={1} />
      <path d="M633 447 H647 M640 440 V454" stroke={LINE} strokeWidth={0.7} />
      {/* windows */}
      {[590, 666].map((x) => (
        <g key={x}>
          <circle cx={x + 13} cy={495} r={36} fill="url(#sr-windowGlow)" />
          <rect x={x - 6} y={483} width={5} height={24} fill="#3d6d60" />
          <rect x={x + 27} y={483} width={5} height={24} fill="#3d6d60" />
          <rect x={x} y={484} width={26} height={22} rx={1.5} fill="#f6c76c" stroke={LINE} strokeWidth={1.1} />
          <path d={`M${x + 13} 484 V506 M${x} 495 H${x + 26}`} stroke={LINE} strokeWidth={0.8} />
          <rect x={x - 2} y={506} width={30} height={3} fill="#d9c9a7" stroke={LINE} strokeWidth={0.6} />
        </g>
      ))}
      {/* porch + door */}
      <path d="M620 518 L640 507 L660 518" stroke={LINE} strokeWidth={1.4} fill="none" strokeLinejoin="round" />
      <circle cx={640} cy={514} r={2.4} fill="#f6c76c" />
      <path d="M629 548 V530 a11 11 0 0 1 22 0 V548 Z" fill="#3d6d60" stroke={LINE} strokeWidth={1.1} />
      <circle cx={646} cy={538} r={1.3} fill="#f2b45a" />
      <rect x={624} y={547} width={32} height={4} fill="#d9c9a7" stroke={LINE} strokeWidth={0.6} />
      {/* garage */}
      <rect x={702} y={506} width={44} height={42} fill="#e9dcbf" stroke={LINE} strokeWidth={1.2} />
      <path d="M698 508 L750 508 L745 500 L703 500 Z" fill="#2f5754" stroke={LINE} strokeWidth={1.1} />
      <rect x={709} y={518} width={30} height={30} fill="#d6c7a6" stroke={LINE} strokeWidth={0.8} />
      {[524, 530, 536, 542].map((y) => (
        <line key={y} x1={709} y1={y} x2={739} y2={y} stroke={LINE} strokeWidth={0.5} opacity={0.6} />
      ))}
      {/* weather vane */}
      <line x1={640} y1={410} x2={640} y2={392} stroke={LINE} strokeWidth={1.4} />
      <g className="vane">
        <path d="M628 392 H652 M652 392 l-5 -3 M652 392 l-5 3 M628 392 l-4 -4 h4" stroke={LINE} strokeWidth={1.4} fill="none" strokeLinecap="round" />
      </g>
      <circle cx={640} cy={392} r={1.7} fill={LINE} />
      {/* fence */}
      {[586, 593, 600, 607, 614, 621, 659, 666, 673, 680, 687, 694].map((x) => (
        <rect key={x} x={x} y={549} width={3} height={10} rx={1} fill="#f6f1e6" stroke={LINE} strokeWidth={0.5} />
      ))}
      <path d="M584 553 H625 M657 553 H698" stroke={LINE} strokeWidth={0.7} />
      {/* garden + lantern + mailbox */}
      {[[592, 545, '#f8ddd5'], [606, 544, '#fbe9c9'], [676, 545, '#bfe3e6'], [690, 544, '#f8ddd5']].map(([x, y, c]) => (
        <circle key={`${x}`} cx={x as number} cy={y as number} r={3} fill={c as string} stroke={LINE} strokeWidth={0.4} />
      ))}
      <line x1={614} y1={566} x2={614} y2={545} stroke="#3a3f39" strokeWidth={1.6} />
      <circle cx={614} cy={543} r={9} fill="url(#sr-windowGlow)" />
      <rect x={611} y={539} width={6} height={7} rx={1.5} fill="#f6c76c" stroke={LINE} strokeWidth={0.6} />
      <line x1={694} y1={568} x2={694} y2={558} stroke="#3a3f39" strokeWidth={1.4} />
      <rect x={688} y={553} width={12} height={7} rx={3} fill="#3d6d60" stroke={LINE} strokeWidth={0.6} />
    </g>
  );
}

function Island({ p, accessBlocked, crews }: { p: string; accessBlocked: boolean; crews: number }) {
  return (
    <g className="float">
      {/* underside */}
      <path d={UNDERSIDE} fill={`url(#${p}-rock)`} />
      <g stroke="#a39377" strokeOpacity={0.28} strokeWidth={1.3} fill="none" strokeLinecap="round">
        {STRATA.map((d) => (
          <path key={d} d={d} />
        ))}
      </g>
      <path d={SOIL} fill={`url(#${p}-soil)`} />
      <g stroke="#6e5a43" strokeOpacity={0.75} strokeWidth={1.3} fill="none" strokeLinecap="round">
        {ROOTS.map((d) => (
          <path key={d} d={d} />
        ))}
      </g>
      {/* waterfall */}
      <path
        d="M996 566 C998 600 1004 640 1000 700 C998 740 1006 770 1004 800 L1022 800 C1022 770 1016 740 1018 700 C1022 640 1016 600 1014 566 Z"
        fill={`url(#${p}-water)`}
      />
      <g stroke="#ffffff" strokeOpacity={0.7} strokeWidth={1.4} fill="none" strokeLinecap="round">
        <path className="shimmer" d="M1002 578 C1004 640 1006 700 1008 790" />
        <path className="shimmer s2" d="M1010 576 C1011 640 1012 700 1014 790" />
      </g>
      {/* hills + far trees */}
      <path d={HILL_A} fill={`url(#${p}-hillA)`} />
      <path d={HILL_B} fill={`url(#${p}-hillB)`} />
      <g stroke="#2f5a50" strokeOpacity={0.35} strokeWidth={1} fill="none">
        <path d="M220 470 C280 440 340 430 400 432" />
        <path d="M700 440 C760 420 840 418 900 430" />
      </g>
      {[[300, 404, 0.9], [322, 410, 0.75], [470, 390, 0.8], [560, 398, 0.7], [760, 392, 0.9], [790, 390, 0.7], [905, 406, 0.85]].map(([x, y, s]) => (
        <Conifer key={`${x}`} x={x} y={y} s={s} />
      ))}
      {/* plateau */}
      <path d={GRASS} fill={`url(#${p}-grass)`} />
      <path
        d="M120 520 C160 562 250 576 360 580 C520 586 690 584 840 578 C960 574 1050 556 1085 520"
        stroke="#4f7d6c"
        strokeWidth={2}
        fill="none"
        strokeOpacity={0.6}
      />
      <g stroke="#5f907d" strokeOpacity={0.5} strokeWidth={1} fill="none" strokeLinecap="round">
        {[[160, 540], [240, 556], [470, 560], [720, 566], [890, 560], [1010, 540], [380, 500], [800, 470]].map(([x, y]) => (
          <path key={`${x}`} d={`M${x} ${y} q3 -6 6 0 M${x + 8} ${y + 1} q3 -5 6 0`} />
        ))}
      </g>
      <path d="M930 532 C950 548 975 556 1005 566" stroke="#bfe3e6" strokeWidth={5} fill="none" strokeLinecap="round" />
      <path d="M934 532 C952 546 975 553 1003 563" stroke="#ffffff" strokeOpacity={0.6} strokeWidth={1.2} fill="none" />
      {/* back row */}
      <House x={408} y={452} w={46} h={32} roof="#3f6e69" />
      <House x={868} y={458} w={50} h={34} roof="#2f5754" flip />
      <Tree x={760} y={460} s={0.7} delay={-2} />
      <Substation />
      {/* poles + wires (decorative, constant — not service status) */}
      <g className="wires" stroke="#2a3433" strokeWidth={1.1} fill="none" opacity={0.85}>
        {WIRES.map((d) => (
          <path key={d} d={d} />
        ))}
      </g>
      {POLES.map((pl) => (
        <Pole key={pl.x} {...pl} />
      ))}
      {/* front row */}
      <Tree x={366} y={502} s={0.85} delay={-1} />
      <Tree x={150} y={512} s={0.7} delay={-3} />
      <House x={392} y={534} w={58} h={40} roof="#2f5754" />
      <Tree x={548} y={522} s={0.8} delay={-4} />
      <Tree x={736} y={522} s={0.85} delay={-2.5} />
      <House x={980} y={516} w={46} h={34} roof="#3f6e69" flip />
      <Tree x={1042} y={516} s={0.8} delay={-1.5} />
      <House x={884} y={532} w={54} h={38} roof="#2f5754" />
      <House x={770} y={544} w={62} h={42} roof="#3f6e69" flip />
      <Tree x={472} y={548} s={0.95} delay={-3.5} />
      <Tree x={846} y={556} s={1} delay={-0.5} />
      <Tree x={962} y={552} s={0.95} delay={-4.5} />
      <MainHome />
      {/* crew yard */}
      <ellipse cx={250} cy={530} rx={100} ry={20} fill="#cdbf9f" opacity={0.9} />
      <ellipse cx={250} cy={530} rx={100} ry={20} fill="none" stroke={LINE} strokeOpacity={0.35} strokeDasharray="3 4" />
      <AnimatePresence>
        {CREW_SLOTS.slice(0, crews).map(([x, y], i) => (
          <motion.g
            key={`crew-${i}`}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.35, delay: i * 0.025 }}
          >
            <CrewMarker x={x} y={y} />
          </motion.g>
        ))}
      </AnimatePresence>
      {/* access road */}
      <path d={ROAD} stroke="#b4a37d" strokeWidth={20} fill="none" strokeLinecap="round" />
      <path d={ROAD} stroke="#e7ddc4" strokeWidth={16} fill="none" strokeLinecap="round" />
      <path d="M641 549 L636 561" stroke="#e7ddc4" strokeWidth={9} strokeLinecap="round" />
      <path d="M128 545 L128 560 M136 543 L136 560" stroke="#3a3f39" strokeWidth={2} strokeLinecap="round" />
      <AnimatePresence>
        {accessBlocked && (
          <motion.g
            key="blocked"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.5 }}
          >
            <path d={ROAD} stroke="#e0735f" strokeOpacity={0.2} strokeWidth={32} fill="none" strokeLinecap="round" />
            <path className="march" d={ROAD} stroke="#c25a45" strokeWidth={3.4} strokeDasharray="10 9" fill="none" strokeLinecap="round" />
            <g transform="rotate(-9 440 568)">
              <rect x={406} y={563} width={66} height={9} rx={4.5} fill="#6b5442" stroke={LINE} strokeWidth={1} />
              <circle cx={474} cy={562} r={9} fill="#4c7f70" />
              <circle cx={484} cy={568} r={7} fill="#6f9f8c" />
              <path d="M418 567 h10 M436 566 h8" stroke="#4a3a2d" strokeWidth={0.8} />
            </g>
            <g transform="translate(512 568)">
              <path d="M-12 8 L-8 -6 M12 8 L8 -6" stroke="#3a3f39" strokeWidth={1.6} strokeLinecap="round" />
              <rect x={-15} y={-11} width={30} height={7} rx={1.5} fill="#f6f1e6" stroke={LINE} strokeWidth={0.8} />
              <path d="M-11 -11 l-4 7 h4 l4 -7 Z M-1 -11 l-4 7 h4 l4 -7 Z M9 -11 l-4 7 h4 l4 -7 Z" fill="#e0735f" />
            </g>
          </motion.g>
        )}
      </AnimatePresence>
      {/* edge mist */}
      <ellipse className="mist-pulse" cx={170} cy={548} rx={130} ry={30} fill={`url(#${p}-mist)`} />
      <ellipse className="mist-pulse m2" cx={1066} cy={526} rx={120} ry={30} fill={`url(#${p}-mist)`} />
    </g>
  );
}

function StormCanopy({ cfg, high = false }: { cfg: (typeof SEVERITY)[Severity]; high?: boolean }) {
  // `high` swaps in a darker, denser upper deck. Low/Medium render exactly as before.
  const top = high ? TONE.thunder : TONE.storm;
  const lift = high ? 1.12 : 1;
  return (
    <g>
      <g className="storm-layer" style={{ opacity: cfg.canopy }}>
        <Cloud x={40} y={70} s={1.1 * lift} puffs={PUFF_C} tone={top} drift="d1" />
        <Cloud x={330} y={52} s={1.25 * lift} puffs={PUFF_C} tone={top} drift="d3" />
        <Cloud x={640} y={80} s={1.15 * lift} puffs={PUFF_C} tone={top} drift="d2" />
        <Cloud x={930} y={56} s={1.3 * lift} puffs={PUFF_C} tone={top} drift="d4" />
        <Cloud x={1180} y={86} s={1 * lift} puffs={PUFF_A} tone={top} drift="d3" />
        {high && (
          <>
            <Cloud x={190} y={26} s={1.3} puffs={PUFF_C} tone={TONE.thunder} drift="d2" />
            <Cloud x={500} y={20} s={1.35} puffs={PUFF_C} tone={TONE.thunder} drift="d4" />
            <Cloud x={800} y={24} s={1.3} puffs={PUFF_C} tone={TONE.thunder} drift="d1" />
            <Cloud x={1090} y={18} s={1.25} puffs={PUFF_C} tone={TONE.thunder} drift="d3" />
          </>
        )}
      </g>
      <g className="storm-layer" style={{ opacity: cfg.bank2 }}>
        <Cloud x={140} y={166} s={1} puffs={PUFF_A} tone={high ? TONE.heavy : TONE.storm} drift="d2" />
        <Cloud x={520} y={172} s={0.9} puffs={PUFF_A} tone={high ? TONE.heavy : TONE.storm} drift="d4" />
        <Cloud x={820} y={176} s={1.1} puffs={PUFF_A} tone={high ? TONE.heavy : TONE.storm} drift="d1" />
        <Cloud x={1080} y={160} s={0.95} puffs={PUFF_B} tone={high ? TONE.heavy : TONE.storm} drift="d3" />
      </g>
      <g className="storm-layer" style={{ opacity: cfg.bank3 }}>
        <Cloud x={250} y={146} s={1.4} puffs={PUFF_C} tone={TONE.heavy} drift="d3" />
        <Cloud x={700} y={138} s={1.5} puffs={PUFF_C} tone={TONE.heavy} drift="d1" />
        <Cloud x={1060} y={132} s={1.3} puffs={PUFF_C} tone={TONE.heavy} drift="d2" />
      </g>
    </g>
  );
}

function Rain({ p, count }: { p: string; count: number }) {
  return (
    <g clipPath={`url(#${p}-rain)`}>
      <g className="rain-sheet" stroke="#cfe9ec" strokeWidth={1.5} strokeLinecap="round">
        {RAIN_DROPS.map((d, i) => (
          <g key={i} className={i < count ? 'drop on' : 'drop'} style={{ '--o': d.o } as CSSProperties}>
            <line x1={d.x} y1={d.y} x2={r1(d.x - d.len * 0.25)} y2={r1(d.y + d.len)} />
            <line
              x1={r1(d.x + RAIN_DX)}
              y1={r1(d.y - RAIN_TILE)}
              x2={r1(d.x + RAIN_DX - d.len * 0.25)}
              y2={r1(d.y - RAIN_TILE + d.len)}
            />
          </g>
        ))}
      </g>
    </g>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export interface StormSceneProps {
  severity: Severity;
  accessBlocked: boolean;
  crews: number;
  variant?: 'hero' | 'window';
  scrollTarget?: RefObject<HTMLElement>;
  className?: string;
}

function useLayerY(progress: MotionValue<number>, distance: number, enabled: boolean) {
  return useTransform(progress, (v) => (enabled ? v * distance : 0));
}

function StormSceneImpl({
  severity,
  accessBlocked,
  crews,
  variant = 'hero',
  scrollTarget,
  className = '',
}: StormSceneProps) {
  const reduce = useReducedMotion();
  const rootRef = useRef<HTMLDivElement>(null);
  const paused = usePauseWhenHidden(rootRef);
  const { scrollYProgress } = useScroll({ target: scrollTarget, offset: ['start start', 'end start'] });
  const parallax = variant === 'hero' && !reduce;
  const farY = useLayerY(scrollYProgress, 90, parallax);
  const stormY = useLayerY(scrollYProgress, 55, parallax);
  const islandY = useLayerY(scrollYProgress, 28, parallax);
  const nearY = useLayerY(scrollYProgress, -70, parallax);

  const p = variant === 'hero' ? 'srh' : 'srw';
  const cfg = SEVERITY[severity];
  const isWindow = variant === 'window';
  const canopyShift = isWindow ? 110 : 0;
  const crewCount = Math.max(0, Math.min(10, Math.round(crews)));

  return (
    <div
      ref={rootRef}
      className={`scene scene--${variant} ${className}`}
      data-severity={severity}
      data-paused={paused ? 'true' : 'false'}
      style={{ '--rain-dur': cfg.dur } as CSSProperties}
    >
      <svg
        viewBox={isWindow ? '110 150 990 560' : '0 0 1200 840'}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label={`Illustrative scenario: a small neighborhood on a floating island under a simulated ${severity} storm. Access route ${
          accessBlocked ? 'blocked' : 'clear'
        }. ${crewCount} symbolic crew marker${crewCount === 1 ? '' : 's'}. Not a map, live weather, or outage status.`}
        focusable="false"
      >
        <Defs p={p} rainY={130 + canopyShift} />
        <motion.g style={{ y: farY }}>
          <FarIslets />
          <Cloud x={70} y={400} s={0.8} puffs={PUFF_B} tone={TONE.far} drift="d2" opacity={0.7} />
          <Cloud x={900} y={330} s={1} puffs={PUFF_A} tone={TONE.far} drift="d3" opacity={0.6} />
          <Cloud x={450} y={352} s={0.65} puffs={PUFF_B} tone={TONE.far} drift="d4" opacity={0.55} />
          <Birds opacity={cfg.birds} />
        </motion.g>
        <g>
          <Cloud x={260} y={722} s={0.9} puffs={PUFF_C} tone={TONE.seaBack} drift="d2" />
          <Cloud x={820} y={708} s={1} puffs={PUFF_C} tone={TONE.seaBack} drift="d3" />
          <Cloud x={560} y={766} s={0.8} puffs={PUFF_A} tone={TONE.seaBack} drift="d1" />
        </g>
        {severity === 'high' && <HighRain p={p} layer="back" />}
        <motion.g style={{ y: islandY }}>
          <Island p={p} accessBlocked={accessBlocked} crews={crewCount} />
        </motion.g>
        <motion.g style={{ y: stormY }}>
          <g transform={canopyShift ? `translate(0 ${canopyShift})` : undefined}>
            <StormCanopy cfg={cfg} high={severity === 'high'} />
          </g>
          {severity === 'high' ? <HighRain p={p} layer="front" /> : <Rain p={p} count={cfg.rain} />}
        </motion.g>
        {!isWindow && (
          <motion.g style={{ y: nearY }}>
            {/* Foreground cloud bank: every cloud (incl. ±28px drift) stays inside the 0–1200 box,
                so nothing is sliced by the illustration's edge and nothing can reach the copy. */}
            <Cloud x={150} y={758} s={1.15} puffs={PUFF_C} tone={TONE.sea} drift="d1" />
            <Cloud x={345} y={772} s={1} puffs={PUFF_A} tone={TONE.sea} drift="d3" />
            <Cloud x={575} y={776} s={1.25} puffs={PUFF_C} tone={TONE.sea} drift="d2" />
            <Cloud x={815} y={768} s={1.05} puffs={PUFF_A} tone={TONE.sea} drift="d4" />
            <Cloud x={915} y={772} s={1} puffs={PUFF_C} tone={TONE.sea} drift="d1" />
            <Cloud x={1010} y={762} s={0.85} puffs={PUFF_A} tone={TONE.sea} drift="d3" />
          </motion.g>
        )}
      </svg>
    </div>
  );
}

export const StormScene = memo(StormSceneImpl);
export default StormScene;
