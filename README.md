# 🎓 GradList — Graduation Registry Platform

A full-stack graduation gift registry web application built with Python/Flask, SQLite, and vanilla HTML/CSS/JS. Modeled after TheKnot.com, adapted for graduation celebrations.

---

## Features

- **User Accounts** — Registration, login, secure hashed passwords, sessions
- **Registry Creation** — Custom title, graduate name, school, degree, graduation date, color theme
- **Gift Items** — Add items with title, description, price, quantity, category, external product URL
- **External Registries** — Link Amazon, Target, Zola or any external registry by URL
- **Guest View** — Public shareable registry page, no account required
- **Mark as Purchased** — Guests can mark items as purchased with progress tracking
- **Registry Discovery** — Search/browse all public registries
- **Account Settings** — Edit profile, change password, avatar color
- **Responsive Design** — Works on desktop and mobile

---

## Project Structure

```
grad_registry/
├── app.py               # Main Flask application (routes, auth, DB logic)
├── run.py               # Development server entrypoint
├── seed.py              # Demo data seeder
├── requirements.txt     # Python dependencies
├── gradlist.db          # SQLite database (auto-created)
├── templates/
│   ├── base.html        # Base layout (navbar, footer, flash messages)
│   ├── index.html       # Homepage
│   ├── register.html    # Registration page
│   ├── login.html       # Login page
│   ├── dashboard.html   # User dashboard
│   ├── registry_form.html  # Create/edit registry settings form
│   ├── registry_edit.html  # Full registry management (items, external links)
│   ├── registry_view.html  # Public guest-facing registry page
│   ├── discover.html    # Search/browse registries
│   ├── account.html     # Account settings
│   └── error.html       # 404/403/500 error page
└── static/
    ├── css/main.css     # Complete stylesheet
    └── js/main.js       # UI interactions (modals, tabs, flash, copy)
```

---

## Setup & Installation

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the application
```bash
python run.py
```

Visit: **http://localhost:5000**

The SQLite database (`gradlist.db`) is created automatically on first run.

### 3. (Optional) Load demo data
```bash
python seed.py
```

Demo accounts:
- `jordan@example.com` / `password123`
- `alex@example.com` / `password123`

---

## Key Routes

| Route | Description |
|---|---|
| `GET /` | Homepage with featured registries |
| `GET /discover?q=...` | Search/browse all public registries |
| `GET /register` | Create account |
| `GET /login` | Login |
| `GET /dashboard` | User dashboard (auth required) |
| `GET/POST /registry/new` | Create a registry (auth required) |
| `GET/POST /registry/<slug>/edit` | Manage registry (auth required) |
| `GET /r/<slug>` | Public registry view (no auth needed) |
| `POST /r/<slug>/items/<id>/purchased` | Mark item purchased (no auth needed) |
| `GET/POST /account` | Account settings (auth required) |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | Random token | Flask session secret key |

For production, set `SECRET_KEY` to a stable value:
```bash
export SECRET_KEY="your-secret-key-here"
```

---

## Production Notes

For production deployment:
1. Set a stable `SECRET_KEY` environment variable
2. Switch from SQLite to PostgreSQL by replacing `sqlite3` with `psycopg2`
3. Use a WSGI server like Gunicorn: `gunicorn -w 4 app:app`
4. Set `app.debug = False`
5. Use HTTPS
6. Consider adding rate limiting on auth routes
