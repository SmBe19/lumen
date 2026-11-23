"""Teacher facing views: exam configuration and monitoring."""

from __future__ import annotations

import io
import zipfile

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)

from .. import auth, monitoring, store

bp = Blueprint("teacher", __name__, url_prefix="/teacher")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _owned_exam(exam_id: str, force: bool = False) -> dict:
    exam = store.get_exam(exam_id, force=force)
    if exam is None or exam.get("owner") != auth.current_teacher():
        abort(404)
    return exam


def _clamp_interval(value: str) -> int:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return 30
    return max(1, min(number, 24 * 3600))


def _clamp_scale(value: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.01, min(number, 1.0))


# ---------------------------------------------------------------------------
# Exam list / create
# ---------------------------------------------------------------------------
@bp.get("/exams")
@auth.login_required
def exams():
    return render_template(
        "exams.html",
        exams=store.list_exams(owner=auth.current_teacher(), force=True),
    )


@bp.post("/exams")
@auth.login_required
def create_exam():
    name = request.form.get("name", "").strip() or "Untitled exam"
    exam_key = request.form.get("exam_key", "").strip().upper()
    interval = _clamp_interval(request.form.get("interval", "30"))
    scale = _clamp_scale(request.form.get("scale", "0.5"))
    try:
        exam = store.create_exam(
            name=name,
            owner=auth.current_teacher(),
            exam_key=exam_key or None,
            interval=interval,
            scale=scale,
        )
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("teacher.exams"))
    flash("Exam created.", "success")
    return redirect(url_for("teacher.exam_config", exam_id=exam["id"]))


# ---------------------------------------------------------------------------
# Exam config
# ---------------------------------------------------------------------------
@bp.get("/exams/<exam_id>")
@auth.login_required
def exam_config(exam_id: str):
    # Always read from disk so the teacher never sees stale data.
    exam = _owned_exam(exam_id, force=True)
    return render_template("exam_config.html", exam=exam)


@bp.post("/exams/<exam_id>")
@auth.login_required
def update_config(exam_id: str):
    exam = _owned_exam(exam_id, force=True)
    name = request.form.get("name", "").strip() or exam["name"]
    exam_key = request.form.get("exam_key", "").strip().upper()
    if not exam_key:
        flash("Exam key must not be empty.", "error")
        return redirect(url_for("teacher.exam_config", exam_id=exam_id))
    for other in store.list_exams(force=True):
        if other["id"] != exam_id and other.get("exam_key", "").upper() == exam_key:
            flash("Exam key is already used by another exam.", "error")
            return redirect(url_for("teacher.exam_config", exam_id=exam_id))

    exam["name"] = name
    exam["exam_key"] = exam_key
    exam["interval"] = _clamp_interval(request.form.get("interval", exam["interval"]))
    exam["scale"] = _clamp_scale(request.form.get("scale", exam["scale"]))
    store.save_exam(exam)
    flash("Configuration saved.", "success")
    return redirect(url_for("teacher.exam_config", exam_id=exam_id))


@bp.post("/exams/<exam_id>/recording")
@auth.login_required
def set_recording(exam_id: str):
    exam = _owned_exam(exam_id, force=True)
    action = request.form.get("action", "")
    if action == "start":
        exam["recording"] = True
    elif action == "stop":
        exam["recording"] = False
    store.save_exam(exam)
    target = request.form.get("next") or url_for("teacher.exam_config", exam_id=exam_id)
    if not target.startswith("/"):
        target = url_for("teacher.exam_config", exam_id=exam_id)
    return redirect(target)


@bp.post("/exams/<exam_id>/students/import")
@auth.login_required
def import_students(exam_id: str):
    exam = _owned_exam(exam_id, force=True)
    csv_text = request.form.get("csv", "")
    students = store.parse_student_csv(csv_text)
    added = store.add_students(exam, students)
    store.save_exam(exam)
    if not students:
        flash("No valid students found in the pasted CSV.", "error")
    else:
        flash(f"Imported {added} student(s) ({len(students) - added} duplicates skipped).", "success")
    return redirect(url_for("teacher.exam_config", exam_id=exam_id) + "#students")


