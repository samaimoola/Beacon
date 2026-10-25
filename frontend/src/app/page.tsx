'use client';

import { useCallback, useEffect, useState } from 'react';
import { MotionConfig, motion } from 'framer-motion';
import Nav from '@/components/Nav';
import Hero from '@/components/Hero';
import Console from '@/components/Console';
import Reading from '@/components/Reading';
import Concierge from '@/components/Concierge';
import Notices from '@/components/Notices';
import Footer from '@/components/Footer';
import SmoothScroll from '@/components/SmoothScroll';
import { useStormReady } from '@/hooks/useStormReady';
import { DEFAULT_ACCESS, DEFAULT_CREWS, DEFAULT_SEVERITY } from '@/lib/scenario';

const EASE_OUT: [number, number, number, number] = [0.22, 1, 0.36, 1];

const reveal = {
  initial: { opacity: 0, y: 24 },
  whileInView: { opacity: 1, y: 0 },
  viewport: { once: true, amount: 0.15 },
  transition: { duration: 0.8, ease: EASE_OUT },
};

function CloudEdge({ from, to, flip = false }: { from: string; to: string; flip?: boolean }) {
  return (
    <svg
      className="cloud-edge"
      viewBox="0 0 1440 70"
      preserveAspectRatio="none"
      aria-hidden="true"
      style={{ background: from, transform: flip ? 'scaleY(-1)' : undefined }}
    >
      <path
        d="M0 70 V38 C60 20 120 22 170 34 C220 10 300 6 350 30 C400 16 470 18 520 36 C580 8 680 4 740 30 C800 14 880 16 930 34 C990 6 1090 6 1150 30 C1210 14 1290 16 1340 34 C1380 24 1420 26 1440 32 V70 Z"
        fill={to}
      />
    </svg>
  );
}

export default function Home() {
  const s = useStormReady();
  const [checked, setChecked] = useState<Record<string, boolean>>({});

  // Reset also clears the checklist.
  useEffect(() => {
    if (s.resetCount > 0) setChecked({});
  }, [s.resetCount]);

  const toggleCheck = useCallback((k: string) => setChecked((c) => ({ ...c, [k]: !c[k] })), []);

  const severity = s.inputs?.stormSeverity ?? DEFAULT_SEVERITY;
  const crews = s.inputs?.availableCrews ?? DEFAULT_CREWS;
  const access = s.inputs?.accessBlocked ?? DEFAULT_ACCESS;
  const offline = s.connection === 'offline';
  const synthetic = s.connection === 'online' && s.backend === 'demo';

  return (
    <MotionConfig reducedMotion="user">
      <SmoothScroll />
      <a href="#workspace" className="skip-link">
        Skip to the scenario workspace
      </a>
      <Nav connection={s.connection} backend={s.backend} />

      {(offline || synthetic) && (
        <div
          role="alert"
          data-sticky-top
          className={`sticky top-[var(--nav-h)] z-40 px-4 py-2 text-center text-sm font-semibold ${
            offline ? 'bg-coral text-ink' : 'bg-lamp text-ink'
          }`}
        >
          {offline
            ? 'Engine disconnected — Beacon shows no estimates until the Python API is reachable.'
            : 'Synthetic demo backend — these households and estimates are fictional.'}
          {offline && (
            <button
              type="button"
              onClick={s.retry}
              disabled={s.retrying}
              className="ml-3 underline underline-offset-4 disabled:no-underline disabled:opacity-70"
            >
              {s.retrying ? 'Retrying…' : 'Retry'}
            </button>
          )}
        </div>
      )}

      <main>
        <Hero severity={severity} accessBlocked={access} crews={crews} />
        <CloudEdge from="#3c7473" to="#f6f1e6" />

        {/* ---------------- Workspace ---------------- */}
        <section id="workspace" className="paper pb-20 pt-10" aria-labelledby="workspace-title">
          <div className="container-wide">
            <motion.div {...reveal} className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <p className="eyebrow text-seaglass-deep">01 · Your scenario</p>
                <h2 id="workspace-title" tabIndex={-1} className="section-title mt-3 outline-none">
                  Set the storm. <em className="text-seaglass-deep">Read the plan.</em>
                </h2>
              </div>
              <p className="max-w-sm text-sm text-ink-soft">
                Every control is a simulated input. The engine recalculates as you go, and the last reading stays on
                screen while it updates.
              </p>
            </motion.div>

            <div className="mt-10 grid gap-10 lg:grid-cols-12 lg:gap-12">
              <motion.div {...reveal} className="lg:col-span-5">
                <div className="lg:sticky lg:top-[calc(var(--nav-h)+16px)]">
                  <Console
                    customers={s.customers}
                    presets={s.presets}
                    inputs={s.inputs}
                    backend={s.backend}
                    disabled={s.customers.length === 0}
                    onCustomer={s.selectCustomer}
                    onSeverity={s.setSeverity}
                    onPreset={s.setDamageScenario}
                    onCrews={s.setCrews}
                    onAccess={s.setAccess}
                    onNeed={s.setNeed}
                    onReset={s.reset}
                  />
                </div>
              </motion.div>

              <motion.div {...reveal} id="reading" className="lg:col-span-7" aria-labelledby="reading-title">
                <p className="eyebrow text-seaglass-deep">02 · The reading</p>
                <h2 id="reading-title" className="sr-only">
                  Scenario reading
                </h2>
                <div className="mt-3">
                  <Reading
                    current={s.current}
                    previous={s.previous}
                    isUpdating={s.isUpdating}
                    isStale={s.isStale}
                    evalError={s.evalError}
                    connection={s.connection}
                    backend={s.backend}
                    checked={checked}
                    onToggleCheck={toggleCheck}
                    onRetry={s.retry}
                    retrying={s.retrying}
                  />
                </div>
              </motion.div>
            </div>
          </div>
        </section>

        {/* ---------------- Concierge ---------------- */}
        <CloudEdge from="#f6f1e6" to="#0d2429" />
        <section id="ask" className="concierge grain on-dark py-20" aria-labelledby="ask-title">
          <motion.div {...reveal} className="container-wide">
            <Concierge
              current={s.current}
              previous={s.previous}
              activeKey={s.desiredKey}
              isUpdating={s.isUpdating}
              isStale={s.isStale}
              connection={s.connection}
              resetCount={s.resetCount}
            />
          </motion.div>
        </section>

        {/* ---------------- Notices ---------------- */}
        <section id="notices" className="notices py-20" aria-labelledby="notices-title">
          <motion.div {...reveal} className="container-wide">
            <span id="notices-title" className="sr-only">
              Notice previews
            </span>
            <Notices
              current={s.current}
              previous={s.previous}
              isUpdating={s.isUpdating}
              connection={s.connection}
              resetCount={s.resetCount}
            />
          </motion.div>
        </section>
      </main>

      <Footer />
    </MotionConfig>
  );
}
