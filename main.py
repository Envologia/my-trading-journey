import os
import logging
from app import create_app

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create the Flask application
app = create_app()

if __name__ == "__main__":
    # Get port from environment variable
    port = int(os.environ.get("PORT", 8000))
    
    logger.info(f"Starting Flask app on port {port}")
    app.run(host="0.0.0.0", port=port)
