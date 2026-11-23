"""Teacher authentication helpers."""

from __future__ import annotations

import functools
from typing import Callable

from flask import flash, g, redirect, request, session, url_for

from . import store


def current_teacher() -> str | None:
    return session.get("teacher")


def login_required(view: Callable) -> Callable:
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not current_teacher():
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def login(username: str, password: str) -> bool:
    if store.verify_teacher(username, password):
        session.clear()
        session["teacher"] = username
        return True
    return False


def logout() -> None:
    session.clear()


def load_logged_in_user() -> None:
    g.teacher = current_teacher()
