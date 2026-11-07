#!/usr/bin/env python3
"""usage.py — cost, calls, and cache per project from Cline sessions.

Reads `~/.cline/data/sessions/*/*.json` (session metadata) and
`*.messages.json` (metrics per assistant response). It calculates:

- calls: assistant responses with metrics (one per model request)
- input, output, cache read, and cache write tokens
- cache hit rate
- cost in USD
- elapsed duration

Usage:
    python3 tools/usage.py
    python3 tools/usage.py --project cad-agent
    python3 tools/usage.py --since 2026-11-01
    python3 tools/usage.py --by-project
    python3 tools/usage.py --json
    python3 tools/usage.py --csv
    python3 tools/usage.py --project cad-agent --max-cost 1.00 --max-calls 1500

Exit codes:
    0  OK
    1  read error / no sessions
    2  budget exceeded (--max-cost or --max-calls)
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

DEFAULT_SESSIONS = Path.home() / ".cline" / "data" / "sessions"

# A project path such as /home/user/projects/cad-agent, inside the prompt.
PROJECT_RE = re.compile(r"((?:/home|/Users|/srv|/opt)/[^\s`*]+?/proyectos/[^\s`*]+)")
PATH_RE = re.compile(r"((?:/home|/Users|/srv|/opt)/[^\s`*]+)")


def load_json(path: Path):
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return None


def human(n: float) -> str:
    n = float(n or 0)
    if abs(n) >= 1e9:
        return f"{n / 1e9:.2f}B"
    if abs(n) >= 1e6:
        return f"{n / 1e6:.1f}M"
    if abs(n) >= 1e3:
        return f"{n / 1e3:.1f}k"
    return f"{n:.0f}"


def parse_dt(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def detect_project(session: dict) -> str:
    md = session.get("metadata") or {}
    for text in (session.get("prompt", ""), md.get("title", "")):
        m = PROJECT_RE.search(text or "")
        if m:
            return m.group(1).rstrip(".,;:)")
    for text in (session.get("prompt", ""), md.get("title", "")):
        m = PATH_RE.search(text or "")
        if m:
            return m.group(1).rstrip(".,;:)")
    return session.get("cwd") or session.get("workspace_root") or "?"


def read_messages(path: Path | None) -> dict:
    """Return calls and sums per assistant message."""
    out = {
        "calls": None,
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "cache_write": 0,
        "cost": 0.0,
        "have_metrics": False,
    }
    if not path or not path.exists():
        return out
    data = load_json(path)
    if data is None:
        return out
    msgs = data.get("messages") if isinstance(data, dict) else data
    if not isinstance(msgs, list):
        return out
    calls = 0
    for m in msgs:
        if not isinstance(m, dict) or m.get("role") != "assistant":
            continue
        metrics = m.get("metrics")
        if not isinstance(metrics, dict):
            if m.get("modelInfo"):
                calls += 1
            continue
        calls += 1
        out["have_metrics"] = True
        out["input"] += int(metrics.get("inputTokens", 0) or 0)
        out["output"] += int(metrics.get("outputTokens", 0) or 0)
        out["cache_read"] += int(metrics.get("cacheReadTokens", 0) or 0)
        out["cache_write"] += int(metrics.get("cacheWriteTokens", 0) or 0)
        out["cost"] += float(metrics.get("cost", 0) or 0)
    out["calls"] = calls
    return out


def read_session(meta_path: Path, sessions_dir: Path, with_messages: bool) -> dict | None:
    session = load_json(meta_path)
    if not isinstance(session, dict):
        return None
    md = session.get("metadata") or {}
    usage = md.get("usage") or {}

    messages_path = None
    raw_mp = session.get("messages_path")
    if raw_mp:
        messages_path = Path(raw_mp)
    else:
        candidate = sessions_dir / session.get("session_id", "") / f"{session.get('session_id', '')}.messages.json"
        if candidate.exists():
            messages_path = candidate

    msgs = read_messages(messages_path) if with_messages else {
        "calls": None, "input": 0, "output": 0, "cache_read": 0,
        "cache_write": 0, "cost": 0.0, "have_metrics": False,
    }

    input_tokens = int(usage.get("inputTokens", md.get("tokensIn", 0)) or 0)
    output_tokens = int(usage.get("outputTokens", md.get("tokensOut", 0)) or 0)
    cache_read = int(usage.get("cacheReadTokens", md.get("cacheReads", 0)) or 0)
    cache_write = int(usage.get("cacheWriteTokens", md.get("cacheWrites", 0)) or 0)
    cost = float(md.get("totalCost", 0) or 0)
    if cost == 0 and msgs["cost"]:
        cost = float(msgs["cost"])

    # If metadata has no tokens, use the per-message sums.
    if input_tokens == 0 and msgs["input"]:
        input_tokens = msgs["input"]
    if output_tokens == 0 and msgs["output"]:
        output_tokens = msgs["output"]
    if cache_read == 0 and msgs["cache_read"]:
        cache_read = msgs["cache_read"]
    if cache_write == 0 and msgs["cache_write"]:
        cache_write = msgs["cache_write"]

    started = parse_dt(session.get("started_at"))
    ended = parse_dt(session.get("ended_at"))
    duration_s = int((ended - started).total_seconds()) if started and ended else None

    calls = msgs["calls"]
    hit = (cache_read / input_tokens * 100.0) if input_tokens else 0.0
    per_call = (input_tokens / calls) if calls else None

    return {
        "session_id": session.get("session_id", meta_path.stem),
        "title": (md.get("title") or session.get("prompt") or "").replace("\n", " ")[:80],
        "project": detect_project(session),
        "source": session.get("source", ""),
        "model": session.get("model") or md.get("modelId", ""),
        "provider": session.get("provider", ""),
        "status": session.get("status", ""),
        "started_at": session.get("started_at", ""),
        "ended_at": session.get("ended_at", ""),
        "duration_s": duration_s,
        "calls": calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read,
        "cache_write_tokens": cache_write,
        "cache_hit_rate": round(hit, 2),
        "cost_usd": round(cost, 6),
        "tokens_per_call": round(per_call) if per_call else None,
        "cwd": session.get("cwd", ""),
        "workspace_root": session.get("workspace_root", ""),
        "messages_path": str(messages_path) if messages_path else "",
    }


def collect(sessions_dir: Path, project: str | None, since: str | None,
            session_id: str | None, with_messages: bool) -> list[dict]:
    rows: list[dict] = []
    if not sessions_dir.exists():
        return rows
    for meta_path in sorted(sessions_dir.glob("*/*.json")):
        name = meta_path.name
        if name.endswith(".messages.json") or name.endswith(".compaction.json"):
            continue
        row = read_session(meta_path, sessions_dir, with_messages)
        if not row:
            continue
        if project:
            hay = " ".join(str(row.get(k, "")) for k in
                           ("project", "cwd", "workspace_root", "title")).lower()
            if project.lower() not in hay:
                continue
        if since and row.get("started_at", "")[:10] < since:
            continue
        if session_id and row.get("session_id") != session_id:
            continue
        rows.append(row)
    rows.sort(key=lambda r: r.get("started_at", ""))
    return rows


def totals(rows: list[dict]) -> dict:
    calls = sum(r["calls"] or 0 for r in rows)
    input_tokens = sum(r["input_tokens"] for r in rows)
    output_tokens = sum(r["output_tokens"] for r in rows)
    cache_read = sum(r["cache_read_tokens"] for r in rows)
    cache_write = sum(r["cache_write_tokens"] for r in rows)
    cost = sum(r["cost_usd"] for r in rows)
    duration = sum(r["duration_s"] or 0 for r in rows)
    return {
        "sessions": len(rows),
        "calls": calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cache_read_tokens": cache_read,
        "cache_write_tokens": cache_write,
        "cache_hit_rate": round(cache_read / input_tokens * 100.0, 2) if input_tokens else 0.0,
        "cost_usd": round(cost, 6),
        "duration_s": duration,
        "tokens_per_call": round(input_tokens / calls) if calls else None,
    }


def group_by_project(rows: list[dict]) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r.get("project") or "?", []).append(r)
    out = []
    for project, items in groups.items():
        t = totals(items)
        t["project"] = project
        out.append(t)
    out.sort(key=lambda g: g["cost_usd"], reverse=True)
    return out


def fmt_duration(seconds: int | None) -> str:
    if not seconds:
        return "-"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    return f"{m}m{s:02d}s"


def print_table(rows: list[dict], t: dict) -> None:
    if not rows:
        print("no sessions match the filter")
        return
    print(f"{'date':10s} {'session':20s} {'project':18s} {'model':18s} "
          f"{'status':8s} {'calls':>6s} {'input':>8s} {'output':>8s} "
          f"{'cache':>8s} {'hit%':>6s} {'cost':>9s} {'elapsed':>8s}")
    print("-" * 132)
    for r in rows:
        print(f"{r['started_at'][:10]:10s} {r['session_id'][:20]:20s} "
              f"{Path(r['project']).name[:18]:18s} {r['model'][:18]:18s} "
              f"{r['status'][:8]:8s} {str(r['calls'] or '-'):>6s} "
              f"{human(r['input_tokens']):>8s} {human(r['output_tokens']):>8s} "
              f"{human(r['cache_read_tokens']):>8s} {r['cache_hit_rate']:6.1f} "
              f"{r['cost_usd']:9.4f} {fmt_duration(r['duration_s']):>8s}")
    print("-" * 132)
    print(f"{'TOTAL':10s} {t['sessions']:>3d} sessions  {t['calls']} calls  "
          f"input {human(t['input_tokens'])}  output {human(t['output_tokens'])}  "
          f"cache {human(t['cache_read_tokens'])}  hit {t['cache_hit_rate']:.1f}%  "
          f"US$ {t['cost_usd']:.4f}  {fmt_duration(t['duration_s'])}")
    if t.get("tokens_per_call"):
        print(f"average: {human(t['tokens_per_call'])} input tokens per call")


def print_by_project(groups: list[dict]) -> None:
    if not groups:
        print("no sessions")
        return
    print(f"{'project':28s} {'ses':>4s} {'calls':>6s} {'input':>8s} "
          f"{'output':>8s} {'cache':>8s} {'hit%':>6s} {'cost':>9s}")
    print("-" * 86)
    for g in groups:
        print(f"{(Path(g['project']).name or g['project'])[:28]:28s} "
              f"{g['sessions']:>4d} {g['calls']:>6d} {human(g['input_tokens']):>8s} "
              f"{human(g['output_tokens']):>8s} {human(g['cache_read_tokens']):>8s} "
              f"{g['cache_hit_rate']:6.1f} {g['cost_usd']:9.4f}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cline usage and cost per project.")
    ap.add_argument("--sessions-dir", type=Path, default=DEFAULT_SESSIONS,
                    help="Cline sessions folder")
    ap.add_argument("--project", help="filter by project (substring)")
    ap.add_argument("--since", help="only sessions since YYYY-MM-DD")
    ap.add_argument("--session", help="only one session by id")
    ap.add_argument("--by-project", action="store_true", help="group by project")
    ap.add_argument("--json", action="store_true", help="JSON output")
    ap.add_argument("--csv", action="store_true", help="CSV output")
    ap.add_argument("--no-messages", action="store_true",
                    help="do not read messages.json (faster, no call count)")
    ap.add_argument("--max-cost", type=float, default=None,
                    help="fail if total cost exceeds this value (USD)")
    ap.add_argument("--max-calls", type=int, default=None,
                    help="fail if calls exceed this value")
    args = ap.parse_args(argv)

    rows = collect(args.sessions_dir, args.project, args.since, args.session,
                   with_messages=not args.no_messages)
    t = totals(rows)
    groups = group_by_project(rows)

    if args.json:
        print(json.dumps({
            "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
            "sessions_dir": str(args.sessions_dir),
            "filters": {
                "project": args.project,
                "since": args.since,
                "session": args.session,
            },
            "sessions": rows,
            "totals": t,
            "by_project": groups,
        }, ensure_ascii=False, indent=2))
    elif args.csv:
        writer = csv.writer(sys.stdout)
        writer.writerow(["session_id", "started_at", "project", "model", "status",
                         "calls", "input_tokens", "output_tokens", "cache_read_tokens",
                         "cache_hit_rate", "cost_usd", "duration_s", "title"])
        for r in rows:
            writer.writerow([r["session_id"], r["started_at"], r["project"], r["model"],
                             r["status"], r["calls"] or "", r["input_tokens"],
                             r["output_tokens"], r["cache_read_tokens"],
                             r["cache_hit_rate"], r["cost_usd"],
                             r["duration_s"] or "", r["title"]])
    else:
        if args.by_project:
            print_by_project(groups)
        else:
            print_table(rows, t)

    # Budget
    exceeded = []
    if args.max_cost is not None and t["cost_usd"] > args.max_cost:
        exceeded.append(f"cost US$ {t['cost_usd']:.4f} > max US$ {args.max_cost:.4f}")
    if args.max_calls is not None and t["calls"] > args.max_calls:
        exceeded.append(f"calls {t['calls']} > max {args.max_calls}")
    if exceeded:
        print()
        print("BUDGET EXCEEDED: " + "; ".join(exceeded), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
