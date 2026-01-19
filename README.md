# Patient-Care (Local Run Instructions)

This project is configured to run locally with a SQLite database by default.

Quick start (PowerShell on Windows):

1. Create a virtual environment and activate it:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt  # if you have a requirements file
# or install from pyproject dependencies manually:
python -m pip install apscheduler email-validator flask flask-dance flask-login flask-sqlalchemy gunicorn numpy oauthlib psycopg2-binary pyjwt scikit-learn sqlalchemy werkzeug
```

3. Run a quick smoke test (runs app test client to hit `/`):

```powershell
python .\check_app.py
```

4. Start the development server:

```powershell
python .\main.py
```

The app will create a SQLite file named `patient_care_dev.db` in the project root when first run.

Environment variables:
- `DATABASE_URL` to point to a different database (optional).
- `SESSION_SECRET` to override the Flask session secret (optional).
- `FLASK_DEBUG=1` to enable Flask debug mode.

Notes:
- Replit-specific authentication integration has been removed; the app uses the built-in session-based auth and local `staff_login` route.
