/**
 * Scenario helpers shared by the React UI. Pure functions only: every number
 * shown comes from an engine result; these helpers only format and compare.
 */
import type { DeclaredNeedsPayload, ScenarioInputsPayload, ScenarioResult } from './api';

export type Severity = 'low' | 'medium' | 'high';
export const SEVERITIES: Severity[] = ['low', 'medium', 'high'];

export const CREWS_MIN = 1;
export const CREWS_MAX = 10;
export const DEFAULT_SEVERITY: Severity = 'medium';
export const DEFAULT_CREWS = 4;
export const DEFAULT_ACCESS = false;

/**
 * Optional, explicit customer declarations. Never inferred from the household or
 * data; held in React state only (no storage, no logging). They tailor guidance
 * and notice wording only — the engine keeps risk and restoration unchanged.
 */
export interface DeclaredNeeds {
  medicalEquipment: boolean;
  accessibilityAssistance: boolean;
}
export const DEFAULT_NEEDS: DeclaredNeeds = { medicalEquipment: false, accessibilityAssistance: false };

export const NEED_OPTIONS: { key: keyof DeclaredNeeds; label: string; short: string }[] = [
  { key: 'medicalEquipment', label: 'I rely on electricity-dependent medical equipment.', short: 'Medical equipment' },
  { key: 'accessibilityAssistance', label: 'I may need accessibility assistance during an outage.', short: 'Accessibility assistance' },
];

export const anyNeeds = (n: DeclaredNeeds) => n.medicalEquipment || n.accessibilityAssistance;

/** Mirrors engine/needs.describe_declared_needs. */
export const describeNeeds = (n: DeclaredNeeds) =>
  NEED_OPTIONS.filter((o) => n[o.key]).map((o) => o.short).join('; ') || 'None declared';

export const needsPayload = (n: DeclaredNeeds): DeclaredNeedsPayload => ({
  medical_equipment: n.medicalEquipment,
  accessibility_assistance: n.accessibilityAssistance,
});

export interface ScenarioInputs {
  customerId: string;
  stormSeverity: Severity;
  availableCrews: number;
  accessBlocked: boolean;
  damageScenario: string | null;
  declaredNeeds: DeclaredNeeds;
}

/** A result paired with the exact inputs (and labels) that produced it. */
export interface EvaluatedScenario {
  key: string;
  inputs: ScenarioInputs;
  result: ScenarioResult;
  customerLabel: string;
  scenarioLabel: string | null;
}

/** Identity of a reading. Includes declared needs so answers/notices about other needs never pass as current. */
export const scenarioKey = (i: ScenarioInputs): string =>
  [
    i.customerId,
    i.stormSeverity,
    i.availableCrews,
    i.accessBlocked ? 1 : 0,
    i.damageScenario ?? '-',
    `n${i.declaredNeeds.medicalEquipment ? 1 : 0}${i.declaredNeeds.accessibilityAssistance ? 1 : 0}`,
  ].join('|');

export const toPayload = (i: ScenarioInputs, customerLabel?: string): ScenarioInputsPayload => ({
  storm_severity: i.stormSeverity,
  available_crews: i.availableCrews,
  access_blocked: i.accessBlocked,
  damage_scenario: i.damageScenario,
  declared_needs: needsPayload(i.declaredNeeds),
  ...(customerLabel ? { customer_label: customerLabel } : {}),
});

export const capitalize = (s: string) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);

// ---------------------------------------------------------------------------
// Restoration window
// ---------------------------------------------------------------------------

export type WindowKind = 'unknown' | 'none' | 'range';

type WindowFields = Pick<ScenarioResult, 'restoration_low_hours' | 'restoration_high_hours'>;

export function windowKind(r: WindowFields): WindowKind {
  const lo = r.restoration_low_hours;
  const hi = r.restoration_high_hours;
  if (lo === null || hi === null || lo === undefined || hi === undefined) return 'unknown';
  if (lo === 0 && hi === 0) return 'none';
  return 'range';
}

/** Mirrors engine/formatting.py: Unknown | No repairs modeled | "x.x–y.y h". */
export function formatWindow(r: WindowFields): string {
  const kind = windowKind(r);
  if (kind === 'unknown') return 'Unknown';
  if (kind === 'none') return 'No repairs modeled';
  return `${(r.restoration_low_hours as number).toFixed(1)}–${(r.restoration_high_hours as number).toFixed(1)} h`;
}

