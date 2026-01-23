#!/usr/bin/env python
"""Run Flask app with exception handling"""
import os
import sys

# Make sure we can see all output
os.environ['PYTHONUNBUFFERED'] = '1'

print("=" * 70)
print("FLASK APP STARTUP")
print("=" * 70)

try:
    print("Importing app module...")
    from app import app
    print("✓ App imported successfully")
    
    print("Starting Flask server on http://0.0.0.0:5000...")
    print("=" * 70)
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=True)
    
except KeyboardInterrupt:
    print("\n✓ Server stopped by user")
    sys.exit(0)
    
except Exception as e:
    print(f"\n✗ ERROR: {type(e).__name__}: {e}")
    import traceback
    print("\nFull traceback:")
    traceback.print_exc()
    sys.exit(1)
