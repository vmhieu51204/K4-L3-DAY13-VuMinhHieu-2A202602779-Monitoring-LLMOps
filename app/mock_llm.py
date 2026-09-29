from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any

from .incidents import STATE
from .tracing import get_langfuse_client, observe, tracing_enabled


@dataclass
class FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class FakeResponse:
    text: str
    usage: FakeUsage
    model: str
    ttft_ms: int
    cost_usd: float = 0.0


def estimate_cost(tokens_in: int, tokens_out: int) -> float:
    input_cost = (tokens_in / 1_000_000) * 3
    output_cost = (tokens_out / 1_000_000) * 15
    return round(input_cost + output_cost, 6)


class FakeLLM:
    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.model = model

    @observe(name="generation", as_type="generation")
    def generate(self, prompt: str, **kwargs: Any) -> FakeResponse:
        started = time.perf_counter()
        time.sleep(0.05)  # mô phỏng thời điểm token đầu tiên sẵn sàng
        ttft_ms = int((time.perf_counter() - started) * 1000)
        time.sleep(0.10)
        input_tokens = max(20, len(prompt) // 4)
        output_tokens = random.randint(80, 180)
        if STATE["cost_spike"]:
            output_tokens *= 4
        cost_usd = estimate_cost(input_tokens, output_tokens)
        answer = (
            "Starter answer. You should improve this output logic and add better quality checks. "
            "Use retrieved context and keep responses concise."
        )

        if tracing_enabled():
            client = get_langfuse_client()
            if hasattr(client, "update_current_generation"):
                try:
                    gen_kwargs: dict[str, Any] = {
                        "model": self.model,
                        "input": prompt,
                        "output": answer,
                        "usage_details": {
                            "input": input_tokens,
                            "output": output_tokens,
                            "total": input_tokens + output_tokens,
                        },
                        "cost_details": {"total": cost_usd},
                    }
                    if "managed_prompt" in kwargs and kwargs["managed_prompt"] is not None:
                        gen_kwargs["prompt"] = kwargs["managed_prompt"]
                    client.update_current_generation(**gen_kwargs)
                except Exception:
                    pass

        return FakeResponse(
            text=answer,
            usage=FakeUsage(input_tokens, output_tokens),
            model=self.model,
            ttft_ms=ttft_ms,
            cost_usd=cost_usd,
        )

