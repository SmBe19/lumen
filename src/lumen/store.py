"""On-disk storage for Lumen.

Everything is stored as plain files and directories - there is no database.
Exam configuration is cached in memory for a short amount of time, while the
teacher facing pages always force a fresh read from disk.
"""

from __future__ import annotations

import csv
import io
import json
import os
import re
import secrets
import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

DATA_DIR = Path(os.environ.get("LUMEN_DATA", "data")).resolve()


def configure_data_dir(path: str | os.PathLike[str]) -> None:
    """Point the store at a different data directory (used by tests)."""
    global DATA_DIR
    DATA_DIR = Path(path).resolve()
    invalidate_cache()
    with _cache_lock:
        _key_cache.clear()


_CONFIG_CACHE_TTL = 30.0  # seconds

# exam_id -> (config, loaded_at)
_config_cache: dict[str, tuple[dict[str, Any], float]] = {}
# exam_key (upper) -> exam_id, rebuilt at most every _CONFIG_CACHE_TTL seconds.
_key_cache: dict[str, str] = {}
_key_cache_loaded_at = 0.0
_cache_lock = threading.Lock()

_KEY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_CLEAN_RE = re.compile(r"[^A-Za-z0-9 ._-]+")


# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
def exams_dir() -> Path:
    return DATA_DIR / "exams"


def exam_dir(exam_id: str) -> Path:
    return exams_dir() / exam_id


def screenshots_root(exam_id: str) -> Path:
    return exam_dir(exam_id) / "screenshots"


def logs_dir(exam_id: str) -> Path:
    return exam_dir(exam_id) / "logs"


def teachers_file() -> Path:
    return DATA_DIR / "teachers.json"


def ensure_dirs() -> None:
    exams_dir().mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Teachers
