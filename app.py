import os
import logging
from flask import Flask, session
from database import db
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import timedelta

import warnings

# Import Google Generative AI client if available. Import errors are
# handled so the app can run without the package installed (LLM
# features will be disabled). Also suppress a noisy FutureWarning
# emitted by google.api_core when running on older Python versions.
try:
    warnings.filterwarnings(
        "ignore",
        category=FutureWarning,
        module=r"google\.api_core.*",
    )
except Exception:
    # If filterwarnings fails for any reason, continue without failing
    pass

try:
    import google.generativeai as genai
except Exception:
    genai = None


from database import db

app = Flask(__name__)
# Provide sensible local defaults for development if environment variables are missing
app.secret_key = os.environ.get("SESSION_SECRET", "dev-session-secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Allow a DATABASE_URL env var, otherwise fall back to a local SQLite file for development
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL") or (
    f"sqlite:///{os.path.join(os.path.dirname(__file__), 'patient_care_dev.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=15)
app.config["SESSION_REFRESH_EACH_REQUEST"] = True

# Disable Jinja2 template caching to ensure file changes are reflected
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.cache = None

# Production safety settings: enable stricter defaults when PRODUCTION env var is set
if os.environ.get('PRODUCTION') in ('1', 'true', 'True'):
    # Require a real session secret in production
    if not os.environ.get('SESSION_SECRET'):
        raise RuntimeError('SESSION_SECRET environment variable must be set in production')
    app.secret_key = os.environ.get('SESSION_SECRET')
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # Disable verbose SQL logging
    app.config['SQLALCHEMY_ECHO'] = False
    logging.getLogger().setLevel(logging.INFO)
    logging.info('Running in PRODUCTION mode with secure settings')
else:
    logging.info('Running in development mode')

# Initialize Gemini API - only if the client is installed and a key is set
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") or "AIzaSyAhotGLDkb4vkDsxb-GsKG4_4RsxNgEcD4"
if genai is None:
    gemini_model = None
    logging.info("google.generativeai not installed; running without LLM integration")
elif not GEMINI_API_KEY:
    gemini_model = None
    logging.info("GEMINI_API_KEY not set; AI chat is disabled. Set the GEMINI_API_KEY environment variable to enable it.")
    logging.debug("To enable LLM: set GEMINI_API_KEY env var and restart the app")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Allow overriding the AI model via env var; default to gemini-2.0-flash for all clients
        model_name = os.environ.get("DEFAULT_AI_MODEL", "gemini-2.0-flash")
        try:
            gemini_model = genai.GenerativeModel(model_name)
            logging.info("Gemini API initialized with model %s", model_name)
        except Exception as e:
            logging.error("Failed to initialize GenerativeModel %s: %s", model_name, e)
            # Fallback to a previously used Gemini model if available
            try:
                fallback = "gemini-1.5-flash"
                gemini_model = genai.GenerativeModel(fallback)
                logging.info("Falling back to model %s", fallback)
            except Exception as e2:
                gemini_model = None
                logging.error("Failed to initialize fallback model %s: %s", fallback, e2)
        # Expose the resolved model name in app config for runtime inspection
        app.config['AI_MODEL_NAME'] = model_name
    except Exception as e:
        gemini_model = None
        logging.error("Failed to initialize Gemini API: %s", e)


# Import models so they are registered with SQLAlchemy
import models

db.init_app(app)

with app.app_context():
    db.create_all()
    logging.info("Database tables created")

# Import routes AFTER app is configured
import routes

# Initialize SocketIO
from flask_socketio import SocketIO, join_room, disconnect

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

@socketio.on('connect')
def handle_connect(auth=None):
    if 'staff_id' in session:
        staff_id = session['staff_id']
        room = f"staff_{staff_id}"
        join_room(room)
        logging.info(f"Staff {staff_id} joined room {room}")
    else:
        # Optional: handling for non-staff connections or anonymous
        pass

# Expose socketio to other modules if needed via app context or direct import
app.socketio = socketio

# Start the background simulation task
#import vital_simulator
#vital_simulator.start_simulation(socketio)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
