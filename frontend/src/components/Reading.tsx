'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import type { Connection } from '@/hooks/useStormReady';
import {
  anyNeeds,
  capitalize,
  describeNeeds,
  classifyFactor,
  formatWindow,
  inputChanges,
  PROVENANCE_LABEL,
  resultChanges,
  windowKind,
  type EvaluatedScenario,
  type Provenance,
} from '@/lib/scenario';

interface ReadingProps {
  current: EvaluatedScenario | null;
  previous: EvaluatedScenario | null;
  isUpdating: boolean;
  isStale: boolean;
  evalError: string | null;
  connection: Connection;
  backend: string | null;
  checked: Record<string, boolean>;
  onToggleCheck: (key: string) => void;
  onRetry: () => void;
  retrying?: boolean;
}

const BANDS = ['Low', 'Moderate', 'High', 'Critical'];
const BAND_COLOR: Record<string, string> = {
  Low: '#3d6d60',
  Moderate: '#8a520c',
  High: '#a8432f',
  Critical: '#7d2a1d',
};
const EVIDENCE = ['Low', 'Medium', 'High'];

const PROV_COLOR: Record<Provenance, string> = {
  real: '#3d6d60',
  historical: '#8a520c',
  simulated: '#24545a',
  assumption: '#a8432f',
  engine: '#5c6761',
  synthetic: '#8a520c',
};

const fade = { initial: { opacity: 0, y: 6 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -4 } };

function FactorList({ items, backend, limit }: { items: string[]; backend: string | null; limit?: number }) {
  const [open, setOpen] = useState(false);
  const shown = limit && !open ? items.slice(0, limit) : items;
  return (
    <>
      <ul className="space-y-3">
        {shown.map((f, i) => {
          const prov = classifyFactor(f, backend);
          return (
            <li key={`${i}-${f}`} className="flex gap-3 text-[0.92rem] leading-relaxed">
              <span className="dot mt-[0.55rem]" style={{ background: PROV_COLOR[prov] }} aria-hidden="true" />
              <span>
                <span className="eyebrow mr-1.5 !text-[0.62rem]" style={{ color: PROV_COLOR[prov] }}>
                  {PROVENANCE_LABEL[prov]}
                </span>
                <span className="text-ink-soft">{f}</span>
              </span>
            </li>
          );
        })}
      </ul>
      {limit && items.length > limit && (
        <button
          type="button"
          className="mt-3 text-sm font-semibold text-seaglass-deep underline decoration-seaglass/50 underline-offset-4 hover:decoration-seaglass-deep"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
        >
          {open ? 'Show fewer' : `Show all ${items.length} drivers`}
        </button>
      )}
    </>
  );
}

