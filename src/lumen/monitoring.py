"""Derived view helpers for monitoring an exam."""

from __future__ import annotations

import time
from typing import Any

from . import store


def _interval(exam: dict[str, Any]) -> float:
    try:
        return max(float(exam.get("interval", 10)), 1.0)
    except (TypeError, ValueError):
        return 10.0


def build_overview(exam: dict[str, Any], now: float | None = None) -> dict[str, Any]:
    """Build the monitor data for an exam.

    This includes the latest screenshot of every student, whether they are
    considered inactive and if they appear to be sending screenshots from more
    than one machine.
    """
    now = now if now is not None else time.time()
    interval = _interval(exam)
    inactive_after = interval * 4
    exam_id = exam["id"]

    students: list[dict[str, Any]] = []
    for student in exam.get("students", []):
        dirname = student["dir"]
        shots = store.list_screenshots(exam_id, dirname)
        latest = shots[0] if shots else None

        recent_window = max(inactive_after, interval * 4)
        recent = [s for s in shots if now - s["captured"] <= recent_window]
        expected = recent_window / interval
        duplicate_warning = len(recent) > expected + 2 and len(recent) >= 3

        if latest is None:
            seconds_since = None
            inactive = True
        else:
            seconds_since = now - latest["captured"]
            inactive = seconds_since > inactive_after

        students.append(
            {
                "name": student["name"],
                "dir": dirname,
                "latest": latest,
                "seconds_since": seconds_since,
                "inactive": inactive,
                "duplicate_warning": duplicate_warning,
                "recent_count": len(recent),
                "screenshot_count": len(shots),
            }
        )

    inactive_students = [s for s in students if s["inactive"]]
    duplicates = [s for s in students if s["duplicate_warning"]]

    return {
        "exam_id": exam_id,
        "recording": bool(exam.get("recording")),
        "interval": interval,
        "students": students,
        "inactive_students": inactive_students,
        "duplicate_warnings": duplicates,
        "generated_at": now,
    }
