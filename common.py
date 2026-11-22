import os
import secrets
import sqlite3
from datetime import timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, request, session
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash


def create_base(config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.update(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.environ.get("DATABASE", str(Path(app.instance_path) / "app.db")),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE") == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
        MAX_CONTENT_LENGTH=64 * 1024,
    )
    if config:
        app.config.update(config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    @app.teardown_appcontext
    def close_db(error=None):
        connection = g.pop("db", None)
        if connection:
            connection.close()

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(sqlite3.IntegrityError)
    def constraint_error(error):
        db().rollback()
        return jsonify(error="A record already exists or a referenced record is invalid."), 409

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


def db():
    if "db" not in g:
        from flask import current_app
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def data():
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        from flask import abort
        abort(400, "Send a JSON object.")
    return value


def text(value, field, maximum=150):
    from flask import abort
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        abort(400, f"{field} must contain 1 to {maximum} characters.")
    return value.strip()


def integer(value, field, minimum=0, maximum=100):
    from flask import abort
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        abort(400, f"{field} must be an integer from {minimum} to {maximum}.")
    return value


def pagination():
    from flask import abort
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))
        if page < 1 or not 1 <= limit <= 100:
            raise ValueError
    except ValueError:
        abort(400, "Use page >= 1 and limit between 1 and 100.")
    return page, limit


def install_auth(app, roles=False):
    with app.app_context():
        db().execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'student')")
        db().commit()

    @app.get("/api/session")
    def get_session():
        session.setdefault("csrf", secrets.token_urlsafe(32))
        user = db().execute("SELECT id, username, role FROM users WHERE id=?", (session.get("user_id"),)).fetchone()
        return {"csrf": session["csrf"], "user": dict(user) if user else None}

    @app.before_request
    def csrf_check():
        if request.path.startswith("/api/") and request.method in {"POST", "PUT", "DELETE"}:
            from flask import abort
            token = request.headers.get("X-CSRF-Token", "")
            if not session.get("csrf") or not secrets.compare_digest(token, session["csrf"]):
                abort(403, "Session expired. Reload the page.")

    @app.post("/api/register")
    def register():
        payload = data()
        username = text(payload.get("username"), "Username", 80)
        password = text(payload.get("password"), "Password", 200)
        if len(password) < 10:
            from flask import abort
            abort(400, "Use a password of at least 10 characters.")
        db().execute("INSERT INTO users(username,password,role) VALUES(?,?,?)", (username, generate_password_hash(password), "student" if roles else "user"))
        db().commit()
        return {"message": "Account created. Sign in to continue."}, 201

    @app.post("/api/login")
    def login():
        from flask import abort
        payload = data()
        user = db().execute("SELECT * FROM users WHERE username=?", (text(payload.get("username"), "Username", 80),)).fetchone()
        password = text(payload.get("password"), "Password", 200)
        if not user or not check_password_hash(user["password"], password):
            abort(401, "Invalid username or password.")
        session.clear()
        session.update(user_id=user["id"], csrf=secrets.token_urlsafe(32))
        session.permanent = True
        return {"csrf": session["csrf"], "user": {"id": user["id"], "username": user["username"], "role": user["role"]}}

    @app.post("/api/logout")
    def logout():
        session.clear()
        return {"message": "Signed out."}


def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        from flask import abort
        if not session.get("user_id"):
            abort(401, "Sign in to continue.")
        g.user = db().execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
        if not g.user:
            abort(401, "Sign in to continue.")
        return fn(*args, **kwargs)
    return wrapped
