"""Login / logout views."""

from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import auth

bp = Blueprint("auth", __name__)


def _safe_next(target: str | None) -> str:
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return url_for("teacher.exams")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if auth.current_teacher():
        return redirect(url_for("teacher.exams"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if auth.login(username, password):
            return redirect(_safe_next(request.args.get("next")))
        flash("Invalid username or password.", "error")

    return render_template("login.html")


@bp.route("/logout", methods=["POST", "GET"])
def logout():
    auth.logout()
    return redirect(url_for("auth.login"))
