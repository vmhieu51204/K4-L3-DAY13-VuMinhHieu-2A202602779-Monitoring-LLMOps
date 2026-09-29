from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .metrics import percentile

LOG_PATH = Path(os.getenv("LOG_PATH", "data/logs.jsonl"))


def compute_dashboard_metrics() -> dict[str, Any]:
    if not LOG_PATH.exists():
        records = []
    else:
        records = []
        with LOG_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except Exception:
                        pass

    now = datetime.now(timezone.utc)
    # Filter last 60 minutes
    recent = []
    for r in records:
        ts_str = r.get("ts")
        if ts_str:
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if (now - dt).total_seconds() <= 3600:
                    recent.append(r)
            except Exception:
                recent.append(r)
        else:
            recent.append(r)

    response_sent = [r for r in recent if r.get("event") == "response_sent"]
    request_received = [r for r in recent if r.get("event") == "request_received"]
    request_failed = [r for r in recent if r.get("event") == "request_failed"]

    # 1. Latency & TTFT
    latencies = [r.get("latency_ms", 0) for r in response_sent if isinstance(r.get("latency_ms"), (int, float))]
    ttfts = [r.get("ttft_ms", 0) for r in response_sent if isinstance(r.get("ttft_ms"), (int, float))]
    p50_lat = percentile(latencies, 50) if latencies else 0.0
    p95_lat = percentile(latencies, 95) if latencies else 0.0
    p99_lat = percentile(latencies, 99) if latencies else 0.0
    ttft_p95 = percentile(ttfts, 95) if ttfts else 0.0

    # 2. Traffic
    total_reqs = len(request_received)
    qps = round(total_reqs / 3600, 4)
    rpm = round(total_reqs / 60, 2)

    # 3. Errors & Retrieval success
    total_calls = len(request_received)
    failed_calls = len(request_failed)
    error_rate = round((failed_calls / total_calls * 100), 2) if total_calls else 0.0
    error_counts: dict[str, int] = {}
    for r in request_failed:
        etype = r.get("error_type", "Unknown")
        error_counts[etype] = error_counts.get(etype, 0) + 1

    tool_calls = [r for r in recent if r.get("tool_success") is not None]
    tool_success_calls = [r for r in tool_calls if r.get("tool_success") is True]
    retrieval_success_rate = round(len(tool_success_calls) / len(tool_calls) * 100, 2) if tool_calls else 100.0

    # 4. Cost
    costs = [r.get("cost_usd", 0.0) for r in response_sent if isinstance(r.get("cost_usd"), (int, float))]
    total_cost = round(sum(costs), 6)

    # 5. Tokens
    tokens_in = sum(r.get("tokens_in", 0) for r in response_sent if isinstance(r.get("tokens_in"), int))
    tokens_out = sum(r.get("tokens_out", 0) for r in response_sent if isinstance(r.get("tokens_out"), int))
    total_tokens = tokens_in + tokens_out

    # 6. Quality
    qualities = [r.get("quality_score", 0.0) for r in response_sent if isinstance(r.get("quality_score"), (int, float))]
    mean_quality = round(sum(qualities) / len(qualities), 2) if qualities else 0.0

    return {
        "time_range": "60m",
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "latency": {
            "p50": p50_lat,
            "p95": p95_lat,
            "p99": p99_lat,
            "ttft_p95": ttft_p95,
            "unit": "ms",
            "threshold": "P95 <= 3000ms",
            "status": "PASS" if p95_lat <= 3000 else "FAIL",
        },
        "traffic": {
            "total_requests": total_reqs,
            "rate_per_minute": rpm,
            "qps": qps,
            "unit": "requests_per_minute",
            "threshold": "rate >= 1 req/min",
            "status": "PASS" if rpm >= 0.1 else "IDLE",
        },
        "errors": {
            "error_rate_pct": error_rate,
            "error_counts": error_counts,
            "retrieval_success_rate_pct": retrieval_success_rate,
            "unit": "percent",
            "threshold": "error_rate <= 2%",
            "status": "PASS" if error_rate <= 2.0 else "FAIL",
        },
        "cost": {
            "total_usd": total_cost,
            "unit": "usd",
            "threshold": "total <= $2.50",
            "status": "PASS" if total_cost <= 2.50 else "FAIL",
        },
        "tokens": {
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total_tokens": total_tokens,
            "unit": "tokens",
            "threshold": "tokens <= 50,000",
            "status": "PASS" if total_tokens <= 50000 else "FAIL",
        },
        "quality": {
            "mean": mean_quality,
            "unit": "score_0_to_1",
            "threshold": "mean >= 0.75",
            "status": "PASS" if mean_quality >= 0.75 else "FAIL",
        },
    }


