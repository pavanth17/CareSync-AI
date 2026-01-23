"""Wrapper to run Flask and capture all output"""
import sys
import logging
from app import app

# Set up logging to be very verbose
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s:%(name)s: %(message)s')

if __name__ == "__main__":
    print("=" * 60)
    print("Starting Flask app (with plain Flask, not SocketIO)...")
    print("=" * 60)
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=True)
    except KeyboardInterrupt:
        print("\nShutdown requested")
    except Exception as e:
        print(f"\n✗ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
