"""Public (student facing) views."""

from __future__ import annotations

from flask import Blueprint, abort, redirect, render_template, request, url_for

from .. import store

bp = Blueprint("public", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/join", methods=["POST"])
def join():
    key = request.form.get("exam_key", "").strip().upper()
    if not key:
        return redirect(url_for("public.index"))
    return redirect(url_for("public.exam", exam_key=key))


@bp.route("/exam/<exam_key>")
def exam(exam_key: str):
    config = store.get_exam_by_key(exam_key)
    if config is None:
        return render_template("not_found.html", exam_key=exam_key), 404
    return render_template("student.html", exam=config)
