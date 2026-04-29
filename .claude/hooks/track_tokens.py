#!/usr/bin/env python3
"""
Claude Code Stop hook — appends per-turn token usage to token_log.md.

Reads the session transcript JSONL, sums token usage across all assistant
messages, and appends one row to token_log.md in the project root.

Phase detection: scans recent Bash/Skill tool calls for speckit patterns
so each log entry shows which workflow phase was active.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Claude Sonnet 4.6 pricing — update if model changes
PRICE_INPUT_PER_M      = 3.00
PRICE_OUTPUT_PER_M     = 15.00
PRICE_CACHE_WRITE_PER_M = 3.75
PRICE_CACHE_READ_PER_M  = 0.30

SPECKIT_PHASES = {
    "check-prerequisites": "speckit-clarify/tasks/analyze",
    "setup-plan":          "speckit-plan",
    "auto-commit":         "speckit-git-commit",
    "speckit-implement":   "speckit-implement",
    "speckit-specify":     "speckit-specify",
    "speckit-clarify":     "speckit-clarify",
    "speckit-plan":        "speckit-plan",
    "speckit-tasks":       "speckit-tasks",
    "gource":              "gource",
    "ffmpeg":              "video-render",
    "alembic":             "db-migration",
    "pytest":              "testing",
    "uvicorn":             "server",
}


def detect_phase(messages: list) -> str:
    for msg in reversed(messages[-30:]):
        tool_uses = []
        if msg.get("type") == "tool_use":
            tool_uses = [msg]
        elif msg.get("role") == "assistant":
            content = msg.get("content", [])
            if isinstance(content, list):
                tool_uses = [b for b in content if isinstance(b, dict) and b.get("type") == "tool_use"]
        for tu in tool_uses:
            if tu.get("name") == "Bash":
                cmd = tu.get("input", {}).get("command", "")
                for pattern, label in SPECKIT_PHASES.items():
                    if pattern in cmd:
                        return label
            elif tu.get("name") == "Skill":
                skill = tu.get("input", {}).get("skill", "")
                if skill:
                    return f"/{skill}"
    return "general"


def sum_usage(messages: list) -> dict:
    totals = dict(input=0, output=0, cache_read=0, cache_write=0)
    for msg in messages:
        usage = (
            msg.get("usage")
            or msg.get("message", {}).get("usage")
        )
        if usage:
            totals["input"]       += usage.get("input_tokens", 0)
            totals["output"]      += usage.get("output_tokens", 0)
            totals["cache_read"]  += usage.get("cache_read_input_tokens", 0)
            totals["cache_write"] += usage.get("cache_creation_input_tokens", 0)
    return totals


def estimate_cost(u: dict) -> float:
    billable_input = max(0, u["input"] - u["cache_read"])
    return (
        billable_input    * PRICE_INPUT_PER_M       / 1_000_000
        + u["output"]     * PRICE_OUTPUT_PER_M      / 1_000_000
        + u["cache_read"] * PRICE_CACHE_READ_PER_M  / 1_000_000
        + u["cache_write"]* PRICE_CACHE_WRITE_PER_M / 1_000_000
    )


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    transcript_path = payload.get("transcript_path", "")
    session_id      = payload.get("session_id", "unknown")[:8]
    cwd             = payload.get("cwd", ".")

    if not transcript_path or not Path(transcript_path).exists():
        sys.exit(0)

    messages = []
    with open(transcript_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                messages.append(json.loads(line))
            except Exception:
                continue

    if not messages:
        sys.exit(0)

    usage = sum_usage(messages)
    cost  = estimate_cost(usage)
    phase = detect_phase(messages)
    now   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    log_path = Path(cwd) / "token_log.md"
    header = (
        "# Token Log\n\n"
        "Auto-updated by the Claude Code Stop hook after each turn.\n"
        "Costs use Claude Sonnet 4.6 pricing — update `PRICE_*` constants in "
        "`.claude/hooks/track_tokens.py` if the model changes.\n\n"
        "| Timestamp (UTC) | Session | Phase | Input | Output | Cache Read | Cache Write | Est. Cost |\n"
        "|---|---|---|---|---|---|---|---|\n"
    )

    if not log_path.exists():
        log_path.write_text(header)

    row = (
        f"| {now} | `{session_id}` | {phase} "
        f"| {usage['input']:,} | {usage['output']:,} "
        f"| {usage['cache_read']:,} | {usage['cache_write']:,} "
        f"| ${cost:.4f} |\n"
    )

    with open(log_path, "a") as f:
        f.write(row)


if __name__ == "__main__":
    main()
