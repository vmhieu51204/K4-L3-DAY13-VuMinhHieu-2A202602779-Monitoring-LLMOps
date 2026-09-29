from __future__ import annotations

import time

from .incidents import STATE
from .pii import scrub_text
from .tracing import get_langfuse_client, observe, tracing_enabled

CORPUS = {
    "refund": ["Refunds are available within 7 days with proof of purchase."],
    "monitoring": ["Metrics detect incidents, logs identify affected requests, traces localize the root cause."],
    "policy": ["Do not expose PII in logs. Use sanitized summaries only."],
}


@observe(name="retrieval", as_type="retriever")
def retrieve(message: str) -> list[str]:
    sanitized_query = scrub_text(message)
    if tracing_enabled():
        client = get_langfuse_client()
        if hasattr(client, "update_current_span"):
            try:
                client.update_current_span(
                    input={"query": sanitized_query},
                    metadata={"sanitized": sanitized_query != message},
                )
            except Exception:
                pass

    if STATE["tool_fail"]:
        raise RuntimeError("Vector store timeout")
    if STATE["rag_slow"]:
        time.sleep(2.5)
    lowered = sanitized_query.lower()
    for key, docs in CORPUS.items():
        if key in lowered:
            return docs
    return ["No domain document matched. Use general fallback answer."]