// ---------------------------------------------------------------------------
// Provenance of engine-supplied factor text
// ---------------------------------------------------------------------------

export type Provenance = 'real' | 'historical' | 'simulated' | 'assumption' | 'engine' | 'synthetic';

export const PROVENANCE_LABEL: Record<Provenance, string> = {
  real: 'Real reference · anonymized',
  historical: 'Historical context',
  simulated: 'Simulated condition',
  assumption: 'Labeled assumption',
  engine: 'Engine calculation',
  synthetic: 'Synthetic demo',
};

/** Classify engine factor strings by their own wording (prefixes the engine writes). */
export function classifyFactor(text: string, backend: string | null): Provenance {
  if (backend === 'demo') return 'synthetic';
  const t = text.toLowerCase();
  if (t.startsWith('real data') || t.startsWith('real topology')) return 'real';
  if (t.startsWith('context') || t.includes('historical') || t.includes('prior assessment')) return 'historical';
  if (t.includes('labeled assumption') || t.includes('assumed') || t.includes('unresolved')) return 'assumption';
  if (t.includes('simulated')) return 'simulated';
  return 'engine';
}

// ---------------------------------------------------------------------------
// Comparisons between two evaluated scenarios (no new numbers are computed)
// ---------------------------------------------------------------------------

export interface Change {
  label: string;
  before: string;
  after: string;
  note?: string;
}

export function inputChanges(prev: EvaluatedScenario, curr: EvaluatedScenario): Change[] {
  const rows: Change[] = [];
  const a = prev.inputs;
  const b = curr.inputs;
  if (a.customerId !== b.customerId) rows.push({ label: 'Household', before: prev.customerLabel, after: curr.customerLabel });
  if (a.stormSeverity !== b.stormSeverity)
    rows.push({ label: 'Storm severity', before: capitalize(a.stormSeverity), after: capitalize(b.stormSeverity) });
  if (a.damageScenario !== b.damageScenario)
    rows.push({
      label: 'Damage preset',
      before: prev.scenarioLabel ?? 'None',
      after: curr.scenarioLabel ?? 'None',
    });
  if (a.availableCrews !== b.availableCrews)
    rows.push({ label: 'Crews', before: String(a.availableCrews), after: String(b.availableCrews) });
  if (a.accessBlocked !== b.accessBlocked)
    rows.push({
      label: 'Access route',
      before: a.accessBlocked ? 'Blocked' : 'Clear',
      after: b.accessBlocked ? 'Blocked' : 'Clear',
    });
  if (describeNeeds(a.declaredNeeds) !== describeNeeds(b.declaredNeeds))
    rows.push({ label: 'Declared needs', before: describeNeeds(a.declaredNeeds), after: describeNeeds(b.declaredNeeds) });
  return rows;
}

const midpoint = (r: WindowFields) =>
  windowKind(r) === 'range'
    ? ((r.restoration_low_hours as number) + (r.restoration_high_hours as number)) / 2
    : null;

export function resultChanges(prev: EvaluatedScenario, curr: EvaluatedScenario): Change[] {
  const rows: Change[] = [];
  const p = prev.result;
  const c = curr.result;
  if (p.risk_band !== c.risk_band) rows.push({ label: 'Risk band', before: p.risk_band, after: c.risk_band });
  const pw = formatWindow(p);
  const cw = formatWindow(c);
  if (pw !== cw) {
    const pm = midpoint(p);
    const cm = midpoint(c);
    let note: string | undefined;
    if (pm !== null && cm !== null) note = cm > pm ? 'longer' : cm < pm ? 'shorter' : undefined;
    rows.push({ label: 'Modeled restoration', before: pw, after: cw, note });
  }
  if (p.evidence_quality !== c.evidence_quality)
    rows.push({ label: 'Evidence quality', before: p.evidence_quality, after: c.evidence_quality });
  if (p.alert_eligible !== c.alert_eligible)
    rows.push({
      label: 'Prototype alert rule',
      before: p.alert_eligible ? 'Eligible' : 'Not eligible',
      after: c.alert_eligible ? 'Eligible' : 'Not eligible',
    });
  return rows;
}
