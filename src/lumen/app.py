"""Flask application factory."""

from __future__ import annotations

import os
import secrets

from flask import Flask

from . import auth, store


def _secret_key() -> str:
    env = os.environ.get("LUMEN_SECRET_KEY")
    if env:
        return env
    path = store.DATA_DIR / "secret_key"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    key = secrets.token_hex(32)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(key, encoding="utf-8")
    return key


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.update(
        SECRET_KEY=_secret_key(),
        MAX_CONTENT_LENGTH=32 * 1024 * 1024,  # 32 MB upload cap
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    store.ensure_dirs()
    store.DATA_DIR.mkdir(parents=True, exist_ok=True)

    from .views.api import bp as api_bp
    from .views.auth_views import bp as auth_bp
    from .views.public import bp as public_bp
    from .views.teacher import bp as teacher_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(teacher_bp)

    app.before_request(auth.load_logged_in_user)

    @app.template_filter("dt")
    def format_datetime(value):
        import datetime

        if not value:
            return "-"
        return datetime.datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")

    @app.template_filter("duration")
    def format_duration(value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            return "-"
        if value < 60:
            return f"{value}s"
        if value < 3600:
            return f"{value // 60}m {value % 60}s"
        return f"{value // 3600}h {(value % 3600) // 60}m"

    @app.template_filter("filesize")
    def format_filesize(value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return "-"
        for unit in ("B", "KB", "MB", "GB"):
            if value < 1024 or unit == "GB":
                return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
            value /= 1024
        return f"{value:.1f} GB"

    return app
