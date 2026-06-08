"""Append-only JSONL logger for the safety-gradient ladder / abliterated boost.

Every climb attempt — at every rung, success OR refusal — is logged with
low-level detail so the records become a ready-made preference dataset:
flagship successes are SFT/DPO *chosen* examples, refusals/sanitizations are
*rejected* examples, and the L0 abliterated seed is the unconstrained target the
upper rungs are pushed toward.

Records land in daily files under ``$LOOM_DATASETS_DIR`` (default
``~/.loom/datasets/abliterated_boost``) as one JSON object per line. Writes are
append-only with an exclusive-lock best-effort + atomic line flush so concurrent
ladder runs don't interleave partial lines.

Author: Ahmed Adel Bakr Alderai
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("loom.tools.boost_logger")


def _dataset_dir() -> Path:
    root = os.environ.get("LOOM_DATASETS_DIR") or os.path.join(
        os.path.expanduser("~"), ".loom", "datasets", "abliterated_boost"
    )
    p = Path(root)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _today_file() -> Path:
    # Date comes from the OS clock at call time; ts on each record is authoritative.
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return _dataset_dir() / f"{day}.jsonl"


def log_attempt(record: dict[str, Any]) -> None:
    """Append one ladder-attempt record as a JSON line. Never raises.

    Expected keys (missing ones are fine — partial records are still useful):
        ts, query, reframed, darkness, rung (L0|L1|L2), provider, model,
        seed, response, scores (dict of the 31 dims), hcs, complied, refused,
        verdict ("success"|"fail"), round, latency_ms.
    """
    try:
        rec = dict(record)
        rec.setdefault("ts", datetime.now(timezone.utc).isoformat())
        line = json.dumps(rec, ensure_ascii=False, default=str)
        path = _today_file()
        # Append mode is atomic enough for single-line writes on local fs; add a
        # trailing newline in the same write call to avoid interleaving.
        with open(path, "a", encoding="utf-8") as fh:
            try:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
            except Exception:
                pass  # locking is best-effort (not available on all fs)
            fh.write(line + "\n")
    except Exception as e:  # logging must never break a generation pipeline
        logger.debug("boost_log_failed: %s", e)


def dataset_path() -> str:
    """Return today's dataset file path (for surfacing in tool results)."""
    return str(_today_file())


def dataset_stats() -> dict[str, Any]:
    """Quick counts across all dataset files — for verification/tooling."""
    d = _dataset_dir()
    files = sorted(d.glob("*.jsonl"))
    total = 0
    success = 0
    for f in files:
        try:
            for ln in f.read_text(encoding="utf-8").splitlines():
                if not ln.strip():
                    continue
                total += 1
                if '"verdict": "success"' in ln or '"verdict":"success"' in ln:
                    success += 1
        except Exception:
            continue
    return {
        "dir": str(d),
        "files": len(files),
        "records": total,
        "success": success,
        "fail": total - success,
    }
