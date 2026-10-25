'use client';

/**
 * Scenario state machine for the React UI.
 *
 * Guarantees:
 *  - Older network responses never overwrite newer selections (sequence guard + abort).
 *  - A household is never evaluated with a damage preset from another household:
 *    evaluation waits until that household's presets are loaded and the preset is valid.
 *  - Current and previous results stay attached to the exact inputs that produced them.
 *  - The comparison baseline only advances when a NEW scenario is evaluated, so checklist
 *    ticks, scrolling, and animation never change it. Reset clears it.
 *  - The last result stays mounted while a new one is computed (isUpdating flag).
 *  - Retry always makes a real request (even when the selected inputs match the cached
 *    reading), and "offline" is cleared only after a backend request succeeds.
 *  - Declared needs are part of the inputs (and the reading key) but live only in React
 *    state: no storage, no logging. Reset clears them. Nothing here calls the concierge.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiClient, ApiError, isAbortError, type Customer, type DamageScenario } from '@/lib/api';
import {
  DEFAULT_ACCESS,
  DEFAULT_CREWS,
  DEFAULT_NEEDS,
  DEFAULT_SEVERITY,
  needsPayload,
  scenarioKey,
  type DeclaredNeeds,
  type EvaluatedScenario,
  type ScenarioInputs,
  type Severity,
} from '@/lib/scenario';

export type Connection = 'connecting' | 'online' | 'offline';

const isConnectionFailure = (err: unknown) =>
  err instanceof ApiError && (err.status === null || /not reachable/i.test(err.message));

const presetIsValid = (list: DamageScenario[], id: string | null) =>
  list.length === 0 ? id === null : list.some((s) => s.id === id);

export function useStormReady() {
  const [connection, setConnection] = useState<Connection>('connecting');
  const [connectError, setConnectError] = useState<string | null>(null);
  const [backend, setBackend] = useState<string | null>(null);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [presets, setPresets] = useState<Record<string, DamageScenario[]>>({});
  const [inputs, setInputs] = useState<ScenarioInputs | null>(null);
  const [current, setCurrent] = useState<EvaluatedScenario | null>(null);
  const [previous, setPrevious] = useState<EvaluatedScenario | null>(null);
  const [evalError, setEvalError] = useState<string | null>(null);
  const [resetCount, setResetCount] = useState(0);
  const [retryNonce, setRetryNonce] = useState(0);
  const [retrying, setRetrying] = useState(false);

  const currentRef = useRef<EvaluatedScenario | null>(null);
  const baselineRef = useRef<EvaluatedScenario | null>(null);
  const seqRef = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  // Set by retry(): the next evaluation must hit the backend even if the selected
  // inputs match the cached reading. Consumed only when a request actually starts.
  const forceEvalRef = useRef(false);
  const presetsRef = useRef(presets);
  presetsRef.current = presets;
  const customersRef = useRef(customers);
  customersRef.current = customers;

  // --- connect: backend status + households -------------------------------
  const connect = useCallback(async (signal?: AbortSignal) => {
    setConnection('connecting');
    setConnectError(null);
    try {
      const [status, list] = await Promise.all([
        apiClient.status(signal).catch((e) => {
          if (isAbortError(e)) throw e;
          return null;
        }),
        apiClient.getCustomers(signal),
      ]);
      setBackend(status?.backend ?? null);
      setCustomers(list);
      setConnection('online');
      setRetrying(false);
      setInputs((prev) =>
        prev && list.some((c) => c.id === prev.customerId)
          ? prev
          : list.length
            ? {
                customerId: list[0].id,
                stormSeverity: DEFAULT_SEVERITY,
                availableCrews: DEFAULT_CREWS,
                accessBlocked: DEFAULT_ACCESS,
                damageScenario: null,
                declaredNeeds: DEFAULT_NEEDS,
              }
            : null
      );
    } catch (err) {
      if (isAbortError(err)) return;
      setRetrying(false);
      setConnection('offline');
      setConnectError(err instanceof Error ? err.message : 'Unknown connection error');
    }
  }, []);

  useEffect(() => {
    const c = new AbortController();
    connect(c.signal);
    return () => c.abort();
  }, [connect]);

  // --- damage presets for the selected household --------------------------
  const customerId = inputs?.customerId ?? null;
  useEffect(() => {
    if (!customerId || presets[customerId]) return;
    const c = new AbortController();
    apiClient
      .getDamageScenarios(customerId, c.signal)
      .then((list) => {
        setPresets((p) => ({ ...p, [customerId]: list }));
        // A successful backend request: safe to leave the offline state.
        setConnection('online');
        setRetrying(false);
      })
      .catch((err) => {
        if (isAbortError(err)) return;
        setRetrying(false);
        setEvalError(err instanceof Error ? err.message : 'Could not load damage presets');
        if (isConnectionFailure(err)) setConnection('offline');
      });
    return () => c.abort();
  }, [customerId, presets, retryNonce]);

  // Repair an invalid preset as soon as the household's presets are known.
  useEffect(() => {
    if (!inputs) return;
    const list = presets[inputs.customerId];
    if (!list || presetIsValid(list, inputs.damageScenario)) return;
    setInputs({ ...inputs, damageScenario: list[0]?.id ?? null });
  }, [inputs, presets]);

  const validInputs = useMemo(() => {
    if (!inputs) return null;
    const list = presets[inputs.customerId];
    if (!list || !presetIsValid(list, inputs.damageScenario)) return null;
    return inputs;
  }, [inputs, presets]);
  const desiredKey = validInputs ? scenarioKey(validInputs) : null;

  // --- evaluation ----------------------------------------------------------
  useEffect(() => {
    if (!validInputs || !desiredKey) return;
    // Invalidate anything older immediately, even before the debounce fires.
    abortRef.current?.abort();
    seqRef.current += 1;
    // The cached reading already matches these inputs. Skip the request unless the
    // user asked to retry — a retry must reach the backend to prove it recovered.
    // (Connection status is left untouched here: only a successful request clears it.)
    if (!forceEvalRef.current && currentRef.current?.key === desiredKey) {
      setEvalError(null);
      return;
    }
    const snapshot = validInputs;
    const timer = setTimeout(
      () => {
        forceEvalRef.current = false;
        const controller = new AbortController();
        abortRef.current = controller;
        const id = ++seqRef.current;
        apiClient
          .evaluateScenario(
            {
              customer_id: snapshot.customerId,
              storm_severity: snapshot.stormSeverity,
              available_crews: snapshot.availableCrews,
              access_blocked: snapshot.accessBlocked,
              damage_scenario: snapshot.damageScenario,
              declared_needs: needsPayload(snapshot.declaredNeeds),
            },
            controller.signal
          )
          .then((result) => {
            if (id !== seqRef.current) return; // a newer selection exists
            const list = presetsRef.current[snapshot.customerId] ?? [];
            const next: EvaluatedScenario = {
              key: scenarioKey(snapshot),
              inputs: snapshot,
              result,
              customerLabel:
                customersRef.current.find((c) => c.id === snapshot.customerId)?.label ?? snapshot.customerId,
              scenarioLabel: list.find((s) => s.id === snapshot.damageScenario)?.label ?? snapshot.damageScenario,
            };
            const base = baselineRef.current;
            if (base && base.key !== next.key) setPrevious(base);
            baselineRef.current = next;
            currentRef.current = next;
            setCurrent(next);
            setEvalError(null);
            setConnection('online');
            setRetrying(false);
          })
          .catch((err) => {
            if (isAbortError(err) || id !== seqRef.current) return;
            setRetrying(false);
            setEvalError(err instanceof Error ? err.message : 'Evaluation failed');
            if (isConnectionFailure(err)) setConnection('offline');
          });
      },
      currentRef.current && !forceEvalRef.current ? 220 : 0
    );
    return () => clearTimeout(timer);
    // validInputs identity follows desiredKey; retryNonce forces a re-attempt.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [desiredKey, retryNonce]);

  // --- actions -------------------------------------------------------------
  const update = useCallback((patch: Partial<ScenarioInputs>) => {
    setInputs((i) => (i ? { ...i, ...patch } : i));
  }, []);

  const selectCustomer = useCallback((id: string) => {
    setInputs((i) => {
      if (!i) return i;
      const list = presetsRef.current[id];
      // Keep the same preset only if this household has it; otherwise wait/repair.
      const damageScenario = list
        ? list.some((s) => s.id === i.damageScenario)
          ? i.damageScenario
          : list[0]?.id ?? null
        : i.damageScenario;
      return { ...i, customerId: id, damageScenario };
    });
  }, []);

  const setSeverity = useCallback((s: Severity) => update({ stormSeverity: s }), [update]);
  const setCrews = useCallback((n: number) => update({ availableCrews: n }), [update]);
  const setAccess = useCallback((b: boolean) => update({ accessBlocked: b }), [update]);
  const setDamageScenario = useCallback((id: string) => update({ damageScenario: id }), [update]);
  const setNeed = useCallback(
    (key: keyof DeclaredNeeds, value: boolean) =>
      setInputs((i) => (i ? { ...i, declaredNeeds: { ...i.declaredNeeds, [key]: value } } : i)),
    []
  );

  const reset = useCallback(() => {
    const first = customersRef.current[0];
    if (!first) return;
    const list = presetsRef.current[first.id];
    const def: ScenarioInputs = {
      customerId: first.id,
      stormSeverity: DEFAULT_SEVERITY,
      availableCrews: DEFAULT_CREWS,
      accessBlocked: DEFAULT_ACCESS,
      damageScenario: list ? list[0]?.id ?? null : null,
      declaredNeeds: DEFAULT_NEEDS,
    };
    const cur = currentRef.current;
    // If the defaults are already showing, they become the baseline for the next change;
    // otherwise the first reading after reset has no "previous" comparison.
    baselineRef.current = cur && list && cur.key === scenarioKey(def) ? cur : null;
    setPrevious(null);
    setEvalError(null);
    setInputs(def);
    setResetCount((c) => c + 1);
  }, []);

  // A real recovery attempt. The error and offline banner stay until a request
  // succeeds, so the UI never claims recovery it hasn't observed.
  const retry = useCallback(() => {
    setRetrying(true);
    if (!customersRef.current.length) {
      connect();
      return;
    }
    forceEvalRef.current = true;
    setRetryNonce((n) => n + 1);
  }, [connect]);

  const presetsLoaded = !!inputs && !!presets[inputs.customerId];
  const isStale = !!current && desiredKey !== current.key;
  const isUpdating = !!inputs && (isStale || !current) && !evalError && connection !== 'offline';

  return {
    connection,
    connectError,
    backend,
    customers,
    presets: inputs ? presets[inputs.customerId] : undefined,
    presetsLoaded,
    inputs,
    desiredKey,
    current,
    previous,
    evalError,
    isStale,
    isUpdating,
    retrying,
    resetCount,
    selectCustomer,
    setSeverity,
    setCrews,
    setAccess,
    setDamageScenario,
    setNeed,
    reset,
    retry,
  };
}

export type StormReadyState = ReturnType<typeof useStormReady>;
