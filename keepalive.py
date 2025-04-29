import threading
import time
import requests
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KeepAliveThread(threading.Thread):
    """Thread to ping the server periodically to keep it alive"""
    
    def __init__(self, interval=600):  # 600 seconds = 10 minutes
        super().__init__()
        self.interval = interval
        self.daemon = True  # Make thread a daemon so it exits when main thread exits
        self.host = None
        self.port = os.environ.get('PORT', 5000)  # Default to port 5000
        self.is_running = True
        
    def set_host(self, host):
        """Set the host to ping"""
        self.host = host
        
    def run(self):
        """Run the thread, pinging the server periodically"""
        logger.info(f"Starting keep-alive thread, interval: {self.interval} seconds")
        
        while self.is_running:
            time.sleep(self.interval)
            
            if not self.host:
                # If no host is explicitly set, use the current machine's localhost
                self.ping_url(f"http://localhost:{self.port}/ping")
            else:
                # Use the detected host with https
                self.ping_url(f"https://{self.host}/ping")
    
    def ping_url(self, url):
        """Ping the URL to keep the server alive"""
        try:
            logger.info(f"Pinging {url} to keep server alive...")
            response = requests.get(url, timeout=10)
            logger.info(f"Ping response: {response.status_code}")
            return True
        except Exception as e:
            logger.error(f"Error pinging {url}: {str(e)}")
            return False

# Create the keep-alive thread
keep_alive_thread = KeepAliveThread()

def start_keep_alive(host=None):
    """Start the keep-alive thread with the given host"""
    if host:
        keep_alive_thread.set_host(host)
    
    # Start the thread if it's not already running
    if not keep_alive_thread.is_alive():
        keep_alive_thread.start()
        return True
    return False