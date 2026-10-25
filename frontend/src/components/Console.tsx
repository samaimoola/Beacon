'use client';

import { motion } from 'framer-motion';
import CometDial from '@/components/CometDial';
import StormScene from '@/components/scene/StormScene';
import type { Customer, DamageScenario } from '@/lib/api';
import {
  capitalize,
  CREWS_MAX,
  CREWS_MIN,
  DEFAULT_NEEDS,
  NEED_OPTIONS,
  SEVERITIES,
  type DeclaredNeeds,
  type ScenarioInputs,
  type Severity,
} from '@/lib/scenario';

interface ConsoleProps {
  customers: Customer[];
  presets: DamageScenario[] | undefined;
  inputs: ScenarioInputs | null;
  backend: string | null;
  disabled: boolean;
  onCustomer: (id: string) => void;
  onSeverity: (s: Severity) => void;
  onPreset: (id: string) => void;
  onCrews: (n: number) => void;
  onAccess: (b: boolean) => void;
  onNeed: (key: keyof DeclaredNeeds, value: boolean) => void;
  onReset: () => void;
}

const SEVERITY_HINT: Record<Severity, string> = {
  low: 'Minor wind and rain',
  medium: 'Widespread outages possible',
  high: 'Major event, heavy damage',
};

function SeverityGlyph({ s }: { s: Severity }) {
  const drops = s === 'low' ? 1 : s === 'medium' ? 2 : 3;
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
      <path d="M6 13a4 4 0 0 1 .6-8 5 5 0 0 1 9.6 1.4A3.4 3.4 0 0 1 17.5 13z" fill="currentColor" opacity=".9" />
      {Array.from({ length: drops }, (_, i) => (
        <path key={i} d={`M${8 + i * 4} 16l-1 3`} stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      ))}
    </svg>
  );
}

