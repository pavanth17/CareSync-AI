from app import app, socketio
import routes
import os

if __name__ == "__main__":
    # Run without the reloader by default to keep a single stable process for local testing.
    debug_mode = os.environ.get("FLASK_DEBUG", "0") in ("1", "true", "True")
    socketio.run(app, host="0.0.0.0", port=5000, debug=debug_mode)
