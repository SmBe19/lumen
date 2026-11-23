"""Student facing JSON API.

The exam key is the only credential here. It may be used to read the small
amount of configuration needed on the student machine and to submit
screenshots / log entries. It never grants access to other exams.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from .. import store

bp = Blueprint("api", __name__, url_prefix="/api")


def _json_error(message: str, status: int):
    response = jsonify({"status": "error", "message": message})
    response.status_code = status
    return response


@bp.get("/exam/<exam_key>/config")
def exam_config(exam_key: str):
    exam = store.get_exam_by_key(exam_key)
    if exam is None:
        return _json_error("unknown exam key", 404)
    return jsonify(
        {
            "status": "ok",
            "recording": bool(exam.get("recording")),
            "interval": exam.get("interval", 10),
            "scale": exam.get("scale", 0.5),
            "exam_name": exam.get("name", ""),
            "students": [s["name"] for s in exam.get("students", [])],
        }
    )


@bp.post("/exam/<exam_key>/screenshot")
def submit_screenshot(exam_key: str):
    exam = store.get_exam_by_key(exam_key)
    if exam is None:
        return _json_error("unknown exam key", 404)

    # A teacher page always reads from disk; here the 30s cache is fine.
    name = (request.form.get("name") or "").strip()
    student = store.student_by_name(exam, name)
    if student is None:
        return _json_error("unknown student", 400)

    if not exam.get("recording"):
        return jsonify({"status": "discarded", "reason": "not recording"})

    upload = request.files.get("screenshot")
    if upload is None:
        return _json_error("missing screenshot", 400)

    data = upload.read()
    if not data:
        return _json_error("empty screenshot", 400)

    filename = store.save_screenshot(exam["id"], student["dir"], data)
    return jsonify({"status": "ok", "filename": filename})


@bp.post("/exam/<exam_key>/log")
def submit_log(exam_key: str):
    exam = store.get_exam_by_key(exam_key)
    if exam is None:
        return _json_error("unknown exam key", 404)

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    student = store.student_by_name(exam, name)
    if student is None:
        return _json_error("unknown student", 400)

    event = (payload.get("event") or "event").strip()[:64]
    message = (payload.get("message") or "").strip()[:1000]
    store.append_log(
        exam["id"], student["dir"], event, message, source="student"
    )
    return jsonify({"status": "ok"})
