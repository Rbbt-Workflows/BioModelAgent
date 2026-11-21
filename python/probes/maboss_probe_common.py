"""Shared probe helpers (stdlib only, no scout dependency).

Probe scripts write their evidence both to stdout and to a log file so the
record can be pasted into ``doc/maboss_investigation.md`` verbatim.
"""
import os
import sys
from pathlib import Path

PROBE_DIR = Path(__file__).resolve().parent
LOG_DIR = Path(os.environ.get("MABOSS_PROBE_LOG_DIR", str(PROBE_DIR / "logs")))


def write_probe_log(name: str, text: str) -> str:
    """Append probe evidence to ``python/probes/logs/<name>.log``."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    target = LOG_DIR / f"{name.lower()}.log"
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")
        handle.write("=" * 72 + "\n")
    print(f"[probe log] {target}", file=sys.stderr)
    return str(target)


def say(*args) -> None:
    """Print to stdout and log to the P0 meta log."""
    text = " ".join(str(a) for a in args)
    print(text)
    write_probe_log("P0", text)