function Ruler({ lo, hi }: { lo: number; hi: number }) {
  const max = Math.max(12, Math.ceil(hi / 12) * 12);
  const ticks = [0, max / 4, max / 2, (3 * max) / 4, max];
  return (
    <div className="ruler mt-5" aria-hidden="true">
      <div className="ruler__track">
        <motion.div
          className="ruler__band"
          initial={false}
          animate={{ x: `${(lo / max) * 100}%`, scaleX: Math.max(0.01, (hi - lo) / max) }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        />
      </div>
      <div className="mt-1.5 flex justify-between text-[0.68rem] font-semibold text-ink-faint tabular">
        {ticks.map((t) => (
          <span key={t}>{t}h</span>
        ))}
      </div>
    </div>
  );
}

export default function Reading({
  current,
  previous,
  isUpdating,
  isStale,
  evalError,
  connection,
  backend,
  checked,
  onToggleCheck,
  onRetry,
  retrying = false,
}: ReadingProps) {
  if (!current) {
    return (
      <div className="flex min-h-[420px] flex-col items-start justify-center rounded-[28px] border border-dashed border-[color:var(--line)] p-8">
        {connection === 'offline' || evalError ? (
          <>
            <p className="eyebrow text-coral-deep">Engine disconnected</p>
            <p className="mt-3 max-w-md font-display text-3xl leading-tight">No reading yet — the engine isn&apos;t reachable.</p>
            <p className="mt-3 max-w-md text-sm text-ink-soft">
              Beacon never shows made-up numbers. Start the Python API (<code className="rounded bg-ivory-200 px-1">python api_server.py</code>) and retry.
            </p>
            {evalError && <p className="mt-2 text-xs text-ink-faint">{evalError}</p>}
            <button type="button" className="btn btn--ink mt-5" onClick={onRetry} disabled={retrying}>
              {retrying ? 'Retrying…' : 'Retry connection'}
            </button>
          </>
        ) : (
          <>
            <p className="eyebrow text-seaglass-deep">
              Reading the scenario<span className="updating-dots" aria-hidden="true"><span /><span /><span /></span>
            </p>
            <div className="mt-4 h-16 w-2/3 animate-pulse rounded-2xl bg-ivory-200" />
            <div className="mt-3 h-4 w-1/2 animate-pulse rounded bg-ivory-200" />
          </>
        )}
      </div>
    );
  }

  const r = current.result;
  const kind = windowKind(r);
  const bandIdx = BANDS.indexOf(r.risk_band);
  const bandColor = BAND_COLOR[r.risk_band] ?? '#1b2829';
  const evIdx = EVIDENCE.indexOf(r.evidence_quality);
  const prepKey = (a: string) => `${current.inputs.customerId}::${a}`;
  const ins = previous ? inputChanges(previous, current) : [];
  const outs = previous ? resultChanges(previous, current) : [];
  const dimmed = isStale ? 'opacity-70' : 'opacity-100';

  return (
    <div className="relative">
      {/* status line */}
      <div className="flex min-h-[2rem] flex-wrap items-center gap-2 text-sm">
        <span className="text-ink-faint">For</span>
        <span className="font-semibold">{current.customerLabel}</span>
        <span className="text-ink-faint">·</span>
        <span>{capitalize(current.inputs.stormSeverity)} storm</span>
        <span className="text-ink-faint">·</span>
        <span>{current.scenarioLabel ?? 'No preset'}</span>
        <span className="text-ink-faint">·</span>
        <span>
          {current.inputs.availableCrews} crew{current.inputs.availableCrews === 1 ? '' : 's'}, access{' '}
          {current.inputs.accessBlocked ? 'blocked' : 'clear'}
        </span>
        <AnimatePresence>
          {isUpdating && (
            <motion.span {...fade} className="chip chip--sim ml-auto" role="status">
              Updating reading<span className="updating-dots" aria-hidden="true"><span /><span /><span /></span>
            </motion.span>
          )}
        </AnimatePresence>
      </div>
      {(evalError || connection === 'offline') && (
        <div role="alert" className="mt-3 flex flex-wrap items-center gap-3 rounded-2xl bg-coral-pale px-4 py-3 text-sm text-coral-deep">
          <strong>{isStale ? 'Couldn\u2019t update.' : 'Engine disconnected.'}</strong>
          <span>
            {isStale
              ? 'Showing the last engine result for the inputs listed above — it does not match your current controls.'
              : 'This reading matches your controls but was calculated before the connection dropped.'}
          </span>
          <button
            type="button"
            className="btn btn--ghost !min-h-[34px] !px-3 text-xs"
            onClick={onRetry}
            disabled={retrying}
          >
            {retrying ? 'Retrying…' : 'Retry'}
          </button>
        </div>
      )}

      <div className={`transition-opacity duration-500 ${dimmed}`}>
        {/* ---------- Restoration: the hero number ---------- */}
        <div className="mt-6">
          <p className="eyebrow text-ink-faint">Modeled restoration range · heuristic scenario band</p>
          <div className="mt-2 min-h-[5.5rem]">
            <AnimatePresence mode="wait" initial={false}>
              <motion.div key={formatWindow(r)} {...fade} transition={{ duration: 0.28 }}>
                {kind === 'range' && (
                  <p className="font-display tabular leading-none" style={{ fontVariationSettings: "'opsz' 144, 'SOFT' 50" }}>
                    <span className="text-[clamp(3.4rem,8vw,6.2rem)] font-[380] tracking-tight">
                      {(r.restoration_low_hours as number).toFixed(1)}
                      <span className="mx-2 text-ink-faint">–</span>
                      {(r.restoration_high_hours as number).toFixed(1)}
                    </span>
                    <span className="ml-3 align-top text-xl font-[500] text-ink-soft">hours</span>
                  </p>
                )}
                {kind === 'none' && (
                  <div>
                    <p className="font-display text-[clamp(2.6rem,6vw,4.4rem)] font-[400] leading-none text-seaglass-deep">
                      No repairs modeled
                    </p>
                    <p className="mt-3 max-w-xl text-[0.95rem] text-ink-soft">
                      This preset models no equipment damage, so there is no repair work to schedule. It does{' '}
                      <strong>not</strong> guarantee uninterrupted power in a real storm.
                    </p>
                  </div>
                )}
                {kind === 'unknown' && (
                  <div>
                    <p className="font-display text-[clamp(2.8rem,7vw,5rem)] font-[400] leading-none text-lamp-deep">Unknown</p>
                    <p className="mt-3 max-w-xl text-[0.95rem] text-ink-soft">
                      The engine can&apos;t map this scenario to labor references (or has no crews to schedule), so it
                      doesn&apos;t estimate a duration rather than invent one.
                    </p>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          </div>
          {kind === 'range' && <Ruler lo={r.restoration_low_hours as number} hi={r.restoration_high_hours as number} />}
          <p className="mt-3 text-xs leading-relaxed text-ink-faint">
            An unvalidated heuristic: the low–high band is an assumed range around the engine&apos;s scheduled repair
            time — not a statistical confidence interval or a restoration commitment.
          </p>
        </div>

        {/* ---------- Instrument strip ---------- */}
        <div className="mt-8 grid gap-6 border-y border-[color:var(--line)] py-6 sm:grid-cols-3 sm:gap-0 sm:divide-x sm:divide-[color:var(--line)]">
          <div className="sm:pr-6">
            <p className="eyebrow text-ink-faint">Outage-risk band</p>
            <p className="mt-2 font-display text-[2.4rem] leading-none" style={{ color: bandColor }}>
              {r.risk_band}
            </p>
            <div className="meter mt-3 grid-cols-4" aria-hidden="true">
              {BANDS.map((b, i) => (
                <span key={b} style={{ background: i <= bandIdx ? bandColor : undefined }} />
              ))}
            </div>
            <p className="mt-2 text-xs text-ink-faint">A band from scenario rules — not a probability.</p>
          </div>
          <div className="sm:px-6">
            <p className="eyebrow text-ink-faint">Evidence quality</p>
            <p className="mt-2 font-display text-[2.4rem] leading-none text-storm-600">{r.evidence_quality}</p>
            <div className="meter mt-3 grid-cols-3" aria-hidden="true">
              {EVIDENCE.map((e, i) => (
                <span key={e} style={{ background: i <= evIdx ? '#336a6e' : undefined }} />
              ))}
            </div>
            <p className="mt-2 text-xs text-ink-faint">How much real data supports the inputs — not prediction accuracy.</p>
          </div>
          <div className="sm:pl-6">
            <p className="eyebrow text-ink-faint">Prototype alert rule</p>
            <p className={`mt-2 font-display text-[2.4rem] leading-none ${r.alert_eligible ? 'text-seaglass-deep' : 'text-ink-faint'}`}>
              {r.alert_eligible ? 'Eligible' : 'Not eligible'}
            </p>
            <p className="mt-3 text-xs text-ink-faint">
              Beacon&apos;s documented prototype rule only — not AEP enrollment, program qualification, or
              restoration priority.
            </p>
          </div>
        </div>

        {/* ---------- Why ---------- */}
        <div className="mt-10 grid gap-10 md:grid-cols-2">
          <div>
            <h3 className="font-display text-2xl">Why this risk band</h3>
            <div className="mt-4">
              <FactorList items={r.risk_factors} backend={backend} />
            </div>
          </div>
          <div>
            <h3 className="font-display text-2xl">What drives the range</h3>
            <div className="mt-4">
              <FactorList items={r.restoration_factors} backend={backend} limit={4} />
            </div>
          </div>
        </div>
      </div>

      {/* ---------- What changed ---------- */}
      <div className="mt-12 rounded-[26px] bg-seaglass-pale/70 p-6 sm:p-7">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h3 className="font-display text-2xl">What changed</h3>
          <span className="text-xs text-ink-faint">Compared with the previous meaningful scenario</span>
        </div>
        {!previous ? (
          <p className="mt-3 max-w-xl text-sm text-ink-soft">
            Change a control to compare with this reading. The baseline only moves when a new scenario is evaluated —
            ticking the checklist or scrolling never changes it.
          </p>
        ) : (
          <div className="mt-4 grid gap-6 md:grid-cols-2">
            <div>
              <p className="eyebrow text-seaglass-deep">You changed</p>
              <ul className="mt-2">
                {ins.length === 0 && <li className="py-2 text-sm text-ink-soft">No input differences.</li>}
                {ins.map((c) => (
                  <li key={c.label} className="ledger-row flex flex-wrap items-center gap-x-2 py-2 text-sm">
                    <span className="w-28 shrink-0 text-ink-faint">{c.label}</span>
                    <span className="text-ink-soft line-through decoration-ink-faint/50">{c.before}</span>
                    <span aria-hidden="true">→</span>
                    <span className="font-semibold">{c.after}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="eyebrow text-seaglass-deep">The engine now reads</p>
              <ul className="mt-2">
                {outs.length === 0 && (
                  <li className="py-2 text-sm text-ink-soft">Risk band, restoration range, and alert rule stayed the same.</li>
                )}
                {outs.map((c) => (
                  <li key={c.label} className="ledger-row flex flex-wrap items-center gap-x-2 py-2 text-sm">
                    <span className="w-36 shrink-0 text-ink-faint">{c.label}</span>
                    <span className="text-ink-soft">{c.before}</span>
                    <span aria-hidden="true">→</span>
                    <span className="font-semibold">{c.after}</span>
                    {c.note && <span className="chip chip--sim">{c.note}</span>}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* ---------- Checklist + provenance ---------- */}
      <div className="mt-12 grid gap-10 lg:grid-cols-[1.1fr_1fr]">
        <div className="notebook -rotate-[0.4deg] p-6 pl-8 sm:p-7 sm:pl-10">
          <h3 className="font-display text-2xl">Preparation checklist</h3>
          <p className="mt-1 text-xs text-ink-faint">Engine-approved guidance. Ticking items is just for you.</p>
          {anyNeeds(current.inputs.declaredNeeds) && (
            <p className="mt-2 rounded-xl bg-lamp-pale/70 px-3 py-2 text-xs leading-relaxed text-lamp-deep">
              <strong>Tailored for what you declared</strong> ({describeNeeds(current.inputs.declaredNeeds)}) — listed
              first. Risk and restoration above are unchanged by it.
            </p>
          )}
          <ul className="mt-5 space-y-3">
            {r.preparation_actions.map((a) => {
              const k = prepKey(a);
              const id = `prep-${k.replace(/[^a-z0-9]/gi, '-').slice(0, 80)}`;
              return (
                <li key={k} className="flex items-start gap-3">
                  <input id={id} type="checkbox" className="check" checked={!!checked[k]} onChange={() => onToggleCheck(k)} />
                  <label htmlFor={id} className={`cursor-pointer text-[0.95rem] leading-snug transition-colors ${checked[k] ? 'text-ink-faint line-through' : ''}`}>
                    {a}
                  </label>
                </li>
              );
            })}
          </ul>
        </div>

        <div>
          <h3 className="font-display text-2xl">Data provenance</h3>
          <ul className="mt-4 space-y-3 text-sm">
            {backend === 'demo' ? (
              <li className="flex gap-3">
                <span className="dot mt-1.5" style={{ background: PROV_COLOR.synthetic }} />
                <span><strong>Synthetic demo.</strong> These households and estimates are fictional.</span>
              </li>
            ) : (
              <>
                <li className="flex gap-3">
                  <span className="dot mt-1.5" style={{ background: PROV_COLOR.real }} />
                  <span><strong>Real references, anonymized.</strong> Network topology, equipment types, and labor install/removal hours.</span>
                </li>
                <li className="flex gap-3">
                  <span className="dot mt-1.5" style={{ background: PROV_COLOR.historical }} />
                  <span><strong>Historical context.</strong> Prior damage on this circuit — never evidence of current damage.</span>
                </li>
              </>
            )}
            <li className="flex gap-3">
              <span className="dot mt-1.5" style={{ background: PROV_COLOR.simulated }} />
              <span><strong>Simulated conditions.</strong> Storm, damage preset, crews, and access are inputs you choose.</span>
            </li>
          </ul>
          <p className="mt-5 rounded-2xl bg-ivory-200 px-4 py-3 text-xs leading-relaxed text-ink-soft">
            <span className="eyebrow mb-1 block !text-[0.6rem] text-ink-faint">Engine source label</span>
            {r.source_label}
          </p>
          <details className="group mt-4">
            <summary className="cursor-pointer list-none text-sm font-semibold text-seaglass-deep">
              <span className="inline-block transition-transform group-open:rotate-90" aria-hidden="true">›</span>{' '}
              Assumptions &amp; caveats ({r.assumptions.length})
            </summary>
            <ul className="mt-3 space-y-2 border-l-2 border-[color:var(--line)] pl-4 text-[0.85rem] leading-relaxed text-ink-soft">
              {r.assumptions.map((a) => (
                <li key={a}>{a}</li>
              ))}
            </ul>
          </details>
        </div>
      </div>
    </div>
  );
}
