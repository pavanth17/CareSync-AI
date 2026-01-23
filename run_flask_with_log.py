#!/usr/bin/env python
"""Flask app runner with output logging"""
import sys
import time
import os

log_file = os.path.join(os.path.dirname(__file__), 'startup.log')

with open(log_file, 'w') as f:
    f.write(f"{time.strftime('%H:%M:%S')} - Starting app import...\n")
    f.flush()

try:
    from app import app
    with open(log_file, 'a') as f:
        f.write(f"{time.strftime('%H:%M:%S')} - App imported successfully\n")
        f.flush()
    
    # Run Flask
    with open(log_file, 'a') as f:
        f.write(f"{time.strftime('%H:%M:%S')} - Starting Flask server on port 5000\n")
        f.flush()
    
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
    
except Exception as e:
    with open(log_file, 'a') as f:
        f.write(f"{time.strftime('%H:%M:%S')} - ERROR: {e}\n")
        import traceback
        f.write(traceback.format_exc())
        f.flush()
    sys.exit(1)
