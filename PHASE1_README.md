# SmartApply — Phase 1 Integration Guide

## What's in this zip
```
app.py                          → REPLACES your current app.py
core.py                         → NEW: shared login_required / get_current_user / get_db
features/
  __init__.py
  profile.py, resume.py, autoapply.py, jobsearch.py,
  tracker.py, saved_jobs.py, notifications.py,
  analytics.py, settings.py     → NEW: one blueprint per sidebar feature
templates/
  layout/base_app.html          → NEW: shared navbar + sidebar shell
  home.html                     → NEW: replaces your old dashboard.html
  features/placeholder.html     → NEW: shared "coming in Phase 2" page
static/css/
  variables.css                 → NEW: design tokens (see note below)
  app_shell.css                 → NEW: navbar + sidebar styles
  home.css                      → NEW: dashboard-only styles
static/js/
  app_shell.js                  → NEW: sidebar collapse, dropdown, mobile menu
  home.js                       → NEW: animated stat counters
```

## Steps to merge into your project

1. **Drop in the new files** at the matching paths in your project root
   (`core.py` and `features/` go next to your existing `app.py`).

2. **Replace `app.py`** with the one in this zip. Every line of your
   existing auth logic (register, login, forgot password, Google OAuth,
   OTP sending) is byte-for-byte identical — the only changes are:
   - `from core import get_current_user, login_required`
   - Blueprint imports + `app.register_blueprint(...)` calls
   - `/dashboard` route logic **moved to `/home`** (per your requirement:
     `return redirect(url_for("home"))` after login)
   - `/dashboard` now just redirects to `/home` (kept as a legacy alias
     so nothing breaks if anything still links to it)
   - Repeated `if "user_id" not in session: ...` blocks replaced with
     the `@login_required` decorator

3. **Delete your old `dashboard.html`** (or keep it, it's just unused now).

4. **CSS token check (important):** `static/css/variables.css` defines
   `--purple-600`, `--gradient-brand`, `--surface-strong`, etc. — the
   same names your `auth.css` already expects from a `home.css`. If you
   already have a file defining these tokens, **don't load both** —
   keep one source of truth. Otherwise just load `variables.css` before
   `auth.css` on your login/register pages too, so those pages match.

5. **Run it:**
   ```bash
   pip install flask python-dotenv werkzeug requests
   python app.py
   ```
   Login → you should land on `/home` with the full dashboard, sidebar,
   and navbar. Every sidebar/feature-card link is clickable and goes to
   a real route — Phase 2+ will replace each placeholder with the real
   feature UI.

## Verified before delivery
I ran an automated smoke test (register → login → confirm redirect to
`/home` → render dashboard → hit all 9 feature routes → logout → confirm
`/home` is protected again). All checks passed.

## What's next (Phase 2)
Tell me which feature to build first — my suggestion is **Create Profile**
first (since Resume Manager and Profile Completion both depend on it),
then Resume Manager, then the rest.