@bp.post("/exams/<exam_id>/students/clear")
@auth.login_required
def clear_students(exam_id: str):
    exam = _owned_exam(exam_id, force=True)
    exam["students"] = []
    store.save_exam(exam)
    flash("Student list cleared.", "success")
    return redirect(url_for("teacher.exam_config", exam_id=exam_id) + "#students")


@bp.post("/exams/<exam_id>/delete")
@auth.login_required
def delete_exam(exam_id: str):
    _owned_exam(exam_id, force=True)
    # Deleting the exam directory removes config, screenshots and logs.
    store.delete_exam(exam_id)
    flash("Exam deleted along with its screenshots.", "success")
    return redirect(url_for("teacher.exams"))


# ---------------------------------------------------------------------------
# Monitoring
# ---------------------------------------------------------------------------
@bp.get("/exams/<exam_id>/monitor")
@auth.login_required
def monitor(exam_id: str):
    exam = _owned_exam(exam_id, force=True)
    return render_template("monitor.html", exam=exam)


@bp.get("/exams/<exam_id>/data")
@auth.login_required
def monitor_data(exam_id: str):
    exam = _owned_exam(exam_id)
    overview = monitoring.build_overview(exam)
    overview["issues"] = store.read_recent_issues(
        exam_id, since=(request.args.get("since", type=float) or 0.0)
    )
    return jsonify(overview)


@bp.get("/exams/<exam_id>/image/<dirname>/<filename>")
@auth.login_required
def screenshot_image(exam_id: str, dirname: str, filename: str):
    _owned_exam(exam_id)
    directory = store.screenshot_dir(exam_id, dirname)
    return send_from_directory(directory, filename, mimetype="image/png")


# ---------------------------------------------------------------------------
# Student detail
# ---------------------------------------------------------------------------
@bp.get("/exams/<exam_id>/student/<dirname>")
@auth.login_required
def student_detail(exam_id: str, dirname: str):
    exam = _owned_exam(exam_id, force=True)
    student = store.student_by_dir(exam, dirname)
    if student is None:
        abort(404)
    return render_template(
        "student_detail.html",
        exam=exam,
        student=student,
        screenshots=store.list_screenshots(exam_id, dirname),
        logs=store.read_logs(exam_id, dirname),
    )


@bp.post("/exams/<exam_id>/student/<dirname>/log")
@auth.login_required
def add_student_log(exam_id: str, dirname: str):
    exam = _owned_exam(exam_id, force=True)
    if store.student_by_dir(exam, dirname) is None:
        abort(404)
    message = request.form.get("message", "").strip()
    if message:
        store.append_log(exam_id, dirname, "note", message, source="teacher")
        flash("Log entry added.", "success")
    return redirect(
        url_for("teacher.student_detail", exam_id=exam_id, dirname=dirname)
    )


# ---------------------------------------------------------------------------
# Downloads
# ---------------------------------------------------------------------------
def _zip_students(exam: dict, students: list[dict]) -> io.BytesIO:
    buffer = io.BytesIO()
    exam_id = exam["id"]
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for student in students:
            directory = store.screenshot_dir(exam_id, student["dir"])
            if not directory.is_dir():
                continue
            safe_name = store.clean_dirname(student["name"])
            for path in sorted(directory.glob("*.png")):
                archive.write(path, arcname=f"{safe_name}/{path.name}")
    buffer.seek(0)
    return buffer


@bp.get("/exams/<exam_id>/student/<dirname>/download")
@auth.login_required
def download_student(exam_id: str, dirname: str):
    exam = _owned_exam(exam_id)
    student = store.student_by_dir(exam, dirname)
    if student is None:
        abort(404)
    buffer = _zip_students(exam, [student])
    filename = f"{store.clean_dirname(student['name'])}.zip"
    return send_file(
        buffer, mimetype="application/zip", as_attachment=True, download_name=filename
    )


@bp.get("/exams/<exam_id>/download")
@auth.login_required
def download_all(exam_id: str):
    exam = _owned_exam(exam_id)
    buffer = _zip_students(exam, exam.get("students", []))
    filename = f"{store.clean_dirname(exam['name'])}-screenshots.zip"
    return send_file(
        buffer, mimetype="application/zip", as_attachment=True, download_name=filename
    )
