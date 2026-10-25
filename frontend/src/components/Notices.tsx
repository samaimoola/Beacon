'use client';

/**
 * Notice previews — calls the deterministic /api/notification-preview service.
 * Nothing is sent and nobody is enrolled. Lifecycle states are explicit simulated
 * selections; Beacon never infers an outage or restoration from the reading.
 * Customer consent and channels are shown separately from scenario eligibility.
 */
import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  apiClient,
  isAbortError,
  type LifecycleState,
  type NotificationPreferences,
  type NotificationPreview,
} from '@/lib/api';
import type { Connection } from '@/hooks/useStormReady';
import { toPayload, type EvaluatedScenario } from '@/lib/scenario';

const LIFECYCLES: { id: LifecycleState; title: string; note: string }[] = [
  { id: 'pre_storm', title: 'Before the storm', note: 'Advisory for the simulated storm.' },
  { id: 'outage_confirmed', title: 'Outage confirmed', note: 'Shown only because you select it — never inferred from the risk band.' },
  { id: 'restoration_updated', title: 'Estimate updated', note: 'Compares with the previous reading for the same household; only a material change is worth a send.' },
  { id: 'restoration_complete', title: 'Restoration complete', note: 'Shown only because you select it — never inferred from zero repair work.' },
];

const CHANNELS = [
  { id: 'sms', label: 'Text message' },
  { id: 'email', label: 'Email' },
  { id: 'push', label: 'App push' },
];
const CHANNEL_LABEL: Record<string, string> = { sms: 'Text message', email: 'Email', push: 'App push' };

const DEFAULT_PREFS: NotificationPreferences = {
  opted_in: true,
  available_channels: ['sms', 'email', 'push'],
  preferred_channel: null,
};

interface NoticesProps {
  current: EvaluatedScenario | null;
  previous: EvaluatedScenario | null;
  isUpdating: boolean;
  connection: Connection;
  resetCount: number;
}

function Ledger({ label, value, ok, hint }: { label: string; value: string; ok: boolean; hint: string }) {
  return (
    <div className="ledger-row flex items-start gap-3 py-3">
      <span className="dot mt-1.5" style={{ background: ok ? '#3d6d60' : '#a8432f' }} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
          <span className="text-sm font-semibold">{label}</span>
          <span className={`text-sm ${ok ? 'text-seaglass-deep' : 'text-coral-deep'}`}>{value}</span>
        </div>
        <p className="text-xs text-ink-faint">{hint}</p>
      </div>
    </div>
  );
}

