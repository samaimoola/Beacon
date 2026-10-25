/**
 * frontend/src/lib/api.ts
 * =======================
 * Typed client for the Beacon FastAPI bridge (api_server.py).
 *
 * Base URL:
 *   - NEXT_PUBLIC_API_URL when set (e.g. http://localhost:8000), otherwise
 *   - same-origin requests to /api/*, which next.config.js proxies to the
 *     Python API. Same-origin works from a phone on the local network too.
 *
 * Non-2xx responses and connection failures throw ApiError. All AWS/Bedrock
 * access stays server-side; nothing here touches credentials.
 */

// ---------------------------------------------------------------------------
// Types (match engine/api.py and api_server.py shapes)
// ---------------------------------------------------------------------------

export interface Customer {
  id: string;
  label: string;
}

export interface DamageScenario {
  id: string;
  label: string;
  description?: string;
  damaged_assets: Array<{ asset_type: string; quantity: number }>;
  jobs: Array<{ task: string; depends_on: number[] }>;
}

export interface ScenarioResult {
  risk_band: string;
  evidence_quality: string;
  risk_factors: string[];
  restoration_low_hours: number | null;
  restoration_high_hours: number | null;
  restoration_factors: string[];
  preparation_actions: string[];
  alert_eligible: boolean;
  assumptions: string[];
  source_label: string;
}

/** Optional explicit customer declarations (engine/needs.py). Guidance only. */
export interface DeclaredNeedsPayload {
  medical_equipment: boolean;
  accessibility_assistance: boolean;
}

export interface EvaluateRequest {
  customer_id: string;
  storm_severity: string;
  available_crews: number;
  access_blocked: boolean;
  damage_scenario: string | null;
  declared_needs?: DeclaredNeedsPayload;
}

/** Scenario inputs as the concierge/notification endpoints expect them. */
export interface ScenarioInputsPayload {
  storm_severity: string;
  available_crews: number;
  access_blocked: boolean;
  damage_scenario: string | null;
  declared_needs?: DeclaredNeedsPayload;
  customer_label?: string;
}

export interface ConciergeAskRequest {
  question: string;
  customer_id: string;
  customer_label: string;
  inputs: ScenarioInputsPayload;
  prev_customer_id?: string | null;
  prev_inputs?: ScenarioInputsPayload | null;
}

export interface ConciergeReply {
  text: string;
  mode: 'live' | 'fallback' | string;
  provider_error: string | null;
  used_counterfactual: boolean;
}

export type LifecycleState =
  | 'pre_storm'
  | 'outage_confirmed'
  | 'restoration_updated'
  | 'restoration_complete';

export interface NotificationPreferences {
  opted_in: boolean;
  available_channels: string[];
  preferred_channel: string | null;
}

export interface NotificationPreviewRequest {
  lifecycle_state: LifecycleState;
  inputs: ScenarioInputsPayload;
  result: ScenarioResult;
  prev_result?: ScenarioResult | null;
  preferences?: NotificationPreferences | null;
}

export interface NotificationPreview {
  lifecycle_state: LifecycleState;
  message: string;
  trigger_reason: string;
  recommended_channel: string | null;
  timing: string;
  scenario_eligible: boolean;
  consent_status: 'opted_in' | 'opted_out' | string;
  channel_available: boolean;
  send_recommended: boolean;
  send_blockers: string[];
  estimate_window: string;
  estimate_change: { kind: string; material: boolean; detail: string } | null;
  unknowns: string[];
  simulation_label: string;
  safety_guidance: string[];
}

export interface BackendStatus {
  backend: 'real' | 'demo' | string;
}

// ---------------------------------------------------------------------------
// Client
// ---------------------------------------------------------------------------

const API_BASE_URL = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');

/** Thrown for any non-success response or connection failure. */
export class ApiError extends Error {
  status: number | null;
  constructor(message: string, status: number | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export const isAbortError = (err: unknown): boolean =>
  err instanceof DOMException && err.name === 'AbortError';

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  let response: Response;
  try {
    response = await fetch(url, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init.headers || {}) },
      cache: 'no-store',
    });
  } catch (err) {
    if (isAbortError(err)) throw err;
    throw new ApiError(
      'Could not reach the Beacon engine. Is the Python API running on port 8000?',
      null
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body && typeof body.detail === 'string') detail = body.detail;
    } catch {
      /* non-JSON error body; keep statusText */
    }
    // The Next.js dev proxy answers 500 when the Python API is down.
    const msg =
      response.status >= 500 && /ECONNREFUSED|socket hang up|Internal Server Error/i.test(detail)
        ? 'The Beacon engine is not reachable (proxy could not connect).'
        : `Engine error ${response.status}: ${detail}`;
    throw new ApiError(msg, response.status);
  }

  return (await response.json()) as T;
}

const post = <T>(path: string, body: unknown, signal?: AbortSignal) =>
  request<T>(path, { method: 'POST', body: JSON.stringify(body), signal });

export const apiClient = {
  /** GET /api/status — which engine backend is active ('real' or 'demo'). */
  status(signal?: AbortSignal): Promise<BackendStatus> {
    return request<BackendStatus>('/api/status', { signal });
  },

  /** GET /api/customers */
  getCustomers(signal?: AbortSignal): Promise<Customer[]> {
    return request<Customer[]>('/api/customers', { signal });
  },

  /** GET /api/damage-scenarios/{customerId} */
  getDamageScenarios(customerId: string, signal?: AbortSignal): Promise<DamageScenario[]> {
    return request<DamageScenario[]>(
      `/api/damage-scenarios/${encodeURIComponent(customerId)}`,
      { signal }
    );
  },

  /** POST /api/evaluate */
  evaluateScenario(req: EvaluateRequest, signal?: AbortSignal): Promise<ScenarioResult> {
    return post<ScenarioResult>('/api/evaluate', req, signal);
  },

  /** POST /api/concierge/ask — grounded server-side concierge (Bedrock or fallback). */
  askConcierge(req: ConciergeAskRequest, signal?: AbortSignal): Promise<ConciergeReply> {
    return post<ConciergeReply>('/api/concierge/ask', req, signal);
  },

  /** POST /api/notification-preview — deterministic, preview-only. */
  notificationPreview(
    req: NotificationPreviewRequest,
    signal?: AbortSignal
  ): Promise<NotificationPreview> {
    return post<NotificationPreview>('/api/notification-preview', req, signal);
  },
};