# ---------------------------------------------------------------------------
def load_teachers() -> dict[str, str]:
    path = teachers_file()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_teachers(teachers: dict[str, str]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = teachers_file().with_suffix(".json.tmp")
    tmp.write_text(json.dumps(teachers, indent=2), encoding="utf-8")
    tmp.replace(teachers_file())


def add_teacher(username: str, password: str) -> None:
    username = username.strip()
    if not username:
        raise ValueError("username must not be empty")
    if not password:
        raise ValueError("password must not be empty")
    teachers = load_teachers()
    teachers[username] = generate_password_hash(password)
    save_teachers(teachers)


def set_teacher_password(username: str, password: str) -> None:
    add_teacher(username, password)


def verify_teacher(username: str, password: str) -> bool:
    teachers = load_teachers()
    hashed = teachers.get(username)
    if not hashed:
        return False
    return check_password_hash(hashed, password)


# ---------------------------------------------------------------------------
# Exams
# ---------------------------------------------------------------------------
def _read_config(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def invalidate_cache(exam_id: str | None = None) -> None:
    global _key_cache_loaded_at
    with _cache_lock:
        if exam_id is None:
            _config_cache.clear()
        else:
            _config_cache.pop(exam_id, None)
        # Force the exam-key index to be rebuilt on the next lookup.
        _key_cache_loaded_at = 0.0


def get_exam(exam_id: str, force: bool = False) -> dict[str, Any] | None:
    """Load an exam config, using a short lived in-memory cache."""
    if not force:
        with _cache_lock:
            entry = _config_cache.get(exam_id)
        if entry and (time.time() - entry[1]) < _CONFIG_CACHE_TTL:
            return entry[0]

    config = _read_config(exam_dir(exam_id) / "config.json")
    if config is not None:
        with _cache_lock:
            _config_cache[exam_id] = (config, time.time())
    return config


def _rebuild_key_cache() -> None:
    """Rebuild the ``exam_key -> exam_id`` index from disk."""
    global _key_cache_loaded_at
    ensure_dirs()
    mapping: dict[str, str] = {}
    for entry in sorted(exams_dir().iterdir()):
        if not entry.is_dir():
            continue
        config = get_exam(entry.name)
        if not config:
            continue
        key = str(config.get("exam_key", "")).upper()
        if key:
            mapping[key] = config["id"]
    with _cache_lock:
        _key_cache.clear()
        _key_cache.update(mapping)
        _key_cache_loaded_at = time.time()


def get_exam_by_key(exam_key: str) -> dict[str, Any] | None:
    """Look up an exam by its key, using an in-memory index.

    The index is rebuilt from disk at most every ``_CONFIG_CACHE_TTL``
    seconds so that regular student requests never touch the disk for
    unrelated exams.
    """
    exam_key = (exam_key or "").strip().upper()
    if not exam_key:
        return None
    with _cache_lock:
        exam_id = _key_cache.get(exam_key)
        fresh = (time.time() - _key_cache_loaded_at) < _CONFIG_CACHE_TTL
    if not fresh:
        _rebuild_key_cache()
        with _cache_lock:
            exam_id = _key_cache.get(exam_key)
    if exam_id is None:
        return None
    return get_exam(exam_id)


def list_exams(
    owner: str | None = None, force: bool = False
) -> list[dict[str, Any]]:
    ensure_dirs()
    exams: list[dict[str, Any]] = []
    for entry in sorted(exams_dir().iterdir()):
        if not entry.is_dir():
            continue
        config = get_exam(entry.name, force=force)
        if not config:
            continue
        if owner is not None and config.get("owner") not in (None, owner):
            continue
        exams.append(config)
    exams.sort(key=lambda c: c.get("created_at", 0))
    return exams


def save_exam(config: dict[str, Any]) -> None:
    exam_id = config["id"]
    directory = exam_dir(exam_id)
    directory.mkdir(parents=True, exist_ok=True)
    config["updated_at"] = time.time()
    tmp = directory / "config.json.tmp"
    tmp.write_text(json.dumps(config, indent=2), encoding="utf-8")
    tmp.replace(directory / "config.json")
    invalidate_cache(exam_id)


def generate_exam_key(existing: set[str] | None = None) -> str:
    if existing is None:
        existing = {str(c.get("exam_key")) for c in list_exams(force=True)}
    while True:
        key = "".join(secrets.choice(_KEY_ALPHABET) for _ in range(6))
        if key not in existing:
            return key


def create_exam(
    name: str,
    owner: str,
    exam_key: str | None = None,
    interval: int = 10,
    scale: float = 0.5,
) -> dict[str, Any]:
    ensure_dirs()
    exam_id = uuid.uuid4().hex
    exam_key = (exam_key or "").strip().upper() or generate_exam_key()
    if _key_taken(exam_key):
        raise ValueError("exam key is already in use")
    config = {
        "id": exam_id,
        "name": name.strip() or "Untitled exam",
        "owner": owner,
        "exam_key": exam_key,
        "interval": int(interval),
        "scale": float(scale),
        "recording": False,
        "students": [],
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    (exam_dir(exam_id) / "screenshots").mkdir(parents=True, exist_ok=True)
    (exam_dir(exam_id) / "logs").mkdir(parents=True, exist_ok=True)
    save_exam(config)
    return config


def _key_taken(exam_key: str) -> bool:
    return any(
        str(c.get("exam_key", "")).upper() == exam_key.upper()
        for c in list_exams(force=True)
    )


def delete_exam(exam_id: str) -> None:
    directory = exam_dir(exam_id)
    if directory.exists():
        shutil.rmtree(directory)
    invalidate_cache(exam_id)


# ---------------------------------------------------------------------------
# Student names / directories
# ---------------------------------------------------------------------------
def clean_dirname(display_name: str) -> str:
    """Turn a display name into a safe directory name.

    Whitespace is replaced by underscores so directory names never contain
    spaces.
    """
    cleaned = display_name.replace("(", " ").replace(")", " ")
    cleaned = _CLEAN_RE.sub("_", cleaned)
    cleaned = cleaned.replace("..", "_")
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    if not cleaned:
        cleaned = "student"
    return cleaned[:120]


def unique_dirname(display_name: str, taken: set[str]) -> str:
    base = clean_dirname(display_name)
    candidate = base
    counter = 2
    while candidate.lower() in taken:
        candidate = f"{base}_{counter}"
        counter += 1
    taken.add(candidate.lower())
    return candidate


def _row_value(row: dict[str, str], key: str) -> str:
    value = row.get(key) or ""
    return value.strip()


def display_name_for_row(row: dict[str, str]) -> str | None:
    displayname = _row_value(row, "displayname")
    firstname = _row_value(row, "firstname")
    lastname = _row_value(row, "lastname")
    klass = _row_value(row, "class")

    if displayname:
        name = displayname
    elif firstname and lastname:
        name = f"{firstname} {lastname}"
    elif firstname:
        name = firstname
    elif lastname:
        name = lastname
    else:
        return None
    if klass:
        name = f"{name} ({klass})"
    return name


# Canonical column name -> accepted header spellings (all case insensitive).
_COLUMN_ALIASES = {
    "firstname": "firstname",
    "vorname": "firstname",
    "lastname": "lastname",
    "name": "lastname",
    "displayname": "displayname",
    "class": "class",
    "klasse": "class",
    "kl": "class",
}


def parse_student_csv(text: str) -> list[dict[str, str]]:
    """Parse pasted CSV content into a list of student entries.

    The CSV must contain a header row with at least one of the supported
    columns (``firstname``/``vorname``, ``lastname``/``name``,
    ``displayname``, ``class``/``klasse``/``kl``), in any order. Matching is
    case insensitive. A :class:`ValueError` is raised when no valid column
    is found instead of guessing.
    """
    text = (text or "").strip()
    if not text:
        return []

    reader = csv.reader(io.StringIO(text))
    rows = [row for row in reader if any(cell.strip() for cell in row)]
    if not rows:
        return []

    fieldnames = [
        _COLUMN_ALIASES.get(cell.strip().lower()) for cell in rows[0]
    ]
    if not any(fieldnames):
        raise ValueError(
            "No valid columns found. The first row must contain at least one "
            "of: firstname/vorname, lastname/name, displayname, "
            "class/klasse/kl."
        )

    students: list[dict[str, str]] = []
    for row in rows[1:]:
        record: dict[str, str] = {}
        for index, field in enumerate(fieldnames):
            if field:
                record[field] = row[index].strip() if index < len(row) else ""
        name = display_name_for_row(record)
        if name:
            students.append({"name": name})
    return students


def remove_student(exam: dict[str, Any], dirname: str) -> dict[str, Any] | None:
    """Remove a single student and delete their stored data."""
    students = exam.get("students", [])
    for index, student in enumerate(students):
        if student["dir"] != dirname:
            continue
        del students[index]
        directory = screenshot_dir(exam["id"], dirname)
        if directory.is_dir():
            shutil.rmtree(directory)
        log = log_path(exam["id"], dirname)
        if log.exists():
            log.unlink()
        return student
    return None


def add_students(exam: dict[str, Any], new_students: list[dict[str, str]]) -> int:
    """Add students to an exam, de-duplicating directory names.

    Returns the number of students that were added.
    """
    taken = {s["dir"].lower() for s in exam.get("students", [])}
    existing_names = {s["name"] for s in exam.get("students", [])}
    added = 0
    for student in new_students:
        name = student["name"]
        # Skip exact duplicates so re-importing the same list is harmless.
        if name in existing_names:
            continue
        entry = {
            "name": name,
            "dir": unique_dirname(name, taken),
        }
        exam.setdefault("students", []).append(entry)
        existing_names.add(name)
        added += 1
    return added


# ---------------------------------------------------------------------------
# Screenshots
# ---------------------------------------------------------------------------
def student_by_dir(exam: dict[str, Any], dirname: str) -> dict[str, Any] | None:
    for student in exam.get("students", []):
        if student["dir"] == dirname:
            return student
    return None


def student_by_name(exam: dict[str, Any], name: str) -> dict[str, Any] | None:
    for student in exam.get("students", []):
        if student["name"] == name:
            return student
    return None


def screenshot_dir(exam_id: str, dirname: str) -> Path:
    # Guard against path traversal.
    safe = Path(dirname).name
    return screenshots_root(exam_id) / safe


def save_screenshot(
    exam_id: str, dirname: str, data: bytes, received_ts: float | None = None
) -> str:
    directory = screenshot_dir(exam_id, dirname)
    directory.mkdir(parents=True, exist_ok=True)
    received_ts = received_ts or time.time()
    millis = int(received_ts * 1000)
    filename = f"{millis}_{secrets.token_hex(3)}.png"
    (directory / filename).write_bytes(data)
    return filename


def list_screenshots(exam_id: str, dirname: str) -> list[dict[str, Any]]:
    """List screenshots for a student, newest first."""
    directory = screenshot_dir(exam_id, dirname)
    if not directory.is_dir():
        return []
    shots = []
    for path in directory.glob("*.png"):
        try:
            stat = path.stat()
        except OSError:
            continue
        millis_part = path.stem.split("_", 1)[0]
        try:
            captured = int(millis_part) / 1000.0
        except ValueError:
            captured = stat.st_mtime
        shots.append(
            {
                "filename": path.name,
                "captured": captured,
                "size": stat.st_size,
            }
        )
    shots.sort(key=lambda s: s["captured"], reverse=True)
    return shots


def latest_screenshot(exam_id: str, dirname: str) -> dict[str, Any] | None:
    shots = list_screenshots(exam_id, dirname)
    return shots[0] if shots else None


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------
def log_path(exam_id: str, dirname: str) -> Path:
    safe = Path(dirname).name
    return logs_dir(exam_id) / f"{safe}.jsonl"


def append_log(
    exam_id: str, dirname: str, event: str, message: str = "", source: str = "student"
) -> dict[str, Any]:
    directory = logs_dir(exam_id)
    directory.mkdir(parents=True, exist_ok=True)
    entry = {
        "id": uuid.uuid4().hex,
        "ts": time.time(),
        "event": event,
        "message": message,
        "source": source,
    }
    with log_path(exam_id, dirname).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")
    return entry


def read_logs(exam_id: str, dirname: str) -> list[dict[str, Any]]:
    path = log_path(exam_id, dirname)
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    entries.sort(key=lambda e: e.get("ts", 0))
    return entries


def read_recent_issues(exam_id: str, since: float = 0.0) -> list[dict[str, Any]]:
    """Return recent issue log entries across all students of an exam."""
    directory = logs_dir(exam_id)
    if not directory.is_dir():
        return []
    issues = []
    for path in directory.glob("*.jsonl"):
        dirname = path.stem
        for entry in read_logs(exam_id, dirname):
            if entry.get("event") in ("stop_sharing", "error", "note") and entry.get(
                "ts", 0
            ) >= since:
                entry = dict(entry)
                entry["dir"] = dirname
                issues.append(entry)
    issues.sort(key=lambda e: e.get("ts", 0))
    return issues
