"""
concierge/
==========
Live AI concierge grounded in StormReady's scenario engine.

Separation of concerns:
  context.py    — builds an ALLOWLISTED, PII-free context object
  grounding.py  — system/grounding instructions + rule-based fallback answers
  provider.py   — Amazon Bedrock (Converse API via boto3) call + config/availability
  assistant.py  — orchestration: context -> provider-or-fallback, engine counterfactuals

The engine is always the source of numerical results. The model only explains
them; it never computes or overrides the active scenario.

Owner: solo maintainer (temporary arrangement; see AGENTS.md).
"""

from concierge.assistant import answer_question, AssistantReply  # noqa: F401
from concierge.context import build_context  # noqa: F401
from concierge.provider import provider_status  # noqa: F401
from concierge.grounding import SUGGESTED_QUESTIONS  # noqa: F401
