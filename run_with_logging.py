#!/usr/bin/env python
"""Run Flask with maximum debugging"""
import os
import sys
import logging

# Ensure unbuffered output
os.environ['PYTHONUNBUFFERED'] = '1'

# Configure logging to be very verbose
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# Also capture all werkzeug logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.DEBUG)

print("=" * 70)
print("FLASK APP WITH FULL DEBUG LOGGING")
print("=" * 70)

try:
    print("\n[INFO] Importing app...")
    from app import app
    print("[OK] App imported")
    
    # Add a before_request handler to log all requests
    @app.before_request
    def log_request():
        from flask import request
        print(f"\n[REQUEST] {request.method} {request.path}")
        print(f"[REQUEST] Form data: {request.form.to_dict()}")
    
    # Add an error handler to catch all exceptions
    @app.errorhandler(Exception)
    def handle_error(error):
        print(f"\n[ERROR] Exception caught: {type(error).__name__}: {error}")
        import traceback
        traceback.print_exc()
        return f"Error: {error}", 500
    
    print("[INFO] Starting Flask on http://0.0.0.0:5000\n")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=True)
    
except KeyboardInterrupt:
    print("\n\n[OK] Server stopped by user")
    sys.exit(0)
except Exception as e:
    print(f"\n\n[FATAL] {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