export default function Console({
  customers,
  presets,
  inputs,
  backend,
  disabled,
  onCustomer,
  onSeverity,
  onPreset,
  onCrews,
  onAccess,
  onNeed,
  onReset,
}: ConsoleProps) {
  const severity = inputs?.stormSeverity ?? 'medium';
  const crews = inputs?.availableCrews ?? 4;
  const access = inputs?.accessBlocked ?? false;
  const needs = inputs?.declaredNeeds ?? DEFAULT_NEEDS;
  const preset = presets?.find((p) => p.id === inputs?.damageScenario);

  return (
    <div className="console">
      <div className="scene-window" data-severity={severity}>
        <StormScene severity={severity} accessBlocked={access} crews={crews} variant="window" />
        <div className="pointer-events-none absolute inset-x-0 bottom-0 flex flex-wrap items-center gap-1.5 bg-gradient-to-t from-storm-950/80 to-transparent px-3 pb-2.5 pt-6 text-[0.7rem] text-ivory/90">
          <span className="chip chip--dark">Illustrative scenario</span>
          <span>{capitalize(severity)} storm</span>
          <span aria-hidden="true">·</span>
          <span>Access {access ? 'blocked' : 'clear'}</span>
          <span aria-hidden="true">·</span>
          <span>Crew markers ×{crews}</span>
        </div>
      </div>

      <form className="px-2 pt-2" onSubmit={(e) => e.preventDefault()} aria-label="Scenario controls">
        {/* Household */}
        <fieldset className="console__row" disabled={disabled}>
          <label htmlFor="household" className="console__label">
            <span className="console__num">i.</span>Household
            {backend === 'demo' ? (
              <span className="chip chip--proto ml-auto">Synthetic</span>
            ) : (
              <span className="chip chip--sim ml-auto">Anonymized</span>
            )}
          </label>
          <div className="field">
            <select id="household" value={inputs?.customerId ?? ''} onChange={(e) => onCustomer(e.target.value)}>
              {customers.length === 0 && <option value="">Waiting for the engine…</option>}
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
        </fieldset>

        {/* Severity */}
        <fieldset className="console__row" disabled={disabled}>
          <legend className="console__label w-full">
            <span className="console__num">ii.</span>Storm severity
            <span className="chip chip--sim ml-auto">Simulated</span>
          </legend>
          <div className="segmented">
            {SEVERITIES.map((s) => {
              const checked = s === severity;
              return (
                <label key={s} className="segmented__opt" data-checked={checked ? 'true' : 'false'}>
                  <input
                    type="radio"
                    name="severity"
                    value={s}
                    checked={checked}
                    onChange={() => onSeverity(s)}
                    className="sr-only-input"
                  />
                  <span className="segmented__face">
                    <SeverityGlyph s={s} />
                    {capitalize(s)}
                  </span>
                  {checked && (
                    <motion.span
                      layoutId="severity-pill"
                      className="segmented__pill"
                      transition={{ type: 'spring', stiffness: 420, damping: 36 }}
                    />
                  )}
                </label>
              );
            })}
          </div>
          <p className="console__hint">{SEVERITY_HINT[severity]} — a scenario input, not a forecast.</p>
        </fieldset>

        {/* Damage preset */}
        <fieldset className="console__row" disabled={disabled || !presets}>
          <label htmlFor="preset" className="console__label">
            <span className="console__num">iii.</span>Damage preset
            <span className="chip chip--sim ml-auto">Simulated</span>
          </label>
          <div className="field">
            <select id="preset" value={inputs?.damageScenario ?? ''} onChange={(e) => onPreset(e.target.value)}>
              {!presets && <option value="">Loading presets for this household…</option>}
              {presets?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          {preset && (
            <p className="console__hint">
              {preset.description}
              {preset.damaged_assets.length > 0 && (
                <span className="mt-1 flex flex-wrap gap-1.5">
                  {preset.damaged_assets.map((a) => (
                    <span key={a.asset_type} className="chip bg-ivory-200 text-ink-soft">
                      {a.asset_type} ×{a.quantity}
                    </span>
                  ))}
                </span>
              )}
            </p>
          )}
        </fieldset>

        {/* Crews + access side by side on wide consoles */}
        <div className="grid gap-0 sm:grid-cols-[1.15fr_1fr]">
          <fieldset className="console__row sm:pr-4" disabled={disabled}>
            <legend className="console__label">
              <span className="console__num">iv.</span>Available crews
            </legend>
            <div className="flex items-center justify-center gap-3">
              <button
                type="button"
                className="crew-btn"
                aria-label="One fewer crew"
                onClick={() => onCrews(Math.max(CREWS_MIN, crews - 1))}
                disabled={disabled || crews <= CREWS_MIN}
              >
                −
              </button>
              <CometDial
                value={crews}
                min={CREWS_MIN}
                max={CREWS_MAX}
                step={1}
                unit=" crews"
                label="Available repair crews (simulated, 1 to 10)"
                accent="#8a520c"
                ink="#1b2829"
                size={142}
                thickness={6}
                disabled={disabled}
                onChange={onCrews}
              />
              <button
                type="button"
                className="crew-btn"
                aria-label="One more crew"
                onClick={() => onCrews(Math.min(CREWS_MAX, crews + 1))}
                disabled={disabled || crews >= CREWS_MAX}
              >
                +
              </button>
            </div>
            <p className="console__hint text-center">Drag, use arrow keys, or the buttons. Simulated count.</p>
          </fieldset>

          <fieldset className="console__row sm:border-l sm:border-l-[color:var(--line)] sm:pl-4" disabled={disabled}>
            <legend className="console__label">
              <span className="console__num">v.</span>Access
            </legend>
            <label className="switch">
              <input
                type="checkbox"
                role="switch"
                aria-checked={access}
                checked={access}
                onChange={(e) => onAccess(e.target.checked)}
                className="sr-only-input"
              />
              <span className="switch__track">
                <span className="switch__thumb" />
              </span>
              <span>{access ? 'Route blocked' : 'Route clear'}</span>
            </label>
            <p className="console__hint">
              Road damage, flooding, or debris delaying crews. Affects restoration time only, not outage likelihood.
            </p>
            <button type="button" className="btn btn--ghost mt-4 w-full" onClick={onReset} disabled={customers.length === 0}>
              <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
                <path d="M4 10a6 6 0 1 0 2-4.5M4 3v3.5h3.5" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Reset scenario
            </button>
            <p className="console__hint">Restores defaults and clears the comparison, chat, and declared needs.</p>
          </fieldset>
        </div>

        {/* Declared needs — explicit, optional, session-only */}
        <fieldset className="console__row" disabled={disabled} aria-describedby="needs-hint">
          <legend className="console__label w-full">
            <span className="console__num">vi.</span>Declared needs
            <span className="chip chip--proto ml-auto">Optional · your choice</span>
          </legend>
          <div className="space-y-2.5">
            {NEED_OPTIONS.map((o) => (
              <label key={o.key} className="flex cursor-pointer items-start gap-2.5 text-[0.9rem] leading-snug">
                <input
                  type="checkbox"
                  className="check mt-px shrink-0"
                  checked={needs[o.key]}
                  onChange={(e) => onNeed(o.key, e.target.checked)}
                />
                <span>{o.label}</span>
              </label>
            ))}
          </div>
          <p id="needs-hint" className="console__hint mt-2">
            Only what you tick — never inferred from the household. Kept in this tab only. Tailors guidance and notice
            wording; it doesn&apos;t change risk, repair time, crews, or AEP priority.
          </p>
        </fieldset>
      </form>
    </div>
  );
}