def render_dashboard_html() -> str:
    m = compute_dashboard_metrics()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta http-equiv="refresh" content="30">
  <title>K4-L3A Day 13 Monitoring & LLMOps Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen p-6 font-sans">
  <div class="max-w-7xl mx-auto space-y-6">
    <!-- Header -->
    <header class="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-slate-800 p-6 rounded-xl border border-slate-700 shadow-lg">
      <div>
        <h1 class="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
          <span class="inline-block w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></span>
          K4-L3A Day 13 Monitoring &amp; LLMOps
        </h1>
        <p class="text-sm text-slate-400 mt-1">Live metrics aggregated from <code class="text-indigo-400 font-mono">data/logs.jsonl</code></p>
      </div>
      <div class="mt-4 sm:mt-0 flex gap-3 text-xs font-mono">
        <div class="bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-700">
          <span class="text-slate-400">Time Range:</span> <span class="text-indigo-400 font-semibold">Last 60 minutes</span>
        </div>
        <div class="bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-700">
          <span class="text-slate-400">Refresh:</span> <span class="text-emerald-400 font-semibold">30s</span>
        </div>
        <div class="bg-slate-900/80 px-3 py-1.5 rounded-lg border border-slate-700">
          <span class="text-slate-400">Updated:</span> <span class="text-slate-200">{m['timestamp']}</span>
        </div>
      </div>
    </header>

    <!-- 6 Panels Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">

      <!-- Panel 1: Latency & TTFT -->
      <div class="bg-slate-800 rounded-xl p-5 border border-slate-700 flex flex-col justify-between shadow">
        <div>
          <div class="flex justify-between items-start">
            <div>
              <span class="text-xs uppercase tracking-wider text-slate-400 font-semibold">Panel 1</span>
              <h2 class="text-lg font-bold text-white">Latency &amp; TTFT</h2>
            </div>
            <span class="px-2.5 py-1 text-xs font-bold rounded-full {'bg-emerald-950 text-emerald-400 border border-emerald-800' if m['latency']['status'] == 'PASS' else 'bg-rose-950 text-rose-400 border border-rose-800'}">
              SLO: {m['latency']['threshold']}
            </span>
          </div>
          <div class="grid grid-cols-2 gap-3 mt-4">
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-750">
              <div class="text-xs text-slate-400">P50 Latency</div>
              <div class="text-2xl font-bold font-mono text-cyan-400">{m['latency']['p50']} <span class="text-xs text-slate-400">ms</span></div>
            </div>
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-750">
              <div class="text-xs text-slate-400">P95 Latency</div>
              <div class="text-2xl font-bold font-mono {'text-emerald-400' if m['latency']['p95'] <= 3000 else 'text-rose-400'}">{m['latency']['p95']} <span class="text-xs text-slate-400">ms</span></div>
            </div>
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-750">
              <div class="text-xs text-slate-400">P99 Latency</div>
              <div class="text-xl font-bold font-mono text-purple-400">{m['latency']['p99']} <span class="text-xs text-slate-400">ms</span></div>
            </div>
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-750">
              <div class="text-xs text-slate-400">TTFT P95</div>
              <div class="text-xl font-bold font-mono text-amber-400">{m['latency']['ttft_p95']} <span class="text-xs text-slate-400">ms</span></div>
            </div>
          </div>
        </div>
        <div class="text-xs text-slate-400 mt-4 pt-3 border-t border-slate-700/60 flex justify-between">
          <span>Unit: <strong>ms</strong></span>
          <span>Source: <code>response_sent</code></span>
        </div>
      </div>

      <!-- Panel 2: Traffic -->
      <div class="bg-slate-800 rounded-xl p-5 border border-slate-700 flex flex-col justify-between shadow">
        <div>
          <div class="flex justify-between items-start">
            <div>
              <span class="text-xs uppercase tracking-wider text-slate-400 font-semibold">Panel 2</span>
              <h2 class="text-lg font-bold text-white">Request Traffic</h2>
            </div>
            <span class="px-2.5 py-1 text-xs font-bold rounded-full bg-blue-950 text-blue-400 border border-blue-800">
              Threshold: {m['traffic']['threshold']}
            </span>
          </div>
          <div class="grid grid-cols-2 gap-3 mt-4">
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-750">
              <div class="text-xs text-slate-400">Total Requests</div>
              <div class="text-3xl font-bold font-mono text-white">{m['traffic']['total_requests']}</div>
            </div>
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-750">
              <div class="text-xs text-slate-400">Rate / Minute</div>
              <div class="text-3xl font-bold font-mono text-blue-400">{m['traffic']['rate_per_minute']}</div>
            </div>
          </div>
          <div class="bg-slate-900/40 p-2.5 rounded-lg border border-slate-750 mt-3 text-xs text-slate-300">
            Average QPS: <span class="font-mono font-semibold text-white">{m['traffic']['qps']}</span> req/sec
          </div>
        </div>
        <div class="text-xs text-slate-400 mt-4 pt-3 border-t border-slate-700/60 flex justify-between">
          <span>Unit: <strong>requests/min</strong></span>
          <span>Source: <code>request_received</code></span>
        </div>
      </div>

      <!-- Panel 3: Errors & Retrieval Success -->
      <div class="bg-slate-800 rounded-xl p-5 border border-slate-700 flex flex-col justify-between shadow">
        <div>
          <div class="flex justify-between items-start">
            <div>
              <span class="text-xs uppercase tracking-wider text-slate-400 font-semibold">Panel 3</span>
              <h2 class="text-lg font-bold text-white">Errors &amp; Retrieval</h2>
            </div>
            <span class="px-2.5 py-1 text-xs font-bold rounded-full {'bg-emerald-950 text-emerald-400 border border-emerald-800' if m['errors']['status'] == 'PASS' else 'bg-rose-950 text-rose-400 border border-rose-800'}">
              Max Error: {m['errors']['threshold']}
            </span>
          </div>
          <div class="grid grid-cols-2 gap-3 mt-4">
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-750">
              <div class="text-xs text-slate-400">Error Rate</div>
              <div class="text-3xl font-bold font-mono {'text-emerald-400' if m['errors']['error_rate_pct'] <= 2 else 'text-rose-400'}">{m['errors']['error_rate_pct']}%</div>
            </div>
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-750">
              <div class="text-xs text-slate-400">Retrieval Success</div>
              <div class="text-3xl font-bold font-mono text-emerald-400">{m['errors']['retrieval_success_rate_pct']}%</div>
            </div>
          </div>
          <div class="mt-3 text-xs text-slate-400">
            Breakdown: {json.dumps(m['errors']['error_counts']) if m['errors']['error_counts'] else 'No errors reported'}
          </div>
        </div>
        <div class="text-xs text-slate-400 mt-4 pt-3 border-t border-slate-700/60 flex justify-between">
          <span>Unit: <strong>percent (%)</strong></span>
          <span>Source: <code>request_failed / received</code></span>
        </div>
      </div>

      <!-- Panel 4: Cost Over Time -->
      <div class="bg-slate-800 rounded-xl p-5 border border-slate-700 flex flex-col justify-between shadow">
        <div>
          <div class="flex justify-between items-start">
            <div>
              <span class="text-xs uppercase tracking-wider text-slate-400 font-semibold">Panel 4</span>
              <h2 class="text-lg font-bold text-white">Cost Over Time</h2>
            </div>
            <span class="px-2.5 py-1 text-xs font-bold rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800">
              Budget: {m['cost']['threshold']}
            </span>
          </div>
          <div class="mt-4 bg-slate-900/60 p-4 rounded-lg border border-slate-750">
            <div class="text-xs text-slate-400">Total Window Cost</div>
            <div class="text-4xl font-bold font-mono text-emerald-400">${m['cost']['total_usd']} <span class="text-sm font-normal text-slate-400">USD</span></div>
          </div>
          <p class="text-xs text-slate-400 mt-3">Calculated via input/output token pricing tiers ($3/$15 per 1M tokens).</p>
        </div>
        <div class="text-xs text-slate-400 mt-4 pt-3 border-t border-slate-700/60 flex justify-between">
          <span>Unit: <strong>USD ($)</strong></span>
          <span>Source: <code>response_sent.cost_usd</code></span>
        </div>
      </div>

      <!-- Panel 5: Token Usage -->
      <div class="bg-slate-800 rounded-xl p-5 border border-slate-700 flex flex-col justify-between shadow">
        <div>
          <div class="flex justify-between items-start">
            <div>
              <span class="text-xs uppercase tracking-wider text-slate-400 font-semibold">Panel 5</span>
              <h2 class="text-lg font-bold text-white">Input &amp; Output Tokens</h2>
            </div>
            <span class="px-2.5 py-1 text-xs font-bold rounded-full bg-indigo-950 text-indigo-400 border border-indigo-800">
              Threshold: {m['tokens']['threshold']}
            </span>
          </div>
          <div class="grid grid-cols-2 gap-3 mt-4">
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-750">
              <div class="text-xs text-slate-400">Prompt Tokens In</div>
              <div class="text-2xl font-bold font-mono text-indigo-400">{m['tokens']['tokens_in']:,}</div>
            </div>
            <div class="bg-slate-900/60 p-3 rounded-lg border border-slate-750">
              <div class="text-xs text-slate-400">Comp Tokens Out</div>
              <div class="text-2xl font-bold font-mono text-indigo-400">{m['tokens']['tokens_out']:,}</div>
            </div>
          </div>
          <div class="mt-3 bg-slate-900/40 p-2.5 rounded-lg border border-slate-750 text-xs flex justify-between">
            <span class="text-slate-400">Total Accumulated:</span>
            <span class="font-mono font-bold text-white">{m['tokens']['total_tokens']:,} tokens</span>
          </div>
        </div>
        <div class="text-xs text-slate-400 mt-4 pt-3 border-t border-slate-700/60 flex justify-between">
          <span>Unit: <strong>tokens</strong></span>
          <span>Source: <code>response_sent.tokens_in/out</code></span>
        </div>
      </div>

      <!-- Panel 6: Quality Proxy -->
      <div class="bg-slate-800 rounded-xl p-5 border border-slate-700 flex flex-col justify-between shadow">
        <div>
          <div class="flex justify-between items-start">
            <div>
              <span class="text-xs uppercase tracking-wider text-slate-400 font-semibold">Panel 6</span>
              <h2 class="text-lg font-bold text-white">Quality Proxy</h2>
            </div>
            <span class="px-2.5 py-1 text-xs font-bold rounded-full {'bg-emerald-950 text-emerald-400 border border-emerald-800' if m['quality']['status'] == 'PASS' else 'bg-amber-950 text-amber-400 border border-amber-800'}">
              Target: {m['quality']['threshold']}
            </span>
          </div>
          <div class="mt-4 bg-slate-900/60 p-4 rounded-lg border border-slate-750">
            <div class="text-xs text-slate-400">Mean Quality Score</div>
            <div class="text-4xl font-bold font-mono {'text-emerald-400' if m['quality']['mean'] >= 0.75 else 'text-amber-400'}">{m['quality']['mean']} <span class="text-sm font-normal text-slate-400">/ 1.0</span></div>
          </div>
          <p class="text-xs text-slate-400 mt-3">Heuristic quality evaluated on relevance, context match and grounding.</p>
        </div>
        <div class="text-xs text-slate-400 mt-4 pt-3 border-t border-slate-700/60 flex justify-between">
          <span>Unit: <strong>score_0_to_1</strong></span>
          <span>Source: <code>response_sent.quality_score</code></span>
        </div>
      </div>

    </div>
  </div>
</body>
</html>"""
