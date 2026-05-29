"""
GradList - Graduation Registry Web Application
Production-ready Flask application with SQLite backend.
"""

import os
import re
import sqlite3
import secrets
import hashlib
import hmac
from datetime import datetime, date
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, g, abort, jsonify
)

# ---------------------------------------------------------------------------
# App Configuration
# ---------------------------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

DATABASE = os.path.join(os.path.dirname(__file__), "gradlist.db")

# ---------------------------------------------------------------------------
# Database Helpers
# ---------------------------------------------------------------------------

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def mutate_db(query, args=()):
    db = get_db()
    cur = db.execute(query, args)
    db.commit()
    return cur.lastrowid


# ---------------------------------------------------------------------------
# Schema Initialization
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    email       TEXT    NOT NULL UNIQUE,
    username    TEXT    NOT NULL UNIQUE,
    password_hash TEXT  NOT NULL,
    full_name   TEXT    NOT NULL,
    bio         TEXT    DEFAULT '',
    avatar_color TEXT   DEFAULT '#6C5CE7',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS registries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    slug          TEXT    NOT NULL UNIQUE,
    title         TEXT    NOT NULL,
    graduate_name TEXT    NOT NULL,
    school        TEXT    NOT NULL DEFAULT '',
    degree        TEXT    NOT NULL DEFAULT '',
    grad_date     TEXT    NOT NULL,
    description   TEXT    DEFAULT '',
    is_public     INTEGER NOT NULL DEFAULT 1,
    cover_color   TEXT    NOT NULL DEFAULT '#6C5CE7',
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS registry_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    registry_id   INTEGER NOT NULL REFERENCES registries(id) ON DELETE CASCADE,
    title         TEXT    NOT NULL,
    description   TEXT    DEFAULT '',
    price         REAL    NOT NULL DEFAULT 0.0,
    quantity_needed INTEGER NOT NULL DEFAULT 1,
    quantity_purchased INTEGER NOT NULL DEFAULT 0,
    product_url   TEXT    DEFAULT '',
    category      TEXT    DEFAULT 'Other',
    is_priority   INTEGER NOT NULL DEFAULT 0,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS external_registries (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    registry_id   INTEGER NOT NULL REFERENCES registries(id) ON DELETE CASCADE,
    name          TEXT    NOT NULL,
    url           TEXT    NOT NULL,
    store_name    TEXT    NOT NULL DEFAULT '',
    description   TEXT    DEFAULT '',
    sort_order    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""


def init_db():
    with app.app_context():
        db = get_db()
        for stmt in SCHEMA.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                db.execute(stmt)
        db.commit()


# ---------------------------------------------------------------------------
# Auth Helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def check_password(stored: str, provided: str) -> bool:
    try:
        salt, hashed = stored.split(":", 1)
        return hmac.compare_digest(
            hashed, hashlib.sha256((salt + provided).encode()).hexdigest()
        )
    except Exception:
        return False


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated


def current_user():
    if "user_id" not in session:
        return None
    return query_db("SELECT * FROM users WHERE id = ?", [session["user_id"]], one=True)


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text or "registry"


def unique_slug(base: str) -> str:
    slug = slugify(base)
    candidate = slug
    suffix = 1
    while query_db("SELECT id FROM registries WHERE slug = ?", [candidate], one=True):
        candidate = f"{slug}-{suffix}"
        suffix += 1
    return candidate


def validate_url(url: str) -> bool:
    if not url:
        return True
    return url.startswith("http://") or url.startswith("https://")


ITEM_CATEGORIES = [
    "Tech & Electronics",
    "Books & Education",
    "Home & Kitchen",
    "Clothing & Accessories",
    "Experiences & Travel",
    "Career & Professional",
    "Fitness & Wellness",
    "Entertainment",
    "Cash Fund",
    "Other",
]

STORE_CHOICES = [
    ("Amazon", "Amazon"),
    ("Target", "Target"),
    ("Best Buy", "Best Buy"),
    ("Etsy", "Etsy"),
    ("Zola", "Zola"),
    ("Walmart", "Walmart"),
    ("Crate & Barrel", "Crate & Barrel"),
    ("Nordstrom", "Nordstrom"),
    ("Other", "Other"),
]

COVER_COLORS = [
    "#6C5CE7", "#00B894", "#E17055", "#0984E3",
    "#FDCB6E", "#E84393", "#2D3436", "#55EFC4",
]


# ---------------------------------------------------------------------------
# Context Processor
# ---------------------------------------------------------------------------

@app.context_processor
def inject_globals():
    return {
        "current_user": current_user(),
        "now": datetime.utcnow(),
        "item_categories": ITEM_CATEGORIES,
        "cover_colors": COVER_COLORS,
    }


# ---------------------------------------------------------------------------
# Public Routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET", "HEAD"])
def index():
    featured = query_db(
        """SELECT r.*, u.full_name
           FROM registries r JOIN users u ON r.user_id = u.id
           WHERE r.is_public = 1
           ORDER BY r.created_at DESC LIMIT 6"""
    )
    return render_template("index.html", featured=featured)


@app.route("/discover")
def discover():
    q = request.args.get("q", "").strip()
    page = max(1, int(request.args.get("page", 1)))
    per_page = 12
    offset = (page - 1) * per_page

    if q:
        like = f"%{q}%"
        registries = query_db(
            """SELECT r.*, u.full_name,
                      (SELECT COUNT(*) FROM registry_items WHERE registry_id = r.id) AS item_count
               FROM registries r JOIN users u ON r.user_id = u.id
               WHERE r.is_public = 1
                 AND (r.title LIKE ? OR r.graduate_name LIKE ? OR r.school LIKE ?)
               ORDER BY r.created_at DESC LIMIT ? OFFSET ?""",
            [like, like, like, per_page, offset],
        )
        total = query_db(
            """SELECT COUNT(*) AS c FROM registries r
               WHERE r.is_public = 1
                 AND (r.title LIKE ? OR r.graduate_name LIKE ? OR r.school LIKE ?)""",
            [like, like, like], one=True,
        )["c"]
    else:
        registries = query_db(
            """SELECT r.*, u.full_name,
                      (SELECT COUNT(*) FROM registry_items WHERE registry_id = r.id) AS item_count
               FROM registries r JOIN users u ON r.user_id = u.id
               WHERE r.is_public = 1
               ORDER BY r.created_at DESC LIMIT ? OFFSET ?""",
            [per_page, offset],
        )
        total = query_db(
            "SELECT COUNT(*) AS c FROM registries WHERE is_public = 1", one=True
        )["c"]

    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template(
        "discover.html",
        registries=registries,
        q=q,
        page=page,
        total_pages=total_pages,
        total=total,
    )


# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not email or "@" not in email:
            errors.append("Valid email is required.")
        if not username or len(username) < 3:
            errors.append("Username must be at least 3 characters.")
        if not re.match(r"^[a-z0-9_-]+$", username):
            errors.append("Username may only contain letters, numbers, underscores, and hyphens.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if query_db("SELECT id FROM users WHERE email = ?", [email], one=True):
            errors.append("That email is already registered.")
        if query_db("SELECT id FROM users WHERE username = ?", [username], one=True):
            errors.append("That username is taken.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form=request.form)

        colors = ["#6C5CE7", "#00B894", "#E17055", "#0984E3", "#FDCB6E", "#E84393"]
        color = secrets.choice(colors)
        uid = mutate_db(
            "INSERT INTO users (email, username, password_hash, full_name, avatar_color) VALUES (?,?,?,?,?)",
            [email, username, hash_password(password), full_name, color],
        )
        session["user_id"] = uid
        session.permanent = True
        flash(f"Welcome to GradList, {full_name}! 🎓 Start building your registry.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html", form={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")
        next_url = request.form.get("next", "")

        user = query_db(
            "SELECT * FROM users WHERE email = ? OR username = ?",
            [identifier, identifier], one=True,
        )
        if user and check_password(user["password_hash"], password):
            session["user_id"] = user["id"]
            session.permanent = True
            flash(f"Welcome back, {user['full_name']}! 🎓", "success")
            return redirect(next_url or url_for("dashboard"))

        flash("Invalid email/username or password.", "error")
        return render_template("login.html", identifier=identifier, next=next_url)

    return render_template("login.html", identifier="", next=request.args.get("next", ""))


@app.route("/logout")
def logout():
    session.clear()
    flash("You've been logged out.", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    registries = query_db(
        """SELECT r.*,
                  (SELECT COUNT(*) FROM registry_items WHERE registry_id = r.id) AS item_count,
                  (SELECT COUNT(*) FROM external_registries WHERE registry_id = r.id) AS ext_count
           FROM registries r WHERE r.user_id = ?
           ORDER BY r.created_at DESC""",
        [user["id"]],
    )
    return render_template("dashboard.html", user=user, registries=registries)


# ---------------------------------------------------------------------------
# Registry CRUD
# ---------------------------------------------------------------------------

@app.route("/registry/new", methods=["GET", "POST"])
@login_required
def new_registry():
    user = current_user()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        graduate_name = request.form.get("graduate_name", "").strip()
        school = request.form.get("school", "").strip()
        degree = request.form.get("degree", "").strip()
        grad_date = request.form.get("grad_date", "").strip()
        description = request.form.get("description", "").strip()
        cover_color = request.form.get("cover_color", "#6C5CE7").strip()
        is_public = 1 if request.form.get("is_public") else 0

        errors = []
        if not title:
            errors.append("Registry title is required.")
        if not graduate_name:
            errors.append("Graduate name is required.")
        if not grad_date:
            errors.append("Graduation date is required.")
        if cover_color not in COVER_COLORS:
            cover_color = "#6C5CE7"

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("registry_form.html", user=user, form=request.form, edit=False)

        slug_base = f"{graduate_name}-{title}"
        slug = unique_slug(slug_base)

        rid = mutate_db(
            """INSERT INTO registries
               (user_id, slug, title, graduate_name, school, degree, grad_date, description, is_public, cover_color)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            [user["id"], slug, title, graduate_name, school, degree, grad_date, description, is_public, cover_color],
        )
        flash("Registry created! Start adding gifts. 🎁", "success")
        return redirect(url_for("edit_registry", slug=slug))

    return render_template("registry_form.html", user=user, form={}, edit=False)


@app.route("/registry/<slug>/edit", methods=["GET", "POST"])
@login_required
def edit_registry(slug):
    user = current_user()
    registry = query_db("SELECT * FROM registries WHERE slug = ?", [slug], one=True)
    if not registry or registry["user_id"] != user["id"]:
        abort(404)

    if request.method == "POST":
        action = request.form.get("action", "save")

        if action == "delete":
            mutate_db("DELETE FROM registries WHERE id = ?", [registry["id"]])
            flash("Registry deleted.", "info")
            return redirect(url_for("dashboard"))

        title = request.form.get("title", "").strip()
        graduate_name = request.form.get("graduate_name", "").strip()
        school = request.form.get("school", "").strip()
        degree = request.form.get("degree", "").strip()
        grad_date = request.form.get("grad_date", "").strip()
        description = request.form.get("description", "").strip()
        cover_color = request.form.get("cover_color", "#6C5CE7").strip()
        is_public = 1 if request.form.get("is_public") else 0

        errors = []
        if not title:
            errors.append("Registry title is required.")
        if not graduate_name:
            errors.append("Graduate name is required.")
        if not grad_date:
            errors.append("Graduation date is required.")
        if cover_color not in COVER_COLORS:
            cover_color = registry["cover_color"]

        if errors:
            for e in errors:
                flash(e, "error")
        else:
            mutate_db(
                """UPDATE registries SET title=?, graduate_name=?, school=?, degree=?,
                   grad_date=?, description=?, is_public=?, cover_color=?
                   WHERE id=?""",
                [title, graduate_name, school, degree, grad_date, description, is_public, cover_color, registry["id"]],
            )
            flash("Registry updated!", "success")
            registry = query_db("SELECT * FROM registries WHERE id = ?", [registry["id"]], one=True)

    items = query_db(
        "SELECT * FROM registry_items WHERE registry_id = ? ORDER BY is_priority DESC, sort_order ASC, created_at DESC",
        [registry["id"]],
    )
    external = query_db(
        "SELECT * FROM external_registries WHERE registry_id = ? ORDER BY sort_order ASC, created_at ASC",
        [registry["id"]],
    )
    return render_template(
        "registry_edit.html",
        user=user, registry=registry, items=items, external=external,
        form=registry, edit=True,
        store_choices=STORE_CHOICES,
    )


# ---------------------------------------------------------------------------
# Registry Items
# ---------------------------------------------------------------------------

@app.route("/registry/<slug>/items/add", methods=["POST"])
@login_required
def add_item(slug):
    user = current_user()
    registry = query_db("SELECT * FROM registries WHERE slug = ?", [slug], one=True)
    if not registry or registry["user_id"] != user["id"]:
        abort(403)

    title = request.form.get("item_title", "").strip()
    description = request.form.get("item_description", "").strip()
    price_raw = request.form.get("item_price", "0").strip()
    qty_raw = request.form.get("item_quantity", "1").strip()
    product_url = request.form.get("item_url", "").strip()
    category = request.form.get("item_category", "Other").strip()
    is_priority = 1 if request.form.get("item_priority") else 0

    errors = []
    if not title:
        errors.append("Item title is required.")
    try:
        price = round(float(price_raw), 2) if price_raw else 0.0
        if price < 0:
            raise ValueError
    except ValueError:
        errors.append("Price must be a positive number.")
        price = 0.0
    try:
        qty = int(qty_raw)
        if qty < 1:
            raise ValueError
    except ValueError:
        errors.append("Quantity must be at least 1.")
        qty = 1
    if product_url and not validate_url(product_url):
        errors.append("Product URL must start with http:// or https://")
    if category not in ITEM_CATEGORIES:
        category = "Other"

    if errors:
        for e in errors:
            flash(e, "error")
    else:
        mutate_db(
            """INSERT INTO registry_items
               (registry_id, title, description, price, quantity_needed, product_url, category, is_priority)
               VALUES (?,?,?,?,?,?,?,?)""",
            [registry["id"], title, description, price, qty, product_url, category, is_priority],
        )
        flash(f'"{title}" added to your registry!', "success")

    return redirect(url_for("edit_registry", slug=slug))


@app.route("/registry/<slug>/items/<int:item_id>/edit", methods=["POST"])
@login_required
def edit_item(slug, item_id):
    user = current_user()
    registry = query_db("SELECT * FROM registries WHERE slug = ?", [slug], one=True)
    if not registry or registry["user_id"] != user["id"]:
        abort(403)
    item = query_db(
        "SELECT * FROM registry_items WHERE id = ? AND registry_id = ?",
        [item_id, registry["id"]], one=True,
    )
    if not item:
        abort(404)

    title = request.form.get("item_title", "").strip()
    description = request.form.get("item_description", "").strip()
    price_raw = request.form.get("item_price", "0").strip()
    qty_raw = request.form.get("item_quantity", "1").strip()
    product_url = request.form.get("item_url", "").strip()
    category = request.form.get("item_category", "Other").strip()
    is_priority = 1 if request.form.get("item_priority") else 0

    errors = []
    if not title:
        errors.append("Item title is required.")
    try:
        price = round(float(price_raw), 2)
    except ValueError:
        errors.append("Invalid price.")
        price = item["price"]
    try:
        qty = max(1, int(qty_raw))
    except ValueError:
        errors.append("Invalid quantity.")
        qty = item["quantity_needed"]
    if product_url and not validate_url(product_url):
        errors.append("Product URL must start with http:// or https://")

    if errors:
        for e in errors:
            flash(e, "error")
    else:
        mutate_db(
            """UPDATE registry_items SET title=?, description=?, price=?,
               quantity_needed=?, product_url=?, category=?, is_priority=? WHERE id=?""",
            [title, description, price, qty, product_url, category, is_priority, item_id],
        )
        flash("Item updated!", "success")

    return redirect(url_for("edit_registry", slug=slug))


@app.route("/registry/<slug>/items/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_item(slug, item_id):
    user = current_user()
    registry = query_db("SELECT * FROM registries WHERE slug = ?", [slug], one=True)
    if not registry or registry["user_id"] != user["id"]:
        abort(403)
    mutate_db(
        "DELETE FROM registry_items WHERE id = ? AND registry_id = ?",
        [item_id, registry["id"]],
    )
    flash("Item removed.", "info")
    return redirect(url_for("edit_registry", slug=slug))


@app.route("/registry/<slug>/items/<int:item_id>/purchased", methods=["POST"])
def mark_purchased(slug, item_id):
    """Guests can mark items as purchased (no login required)."""
    registry = query_db("SELECT * FROM registries WHERE slug = ? AND is_public = 1", [slug], one=True)
    if not registry:
        abort(404)
    item = query_db(
        "SELECT * FROM registry_items WHERE id = ? AND registry_id = ?",
        [item_id, registry["id"]], one=True,
    )
    if not item:
        abort(404)

    qty_purchased = item["quantity_purchased"]
    qty_needed = item["quantity_needed"]
    if qty_purchased < qty_needed:
        mutate_db(
            "UPDATE registry_items SET quantity_purchased = quantity_purchased + 1 WHERE id = ?",
            [item_id],
        )
        flash("Marked as purchased! The graduate will love it. 🎓", "success")
    else:
        flash("This item has already been fully purchased.", "info")

    return redirect(url_for("view_registry", slug=slug))


# ---------------------------------------------------------------------------
# External Registries
# ---------------------------------------------------------------------------

@app.route("/registry/<slug>/external/add", methods=["POST"])
@login_required
def add_external(slug):
    user = current_user()
    registry = query_db("SELECT * FROM registries WHERE slug = ?", [slug], one=True)
    if not registry or registry["user_id"] != user["id"]:
        abort(403)

    name = request.form.get("ext_name", "").strip()
    url = request.form.get("ext_url", "").strip()
    store_name = request.form.get("ext_store", "").strip()
    description = request.form.get("ext_description", "").strip()

    errors = []
    if not name:
        errors.append("Registry name is required.")
    if not url:
        errors.append("Registry URL is required.")
    elif not validate_url(url):
        errors.append("URL must start with http:// or https://")

    if errors:
        for e in errors:
            flash(e, "error")
    else:
        mutate_db(
            """INSERT INTO external_registries (registry_id, name, url, store_name, description)
               VALUES (?,?,?,?,?)""",
            [registry["id"], name, url, store_name, description],
        )
        flash(f'"{name}" external registry linked!', "success")

    return redirect(url_for("edit_registry", slug=slug))


@app.route("/registry/<slug>/external/<int:ext_id>/delete", methods=["POST"])
@login_required
def delete_external(slug, ext_id):
    user = current_user()
    registry = query_db("SELECT * FROM registries WHERE slug = ?", [slug], one=True)
    if not registry or registry["user_id"] != user["id"]:
        abort(403)
    mutate_db(
        "DELETE FROM external_registries WHERE id = ? AND registry_id = ?",
        [ext_id, registry["id"]],
    )
    flash("External registry removed.", "info")
    return redirect(url_for("edit_registry", slug=slug))


# ---------------------------------------------------------------------------
# Public Registry View
# ---------------------------------------------------------------------------

@app.route("/r/<slug>")
def view_registry(slug):
    registry = query_db(
        """SELECT r.*, u.full_name AS owner_name, u.username AS owner_username
           FROM registries r JOIN users u ON r.user_id = u.id
           WHERE r.slug = ?""",
        [slug], one=True,
    )
    if not registry:
        abort(404)

    user = current_user()
    is_owner = user and user["id"] == registry["user_id"]

    if not registry["is_public"] and not is_owner:
        abort(404)

    category_filter = request.args.get("cat", "").strip()
    show_purchased = request.args.get("show_purchased", "1") == "1"

    items_query = """
        SELECT * FROM registry_items WHERE registry_id = ?
    """
    args = [registry["id"]]

    if category_filter and category_filter in ITEM_CATEGORIES:
        items_query += " AND category = ?"
        args.append(category_filter)

    if not show_purchased:
        items_query += " AND quantity_purchased < quantity_needed"

    items_query += " ORDER BY is_priority DESC, sort_order ASC, created_at DESC"

    items = query_db(items_query, args)
    external = query_db(
        "SELECT * FROM external_registries WHERE registry_id = ? ORDER BY sort_order ASC",
        [registry["id"]],
    )

    categories_used = query_db(
        "SELECT DISTINCT category FROM registry_items WHERE registry_id = ? ORDER BY category",
        [registry["id"]],
    )

    total_items = query_db(
        "SELECT COUNT(*) AS c FROM registry_items WHERE registry_id = ?",
        [registry["id"]], one=True,
    )["c"]
    purchased_items = query_db(
        "SELECT COUNT(*) AS c FROM registry_items WHERE registry_id = ? AND quantity_purchased >= quantity_needed",
        [registry["id"]], one=True,
    )["c"]
    total_value = query_db(
        "SELECT COALESCE(SUM(price * quantity_needed), 0) AS v FROM registry_items WHERE registry_id = ?",
        [registry["id"]], one=True,
    )["v"]

    return render_template(
        "registry_view.html",
        registry=registry,
        items=items,
        external=external,
        is_owner=is_owner,
        category_filter=category_filter,
        show_purchased=show_purchased,
        categories_used=categories_used,
        total_items=total_items,
        purchased_items=purchased_items,
        total_value=total_value,
    )


# ---------------------------------------------------------------------------
# Account Settings
# ---------------------------------------------------------------------------

@app.route("/account", methods=["GET", "POST"])
@login_required
def account():
    user = current_user()

    if request.method == "POST":
        action = request.form.get("action", "profile")

        if action == "profile":
            full_name = request.form.get("full_name", "").strip()
            bio = request.form.get("bio", "").strip()
            avatar_color = request.form.get("avatar_color", user["avatar_color"]).strip()

            if not full_name:
                flash("Name is required.", "error")
            else:
                if avatar_color not in COVER_COLORS:
                    avatar_color = user["avatar_color"]
                mutate_db(
                    "UPDATE users SET full_name=?, bio=?, avatar_color=? WHERE id=?",
                    [full_name, bio, avatar_color, user["id"]],
                )
                flash("Profile updated!", "success")

        elif action == "password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            confirm_pw = request.form.get("confirm_password", "")

            if not check_password(user["password_hash"], current_pw):
                flash("Current password is incorrect.", "error")
            elif len(new_pw) < 8:
                flash("New password must be at least 8 characters.", "error")
            elif new_pw != confirm_pw:
                flash("New passwords do not match.", "error")
            else:
                mutate_db(
                    "UPDATE users SET password_hash=? WHERE id=?",
                    [hash_password(new_pw), user["id"]],
                )
                flash("Password changed successfully!", "success")

        return redirect(url_for("account"))

    return render_template("account.html", user=user)


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------

def _error_page(code, message):
    try:
        return render_template("error.html", code=code, message=message), code
    except Exception:
        html = f"""<!DOCTYPE html>
<html><head><title>{code} Error - GradList</title>
<style>body{{font-family:sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#FAFAF7}}
.box{{text-align:center;max-width:480px;padding:40px}}
h1{{font-size:5rem;color:#e2e4e8;margin:0}}h2{{color:#1B2845;margin:8px 0 12px}}
p{{color:#5C6370;margin-bottom:24px}}
a{{display:inline-block;margin:4px;padding:10px 22px;border-radius:12px;text-decoration:none;font-weight:600}}
.primary{{background:#1B2845;color:#fff}}.outline{{border:2px solid #e2e4e8;color:#1B2845}}</style>
</head><body><div class="box">
<h1>{code}</h1><h2>{"Page Not Found" if code==404 else "Access Denied" if code==403 else "Something Went Wrong"}</h2>
<p>{message}</p>
<a href="/" class="primary">Go Home</a> <a href="/discover" class="outline">Find a Registry</a>
</div></body></html>"""
        return html, code


@app.errorhandler(404)
def not_found(e):
    return _error_page(404, "Page not found.")


@app.errorhandler(403)
def forbidden(e):
    return _error_page(403, "Access denied.")


@app.errorhandler(500)
def server_error(e):
    return _error_page(500, "Something went wrong on our end.")


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

with app.app_context():
    init_db()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