function PhoneScreen({ preview }: { preview: NotificationPreview }) {
  const ch = preview.recommended_channel;
  const stateTitle = LIFECYCLES.find((l) => l.id === preview.lifecycle_state)?.title ?? preview.lifecycle_state;
  return (
    <div className="absolute inset-0 flex flex-col px-4 pb-5 pt-12">
      <div className="flex items-center justify-between text-[0.62rem] font-semibold uppercase tracking-[0.16em] text-ivory/80">
        <span>Preview</span>
        <span className="rounded-full bg-ivory/15 px-2 py-0.5">Not sent</span>
      </div>
      <p className="mt-6 text-center font-display text-[1.7rem] leading-none text-ivory">{stateTitle}</p>
      <p className="mt-1 text-center text-[0.68rem] text-ivory/70">Simulated lifecycle state</p>
      <AnimatePresence mode="wait">
        <motion.div
          key={`${preview.lifecycle_state}-${ch ?? 'none'}-${preview.message.length}`}
          initial={{ opacity: 0, y: 14, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          className="mt-5 rounded-[20px] bg-ivory/95 p-3.5 text-ink shadow-lg"
        >
          <div className="flex items-center gap-2 text-[0.66rem] font-semibold text-ink-faint">
            <span className="grid h-5 w-5 place-items-center rounded-md bg-storm-800 text-[0.55rem] text-mist">B</span>
            <span>Beacon (prototype)</span>
            <span className="ml-auto">{ch ? CHANNEL_LABEL[ch] ?? ch : 'No channel'}</span>
          </div>
          {ch === 'email' && <p className="mt-2 text-[0.72rem] font-semibold">Subject: Simulated notice — {stateTitle}</p>}
          <p data-lenis-prevent className="mt-2 max-h-[13.5rem] overflow-y-auto overscroll-contain text-[0.76rem] leading-relaxed" role="region" tabIndex={0} aria-label="Notice preview text">{preview.message}</p>
        </motion.div>
      </AnimatePresence>
      <p className="mt-auto text-center text-[0.62rem] leading-snug text-ivory/75">{preview.simulation_label}</p>
    </div>
  );
}

export default function Notices({ current, previous, isUpdating, connection, resetCount }: NoticesProps) {
  const [lifecycle, setLifecycle] = useState<LifecycleState>('pre_storm');
  const [prefs, setPrefs] = useState<NotificationPreferences>(DEFAULT_PREFS);
  const [preview, setPreview] = useState<NotificationPreview | null>(null);
  const [previewKey, setPreviewKey] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const seq = useRef(0);

  useEffect(() => {
    if (resetCount === 0) return;
    setLifecycle('pre_storm');
    setPrefs(DEFAULT_PREFS);
  }, [resetCount]);

  const samePrev = previous && current && previous.inputs.customerId === current.inputs.customerId ? previous : null;
  const prefsKey = JSON.stringify(prefs);

  useEffect(() => {
    if (!current || connection === 'offline') return;
    const id = ++seq.current;
    const controller = new AbortController();
    const key = `${current.key}|${samePrev?.key ?? '-'}|${lifecycle}|${prefsKey}`;
    const t = window.setTimeout(() => {
      apiClient
        .notificationPreview(
          {
            lifecycle_state: lifecycle,
            inputs: toPayload(current.inputs, current.customerLabel),
            result: current.result,
            prev_result: samePrev?.result ?? null,
            preferences: prefs,
          },
          controller.signal
        )
        .then((p) => {
          if (id !== seq.current) return;
          setPreview(p);
          setPreviewKey(key);
          setError(null);
        })
        .catch((err) => {
          if (isAbortError(err) || id !== seq.current) return;
          setError(err instanceof Error ? err.message : 'Preview failed');
        });
    }, 120);
    return () => {
      window.clearTimeout(t);
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current?.key, samePrev?.key, lifecycle, prefsKey, connection]);

  const toggleChannel = (c: string) =>
    setPrefs((p) => {
      const has = p.available_channels.includes(c);
      const available_channels = has ? p.available_channels.filter((x) => x !== c) : [...p.available_channels, c];
      return {
        ...p,
        available_channels,
        preferred_channel: p.preferred_channel && available_channels.includes(p.preferred_channel) ? p.preferred_channel : null,
      };
    });

  const expectedKey = current ? `${current.key}|${samePrev?.key ?? '-'}|${lifecycle}|${prefsKey}` : null;
  const refreshing = !!preview && (previewKey !== expectedKey || isUpdating);

  return (
    <div>
      <div className="max-w-2xl">
        <p className="eyebrow text-seaglass-deep">04 · Notice previews</p>
        <h2 className="section-title mt-3">
          What a notice <em className="mr-[0.12em] text-seaglass-deep">could</em> say.
        </h2>
        <p className="mt-4 leading-relaxed text-ink-soft">
          Choose a simulated lifecycle moment and the customer&apos;s preferences. Beacon drafts the message from
          the engine&apos;s numbers. These are previews only — nothing is sent, and no one is enrolled.
        </p>
      </div>

      <div className="mt-10 grid items-start gap-10 lg:grid-cols-[1fr_auto_1fr] lg:gap-12">
        {/* lifecycle selection */}
        <fieldset>
          <legend className="eyebrow text-ink-faint">Simulated lifecycle state</legend>
          <p className="mt-1 text-xs text-ink-faint">You choose the moment; nothing here is inferred from the reading.</p>
          <div className="mt-3 space-y-1.5">
            {LIFECYCLES.map((l) => {
              const checked = l.id === lifecycle;
              return (
                <label key={l.id} className="step" data-checked={checked ? 'true' : 'false'}>
                  <input
                    type="radio"
                    name="lifecycle"
                    value={l.id}
                    checked={checked}
                    onChange={() => setLifecycle(l.id)}
                    className="sr-only-input"
                  />
                  <span className="step__mark" aria-hidden="true" />
                  <span>
                    <span className="block text-[0.95rem] font-semibold">{l.title}</span>
                    <span className="block text-xs text-ink-faint">{l.note}</span>
                  </span>
                </label>
              );
            })}
          </div>

          <div className="mt-7 rounded-[22px] border border-[color:var(--line)] bg-ivory-50/80 p-5">
            <p className="eyebrow text-ink-faint">Customer preferences (simulated)</p>
            <label className="switch switch--calm mt-3">
              <input
                type="checkbox"
                role="switch"
                aria-checked={prefs.opted_in}
                checked={prefs.opted_in}
                onChange={(e) => setPrefs((p) => ({ ...p, opted_in: e.target.checked }))}
                className="sr-only-input"
              />
              <span className="switch__track">
                <span className="switch__thumb" />
              </span>
              <span>{prefs.opted_in ? 'Opted in to notices' : 'Opted out of notices'}</span>
            </label>
            <fieldset className="mt-4">
              <legend className="text-sm font-semibold">Channels available</legend>
              <div className="mt-2 flex flex-wrap gap-x-5 gap-y-2">
                {CHANNELS.map((c) => (
                  <label key={c.id} className="flex cursor-pointer items-center gap-2 text-sm">
                    <input type="checkbox" className="check" checked={prefs.available_channels.includes(c.id)} onChange={() => toggleChannel(c.id)} />
                    {c.label}
                  </label>
                ))}
              </div>
            </fieldset>
            <div className="field mt-4">
              <label htmlFor="pref-channel" className="mb-1.5 block text-sm font-semibold">
                Preferred channel
              </label>
              <select
                id="pref-channel"
                value={prefs.preferred_channel ?? ''}
                onChange={(e) => setPrefs((p) => ({ ...p, preferred_channel: e.target.value || null }))}
              >
                <option value="">Automatic (state default)</option>
                {CHANNELS.filter((c) => prefs.available_channels.includes(c.id)).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </fieldset>

        {/* phone */}
        <div className="flex flex-col items-center">
          <div className="phone" role="img" aria-label="Phone illustration showing a simulated, unsent notification preview">
            <div className="phone__notch" />
            <div className="phone__screen">
              {preview ? (
                <PhoneScreen preview={preview} />
              ) : (
                <div className="absolute inset-0 grid place-items-center px-6 text-center text-sm text-ivory/80">
                  {error ?? (connection === 'offline' ? 'Engine disconnected — no preview.' : 'Drafting a preview…')}
                </div>
              )}
            </div>
          </div>
          <p className="mt-3 h-4 text-xs text-ink-faint" role="status">
            {refreshing ? 'Refreshing preview…' : error ? `Preview error: ${error}` : ''}
          </p>
        </div>

        {/* decision */}
        <div className={`transition-opacity duration-300 ${refreshing ? 'opacity-70' : ''}`}>
          <p className="eyebrow text-ink-faint">Delivery decision (simulated)</p>
          {preview ? (
            <>
              <div className="mt-2">
                <Ledger
                  label="Scenario eligibility"
                  value={preview.scenario_eligible ? 'Eligible' : 'Not eligible'}
                  ok={preview.scenario_eligible}
                  hint="From the prototype alert rule on this reading — separate from consent."
                />
                <Ledger
                  label="Customer consent"
                  value={preview.consent_status === 'opted_in' ? 'Opted in' : 'Opted out'}
                  ok={preview.consent_status === 'opted_in'}
                  hint="A simulated preference you control."
                />
                <Ledger
                  label="Channel"
                  value={preview.recommended_channel ? CHANNEL_LABEL[preview.recommended_channel] ?? preview.recommended_channel : 'None available'}
                  ok={preview.channel_available}
                  hint="Preferred channel if available, otherwise the state default."
                />
                {preview.estimate_change && (
                  <Ledger
                    label="Estimate change"
                    value={
                      preview.estimate_change.kind === 'no_previous'
                        ? 'No baseline'
                        : preview.estimate_change.material
                          ? 'Material'
                          : 'Not material'
                    }
                    ok={preview.estimate_change.material}
                    hint="An estimate-update notice needs a material change from the previous reading."
                  />
                )}
              </div>
              <div className={`mt-4 rounded-2xl px-4 py-3 text-sm ${preview.send_recommended ? 'bg-seaglass-pale text-[#2c5a4e]' : 'bg-coral-pale text-coral-deep'}`}>
                {preview.send_recommended ? (
                  <>
                    <strong>A send would be recommended</strong> via{' '}
                    {CHANNEL_LABEL[preview.recommended_channel ?? ''] ?? preview.recommended_channel}. This is a preview —
                    nothing is sent.
                  </>
                ) : (
                  <>
                    <strong>No send recommended.</strong> The preview is still shown.
                    <ul className="mt-1 list-disc pl-5 text-xs">
                      {preview.send_blockers.map((b) => (
                        <li key={b}>{b}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
              <dl className="mt-5 space-y-3 text-sm">
                <div>
                  <dt className="font-semibold">Why this notice</dt>
                  <dd className="text-ink-soft">{preview.trigger_reason}</dd>
                </div>
                <div>
                  <dt className="font-semibold">Timing</dt>
                  <dd className="text-ink-soft">{preview.timing}</dd>
                </div>
                <div>
                  <dt className="font-semibold">Estimate in the message</dt>
                  <dd className="text-ink-soft tabular">{preview.estimate_window}</dd>
                </div>
                {preview.estimate_change && (
                  <div>
                    <dt className="font-semibold">Change vs. previous reading</dt>
                    <dd className="text-ink-soft">
                      {preview.estimate_change.detail}{' '}
                      <span className="chip chip--sim">{preview.estimate_change.material ? 'Material' : 'Not material'}</span>
                    </dd>
                  </div>
                )}
                {preview.unknowns.length > 0 && (
                  <div>
                    <dt className="font-semibold">Unknown or missing</dt>
                    <dd>
                      <ul className="list-disc pl-5 text-ink-soft">
                        {preview.unknowns.map((u) => (
                          <li key={u}>{u}</li>
                        ))}
                      </ul>
                    </dd>
                  </div>
                )}
              </dl>
              <details className="group mt-5">
                <summary className="cursor-pointer list-none text-sm font-semibold text-seaglass-deep">
                  <span className="inline-block transition-transform group-open:rotate-90" aria-hidden="true">›</span> Approved safety guidance
                </summary>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-[0.85rem] text-ink-soft">
                  {preview.safety_guidance.map((g) => (
                    <li key={g}>{g}</li>
                  ))}
                </ul>
              </details>
            </>
          ) : (
            <p className="mt-3 text-sm text-ink-soft">The decision appears once a preview is drafted from the current reading.</p>
          )}
        </div>
      </div>
    </div>
  );
}
