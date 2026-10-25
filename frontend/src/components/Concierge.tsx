'use client';

/**
 * Ask Beacon AI — chat over the existing server-side concierge (/api/concierge/ask).
 *
 *  - Calls the provider ONLY on an explicit question or suggested-question click.
 *  - Pending answers use neutral wording; each answer is labeled with the mode the
 *    server actually returned ("live" Bedrock or rule-based "fallback").
 *  - Disabled whenever the reading does not match the selected inputs (loading, or an
 *    evaluation error left an older reading on screen), so it never explains a stale result.
 *  - Declared needs are part of the reading key, so answers about other needs are separated.
 *  - Answers that arrive after the scenario changed are discarded and marked outdated.
 *  - Messages about earlier scenarios are visibly separated; reset clears the chat.
 */
import { Fragment, useEffect, useRef, useState, type ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { apiClient } from '@/lib/api';
import type { Connection } from '@/hooks/useStormReady';
import { anyNeeds, capitalize, describeNeeds, toPayload, type EvaluatedScenario } from '@/lib/scenario';

const SUGGESTED = ['Will I lose power?', 'Why did my estimate change?', 'What should I do now?', 'Would another crew help?'];

interface Msg {
  id: number;
  role: 'user' | 'assistant';
  text: string;
  scenarioKey: string;
  summary: string;
  status: 'pending' | 'done' | 'error' | 'outdated';
  mode?: string;
  providerError?: string | null;
  usedCounterfactual?: boolean;
}

interface ConciergeProps {
  current: EvaluatedScenario | null;
  previous: EvaluatedScenario | null;
  activeKey: string | null;
  isUpdating: boolean;
  /** True when the shown reading does not match the selected inputs. */
  isStale: boolean;
  connection: Connection;
  resetCount: number;
}

const summarize = (s: EvaluatedScenario) =>
  `${s.customerLabel.split(' — ')[0]} · ${capitalize(s.inputs.stormSeverity)} · ${s.scenarioLabel ?? 'no preset'} · ${s.inputs.availableCrews} crew${s.inputs.availableCrews === 1 ? '' : 's'}` +
  (anyNeeds(s.inputs.declaredNeeds) ? ` · needs: ${describeNeeds(s.inputs.declaredNeeds)}` : '');

/** Tiny, safe formatter: **bold**, "- "/"• " bullet lines, paragraphs. No HTML injection. */
function renderText(text: string): ReactNode {
  const lines = text.split(/\n+/);
  const out: ReactNode[] = [];
  let list: string[] = [];
  const bold = (s: string, k: string) =>
    s.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
      part.startsWith('**') && part.endsWith('**') ? <strong key={`${k}-${i}`}>{part.slice(2, -2)}</strong> : <Fragment key={`${k}-${i}`}>{part}</Fragment>
    );
  const flush = (k: number) => {
    if (!list.length) return;
    out.push(
      <ul key={`l${k}`} className="my-1.5 list-disc space-y-1 pl-5">
        {list.map((li, i) => (
          <li key={i}>{bold(li, `li${k}-${i}`)}</li>
        ))}
      </ul>
    );
    list = [];
  };
  lines.forEach((raw, i) => {
    const line = raw.trim();
    if (/^([-•*]|\d+\.)\s+/.test(line)) list.push(line.replace(/^([-•*]|\d+\.)\s+/, ''));
    else {
      flush(i);
      if (line) out.push(<p key={`p${i}`} className="mb-1.5 last:mb-0">{bold(line, `p${i}`)}</p>);
    }
  });
  flush(lines.length);
  return out;
}

function SourceLabel({ m }: { m: Msg }) {
  if (m.status === 'pending')
    return (
      <span className="chip bg-ivory-200 text-ink-soft">
        Answer source pending<span className="updating-dots" aria-hidden="true"><span /><span /><span /></span>
      </span>
    );
  if (m.status === 'outdated') return <span className="chip bg-ivory-200 text-ink-faint">Discarded · scenario changed</span>;
  if (m.status === 'error') return <span className="chip chip--warn">Not answered</span>;
  if (m.mode === 'live')
    return (
      <span className="chip" style={{ background: '#d7e8df', color: '#2c5a4e' }}>
        <span className="dot" style={{ background: '#3d6d60' }} /> Live AI · Amazon Bedrock · grounded in engine results
      </span>
    );
  return (
    <span className="chip chip--proto">
      <span className="dot" style={{ background: '#8a520c' }} /> Rule-based fallback · composed from engine results, not AI-generated
    </span>
  );
}

