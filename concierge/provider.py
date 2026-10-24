"""
concierge/provider.py
=====================
Amazon Bedrock provider via boto3's Converse API.

Configuration is EXTERNAL (environment variables); nothing is hard-coded:
  - Region:    BEDROCK_REGION  (falls back to AWS_REGION / AWS_DEFAULT_REGION)
  - Model id:  BEDROCK_MODEL_ID (or STORMREADY_BEDROCK_MODEL_ID)
               This is the model id or inference-profile id/ARN. We never invent
               a working model id — if it is unset, the provider is unavailable.

Credentials come from boto3's normal credential chain (profile/SSO/env/role).
We never read, store, print, or log credential values. Status reporting only
ever exposes booleans and the region/model *presence*, never secret values.

Short timeouts and bounded retries keep the UI responsive; on any failure we
return a typed error so the caller can fall back to the rule-based responder.
"""

from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional

# Connection/read timeouts (seconds) and retry cap — deliberately small.
_CONNECT_TIMEOUT = 3
_READ_TIMEOUT = 20
_MAX_ATTEMPTS = 2  # 1 try + 1 retry
_MAX_TOKENS = 400  # concise answers


def _region() -> Optional[str]:
    for var in ("BEDROCK_REGION", "AWS_REGION", "AWS_DEFAULT_REGION"):
        v = os.environ.get(var)
        if v:
            return v.strip()
    return None


def _model_id() -> Optional[str]:
    for var in ("BEDROCK_MODEL_ID", "STORMREADY_BEDROCK_MODEL_ID"):
        v = os.environ.get(var)
        if v:
            return v.strip()
    return None


@dataclass
class ProviderStatus:
    sdk_installed: bool
    region_configured: bool
    model_configured: bool
    credentials_resolvable: bool
    ready: bool
    blocker: Optional[str]  # human-readable, NEVER contains secret values


def provider_status() -> ProviderStatus:
    """
    Report whether the live provider can be used, WITHOUT exposing any secret.

    Does not make a network call; it only checks that the SDK, region, model id,
    and resolvable credentials are present. Actual invocation can still fail
    (e.g. access denied), which is handled at call time.
    """
    try:
        import boto3  # noqa: F401
        import botocore  # noqa: F401
        sdk = True
    except Exception:
        return ProviderStatus(
            sdk_installed=False, region_configured=False, model_configured=False,
            credentials_resolvable=False, ready=False,
            blocker="boto3 is not installed (pip install boto3).",
        )

    region = _region()
    model = _model_id()

    creds_ok = False
    try:
        import botocore.session
        creds_ok = botocore.session.get_session().get_credentials() is not None
    except Exception:
        creds_ok = False

    missing = []
    if not region:
        missing.append("region (set BEDROCK_REGION or AWS_REGION)")
    if not model:
        missing.append("model id (set BEDROCK_MODEL_ID to a model or inference-profile id)")
    if not creds_ok:
        missing.append("AWS credentials (configure a profile/SSO or env credentials)")

    ready = sdk and bool(region) and bool(model) and creds_ok
    blocker = None if ready else "Missing: " + "; ".join(missing)
    return ProviderStatus(
        sdk_installed=sdk,
        region_configured=bool(region),
        model_configured=bool(model),
        credentials_resolvable=creds_ok,
        ready=ready,
        blocker=blocker,
    )


@dataclass
class ProviderResult:
    ok: bool
    text: Optional[str]
    error: Optional[str]  # sanitized message, never contains secrets


def _client():
    import boto3
    from botocore.config import Config
    cfg = Config(
        region_name=_region(),
        connect_timeout=_CONNECT_TIMEOUT,
        read_timeout=_READ_TIMEOUT,
        retries={"max_attempts": _MAX_ATTEMPTS, "mode": "standard"},
    )
    # Credentials resolved via the normal chain; we never pass keys ourselves.
    return boto3.client("bedrock-runtime", config=cfg)


def converse(system_prompt: str, user_message: str) -> ProviderResult:
    """
    Make a single Bedrock Converse call. Returns a ProviderResult.

    On any exception, returns ok=False with a sanitized error string suitable for
    display/logging (no credentials, no raw request signing data).
    """
    status = provider_status()
    if not status.ready:
        return ProviderResult(ok=False, text=None, error=status.blocker or "Provider not configured.")

    model_id = _model_id()
    try:
        client = _client()
        resp = client.converse(
            modelId=model_id,
            system=[{"text": system_prompt}],
            messages=[{"role": "user", "content": [{"text": user_message}]}],
            inferenceConfig={"maxTokens": _MAX_TOKENS, "temperature": 0.2, "topP": 0.9},
        )
        parts = resp.get("output", {}).get("message", {}).get("content", [])
        text = "".join(p.get("text", "") for p in parts).strip()
        if not text:
            return ProviderResult(ok=False, text=None, error="Provider returned an empty response.")
        return ProviderResult(ok=True, text=text, error=None)
    except Exception as exc:  # pragma: no cover - exercised via mocks
        # Sanitize: surface the exception type + short message, never secrets.
        name = type(exc).__name__
        msg = str(exc)
        # Botocore ClientError messages can be long; keep them short and generic.
        if len(msg) > 200:
            msg = msg[:200] + "…"
        return ProviderResult(ok=False, text=None, error=f"{name}: {msg}")
