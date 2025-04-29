"""
Keep-alive mechanism to prevent Render from putting the app to sleep
"""
import logging
import threading
import time
import requests

# Configure logging
logger = logging.getLogger(__name__)

class KeepAliveThread(threading.Thread):
    """Thread to ping the server periodically to keep it alive"""
    
    def __init__(self, interval=600):  # 600 seconds = 10 minutes
        """Initialize the thread with a ping interval"""
        super().__init__(daemon=True)  # Daemon thread will close when main thread exits
        self.interval = interval
        self.host = None
        self.running = True
        
    def set_host(self, host):
        """Set the host to ping"""
        self.host = host
        logger.info(f"Keep-alive thread updated with host: {host}")
        
    def run(self):
        """Run the thread, pinging the server periodically"""
        while self.running:
            try:
                if self.host:
                    url = f"https://{self.host}/ping"
                    self.ping_url(url)
            except Exception as e:
                logger.error(f"Error in keep-alive thread: {str(e)}")
            
            # Sleep for the specified interval
            time.sleep(self.interval)
            
    def ping_url(self, url):
        """Ping the URL to keep the server alive"""
        try:
            response = requests.get(url, timeout=10)
            logger.info(f"Keep-alive ping to {url}: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to ping {url}: {str(e)}")

# Create a global instance of the thread
keep_alive_thread = KeepAliveThread()

def start_keep_alive(host=None):
    """Start the keep-alive thread with the given host"""
    if host:
        keep_alive_thread.set_host(host)
    
    # Start the thread if it's not already running
    if not keep_alive_thread.is_alive():
        keep_alive_thread.start()
        logger.info("Keep-alive thread started")