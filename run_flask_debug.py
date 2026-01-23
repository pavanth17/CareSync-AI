"""Run Flask with comprehensive error logging"""
import sys
import logging
import traceback
from app import app

# Set up very detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('flask_debug.log')
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Starting Flask app with detailed logging...")
    logger.info("=" * 60)
    
    try:
        logger.info("Running Flask on port 5000...")
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    except KeyboardInterrupt:
        logger.info("\nShutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