export default function Concierge({ current, previous, activeKey, isUpdating, isStale, connection, resetCount }: ConciergeProps) {
  const [messages, setMessages] = useState<Msg[]>([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const idRef = useRef(0);
  const epochRef = useRef(0);
  const activeKeyRef = useRef(activeKey);
  activeKeyRef.current = activeKey;
  const abortRef = useRef<AbortController | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  // Reset clears the chat and abandons any in-flight answer.
  useEffect(() => {
    if (resetCount === 0) return;
    epochRef.current += 1;
    abortRef.current?.abort();
    setMessages([]);
    setBusy(false);
    setDraft('');
  }, [resetCount]);

  // Scroll the log (not the page) to the newest message.
  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const reason =
    connection === 'offline'
      ? 'Reconnect the engine to ask questions.'
      : !current
        ? 'Waiting for the first scenario reading…'
        : isUpdating
          ? 'Waiting for the updated reading so answers match your inputs…'
          : isStale || activeKey !== current.key
            ? 'The reading doesn\u2019t match your current controls. Retry the update before asking.'
            : busy
            ? 'Answering your last question…'
            : null;
  const canAsk = reason === null;

  const ask = (question: string) => {
    const q = question.trim();
    if (!q || !canAsk || !current) return;
    const sentKey = current.key;
    const epoch = epochRef.current;
    const uid = ++idRef.current;
    const aid = ++idRef.current;
    const summary = summarize(current);
    setMessages((m) => [
      ...m,
      { id: uid, role: 'user', text: q, scenarioKey: sentKey, summary, status: 'done' },
      { id: aid, role: 'assistant', text: 'Consulting the Beacon engine…', scenarioKey: sentKey, summary, status: 'pending' },
    ]);
    setDraft('');
    setBusy(true);
    const controller = new AbortController();
    abortRef.current = controller;
    apiClient
      .askConcierge(
        {
          question: q,
          customer_id: current.inputs.customerId,
          customer_label: current.customerLabel,
          inputs: toPayload(current.inputs, current.customerLabel),
          prev_customer_id: previous?.inputs.customerId ?? null,
          prev_inputs: previous ? toPayload(previous.inputs, previous.customerLabel) : null,
        },
        controller.signal
      )
      .then((reply) => {
        if (epoch !== epochRef.current) return;
        const stale = activeKeyRef.current !== sentKey;
        setMessages((m) =>
          m.map((x) =>
            x.id !== aid
              ? x
              : stale
                ? { ...x, status: 'outdated', text: 'This answer arrived after the scenario changed, so Beacon discarded it.' }
                : {
                    ...x,
                    status: 'done',
                    text: reply.text,
                    mode: reply.mode,
                    providerError: reply.provider_error,
                    usedCounterfactual: reply.used_counterfactual,
                  }
          )
        );
      })
      .catch((err) => {
        if (epoch !== epochRef.current || (err instanceof DOMException && err.name === 'AbortError')) return;
        setMessages((m) =>
          m.map((x) =>
            x.id === aid ? { ...x, status: 'error', text: `The concierge couldn't answer: ${err instanceof Error ? err.message : 'unknown error'}` } : x
          )
        );
      })
      .finally(() => {
        if (epoch === epochRef.current) setBusy(false);
      });
  };

  const currentKey = current?.key ?? null;
  const earlier = messages.filter((m) => m.scenarioKey !== currentKey);
  const now = messages.filter((m) => m.scenarioKey === currentKey);

  const renderMsg = (m: Msg) => (
    <motion.li
      key={m.id}
      layout="position"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
      className={m.role === 'user' ? 'flex justify-end' : 'flex flex-col items-start gap-1.5'}
    >
      {m.role === 'user' ? (
        <div className="bubble bubble--user">{m.text}</div>
      ) : (
        <>
          <div className={`bubble bubble--bot ${m.status !== 'done' ? 'text-ink-faint' : ''}`}>{renderText(m.text)}</div>
          <div className="flex flex-wrap items-center gap-1.5 pl-1">
            <SourceLabel m={m} />
            {m.usedCounterfactual && <span className="chip chip--dark">Includes an engine-computed crew comparison</span>}
          </div>
          {m.status === 'done' && m.mode !== 'live' && m.providerError && (
            <p className="max-w-[88%] pl-1 text-[0.72rem] text-ivory/55">Why fallback: {m.providerError}</p>
          )}
        </>
      )}
    </motion.li>
  );

  return (
    <div className="grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:gap-14">
      <div>
        <h2 id="ask-title" tabIndex={-1} className="outline-none">
          <span className="eyebrow block text-mist">03 · Ask Beacon AI</span>
          <span className="section-title mt-3 block">
            Questions, <em className="text-mist">answered from the engine.</em>
          </span>
        </h2>
        <p className="mt-5 max-w-md leading-relaxed text-ivory/80">
          Ask what your reading means, why it changed, or what to do now. The concierge runs on the server and only
          explains numbers the Beacon engine already calculated — it never invents probabilities, weather, outages,
          or program eligibility.
        </p>
        <ul className="mt-6 space-y-2 text-sm text-ivory/70">
          <li>• Each answer states its real source: live Amazon Bedrock AI, or a rule-based fallback that is not AI-generated.</li>
          <li>• “Would another crew help?” re-runs the engine with exactly one more crew (up to the 10-crew maximum).</li>
          <li>• Answers are tied to the scenario you asked about; changing inputs separates them.</li>
        </ul>
        {current && (
          <p className="mt-6 inline-flex flex-wrap items-center gap-2 rounded-2xl border border-mist/20 px-3 py-2 text-xs text-ivory/75">
            <span className="eyebrow !text-[0.6rem] text-mist">Asking about</span> {summarize(current)}
          </p>
        )}
      </div>

      <div className="flex min-h-[520px] flex-col rounded-[30px] border border-mist/15 bg-storm-800/60 p-4 sm:p-5">
        <div
          ref={logRef}
          data-lenis-prevent
          role="log"
          aria-label="Beacon AI conversation"
          className="chat-log flex-1 overflow-y-auto overscroll-contain pr-1"
          style={{ maxHeight: 460 }}
          aria-live="polite"
        >
          {messages.length === 0 && (
            <div className="flex h-full min-h-[260px] flex-col items-center justify-center text-center text-ivory/70">
              <svg viewBox="0 0 64 40" width="86" aria-hidden="true">
                <path d="M14 30a10 10 0 0 1 1.6-19.8A13 13 0 0 1 40.4 14 9 9 0 0 1 50 30z" fill="#bfe3e6" opacity=".25" />
                <circle cx="24" cy="22" r="2.2" fill="#f2b45a" />
                <circle cx="32" cy="22" r="2.2" fill="#f2b45a" opacity=".7" />
                <circle cx="40" cy="22" r="2.2" fill="#f2b45a" opacity=".45" />
              </svg>
              <p className="mt-3 max-w-xs text-sm">Pick a suggested question or type your own. Nothing is sent until you ask.</p>
            </div>
          )}
          {earlier.length > 0 && (
            <details className="mb-4 rounded-2xl border border-dashed border-mist/25 p-3 opacity-70">
              <summary className="cursor-pointer text-xs font-semibold text-mist">
                Earlier answers — about a different scenario ({earlier.filter((m) => m.role === 'assistant').length})
              </summary>
              <ul className="mt-3 space-y-3">{earlier.map(renderMsg)}</ul>
            </details>
          )}
          <ul className="space-y-4">
            <AnimatePresence initial={false}>{now.map(renderMsg)}</AnimatePresence>
          </ul>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {SUGGESTED.map((q) => (
            <button key={q} type="button" className="suggest" onClick={() => ask(q)} disabled={!canAsk}>
              {q}
            </button>
          ))}
        </div>
        <form
          className="mt-3 flex items-center gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            ask(draft);
          }}
        >
          <label htmlFor="ask-input" className="sr-only">
            Ask Beacon AI about this scenario
          </label>
          <input
            id="ask-input"
            className="chat-input"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="Ask about this scenario…"
            maxLength={400}
            autoComplete="off"
          />
          <button
            type="submit"
            className="btn btn--lamp !min-h-[48px]"
            aria-label="Ask Beacon AI"
            disabled={!canAsk || !draft.trim()}
          >
            Ask
          </button>
        </form>
        <p className="mt-2 min-h-[1.1rem] text-[0.75rem] text-ivory/60" role="status">
          {reason ?? 'Answers explain the current reading only.'}
        </p>
      </div>
    </div>
  );
}
