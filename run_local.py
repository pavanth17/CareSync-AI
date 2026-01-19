"""Run the Flask app in localhost-only mode for development/testing.

This binds to 127.0.0.1 by default and uses the Flask development server.
Usage:
  $env:PORT='5000'; python run_local.py
"""
import os
from app import app

HOST = os.environ.get('HOST', '127.0.0.1')
PORT = int(os.environ.get('PORT', '5000'))

if __name__ == '__main__':
    # Ensure server is only bound to localhost
    print(f"Starting Flask local server on http://{HOST}:{PORT} (localhost-only)")
    app.run(host=HOST, port=PORT, debug=True)
