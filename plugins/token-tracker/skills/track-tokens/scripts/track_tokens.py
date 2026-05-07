#!/usr/bin/env python3
"""Aggregate token usage from a Claude Code session transcript (JSONL).

Single source of truth: each assistant entry carries a `message.usage` object
with input_tokens / output_tokens / cache_read_input_tokens /
cache_creation_input_tokens. We sum these per model. No estimation, no
heuristics — if the transcript does not record a value, we report 0 for it.

Usage:
  track_tokens.py [--session PATH] [--format json|markdown] [--since ISO8601]
                  [--no-cost] [--pricing PATH]

Auto-detects the active session by picking the most recently modified
*.jsonl under ~/.claude/projects/*/.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

DEFAULT_PRICING = {
    "claude-opus-4-7":            {"input": 15.00, "output": 75.00, "cache_read": 1.50, "cache_creation": 18.75},
    "claude-opus-4-6":            {"input": 15.00, "output": 75.00, "cache_read": 1.50, "cache_creation": 18.75},
    "claude-sonnet-4-6":          {"input":  3.00, "output": 15.00, "cache_read": 0.30, "cache_creation":  3.75},
    "claude-haiku-4-5-20251001":  {"input":  0.80, "output":  4.00, "cache_read": 0.08, "cache_creation":  1.00},
}


def find_active_session() -> str | None:
    pattern = str(Path.home() / ".claude" / "projects" / "*" / "*.jsonl")
    files = glob.glob(pattern)
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def parse_transcript(path: str, since: str | None = None) -> dict:
    by_model: dict[str, dict] = {}
    first_ts: str | None = None
    last_ts: str | None = None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "assistant":
                continue
            msg = entry.get("message") or {}
            usage = msg.get("usage")
            if not usage:
                continue
            ts = entry.get("timestamp")
            if since and ts and ts < since:
                continue
            if ts:
                if first_ts is None or ts < first_ts:
                    first_ts = ts
                if last_ts is None or ts > last_ts:
                    last_ts = ts
            model = msg.get("model") or "unknown"
            agg = by_model.setdefault(model, {
                "messages": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read_input_tokens": 0,
                "cache_creation_input_tokens": 0,
            })
            agg["messages"] += 1
            agg["input_tokens"] += int(usage.get("input_tokens") or 0)
            agg["output_tokens"] += int(usage.get("output_tokens") or 0)
            agg["cache_read_input_tokens"] += int(usage.get("cache_read_input_tokens") or 0)
            agg["cache_creation_input_tokens"] += int(usage.get("cache_creation_input_tokens") or 0)
    return {"by_model": by_model, "first_ts": first_ts, "last_ts": last_ts}


def compute_costs(by_model: dict, pricing: dict) -> tuple[dict, float, list[str]]:
    per_model: dict[str, float | None] = {}
    total = 0.0
    unknown_models: list[str] = []
    for model, agg in by_model.items():
        prices = pricing.get(model)
        if not prices:
            per_model[model] = None
            unknown_models.append(model)
            continue
        cost = (
            agg["input_tokens"] * prices["input"]
            + agg["output_tokens"] * prices["output"]
            + agg["cache_read_input_tokens"] * prices["cache_read"]
            + agg["cache_creation_input_tokens"] * prices["cache_creation"]
        ) / 1_000_000
        per_model[model] = cost
        total += cost
    return per_model, total, unknown_models


def render_markdown(path: str, parsed: dict, costs: dict | None, total_cost: float | None,
                    unknown_models: list[str]) -> str:
    by_model = parsed["by_model"]
    out: list[str] = ["## Token Usage", ""]
    out.append(f"**Source:** `{path}`")
    if parsed["first_ts"] and parsed["last_ts"]:
        out.append(f"**Window:** `{parsed['first_ts']}` → `{parsed['last_ts']}`")
    out.append("")

    headers = ["Model", "Msgs", "Input", "Output", "Cache Read", "Cache Write"]
    aligns  = ["---", "---:", "---:", "---:", "---:", "---:"]
    if costs is not None:
        headers.append("Cost (USD)")
        aligns.append("---:")
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join(aligns)  + " |")

    totals = {"messages": 0, "input": 0, "output": 0, "cache_read": 0, "cache_creation": 0}
    for model, agg in by_model.items():
        row = [
            f"`{model}`",
            f"{agg['messages']:,}",
            f"{agg['input_tokens']:,}",
            f"{agg['output_tokens']:,}",
            f"{agg['cache_read_input_tokens']:,}",
            f"{agg['cache_creation_input_tokens']:,}",
        ]
        totals["messages"] += agg["messages"]
        totals["input"] += agg["input_tokens"]
        totals["output"] += agg["output_tokens"]
        totals["cache_read"] += agg["cache_read_input_tokens"]
        totals["cache_creation"] += agg["cache_creation_input_tokens"]
        if costs is not None:
            c = costs.get(model)
            row.append(f"${c:.4f}" if c is not None else "—")
        out.append("| " + " | ".join(row) + " |")

    total_row = [
        "**Total**",
        f"**{totals['messages']:,}**",
        f"**{totals['input']:,}**",
        f"**{totals['output']:,}**",
        f"**{totals['cache_read']:,}**",
        f"**{totals['cache_creation']:,}**",
    ]
    if costs is not None and total_cost is not None:
        total_row.append(f"**${total_cost:.4f}**")
    out.append("| " + " | ".join(total_row) + " |")
    out.append("")

    if unknown_models:
        out.append(f"> Note: cost not computed for unknown models: {', '.join(unknown_models)}")
        out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", help="Path to session JSONL (auto-detect if omitted)")
    ap.add_argument("--format", choices=["markdown", "json"], default="markdown")
    ap.add_argument("--since", help="ISO8601 timestamp; only include entries on or after this time")
    ap.add_argument("--no-cost", action="store_true", help="Skip cost computation")
    ap.add_argument("--pricing", help="Path to JSON file overriding default pricing per million tokens")
    args = ap.parse_args()

    path = args.session or find_active_session()
    if not path or not os.path.exists(path):
        print("ERROR: no active session transcript found.", file=sys.stderr)
        print("       Pass --session PATH or run from inside an active Claude Code session.", file=sys.stderr)
        return 2

    parsed = parse_transcript(path, since=args.since)
    if not parsed["by_model"]:
        print(f"ERROR: no usage entries found in {path}", file=sys.stderr)
        return 3

    pricing = DEFAULT_PRICING
    if args.pricing:
        with open(args.pricing, "r", encoding="utf-8") as f:
            pricing = json.load(f)

    costs: dict | None = None
    total_cost: float | None = None
    unknown: list[str] = []
    if not args.no_cost:
        costs, total_cost, unknown = compute_costs(parsed["by_model"], pricing)

    if args.format == "json":
        out = {
            "transcript": path,
            "first_ts": parsed["first_ts"],
            "last_ts": parsed["last_ts"],
            "by_model": parsed["by_model"],
            "costs_usd": costs,
            "total_cost_usd": total_cost,
            "unknown_models": unknown,
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(render_markdown(path, parsed, costs, total_cost, unknown))
    return 0


if __name__ == "__main__":
    sys.exit(main())
