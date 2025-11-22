#!/usr/bin/env python3
"""
GPSLive Device Tracker for Home Assistant
"""
import os
import sys
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv('DEBUG_LOGGING', 'false').lower() == 'true' else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for the GPSLive Device Tracker."""
    logger.info("GPSLive Device Tracker starting...")
    
    try:
        # Main loop placeholder
        while True:
            logger.debug("GPSLive Device Tracker running...")
            time.sleep(60)
            
    except KeyboardInterrupt:
        logger.info("Shutting down GPSLive Device Tracker...")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
