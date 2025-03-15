import time
import random
import threading
import os
import logging
from concurrent.futures import ThreadPoolExecutor, wait
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Configuration
MIN_WATCH_TIME = 35  # Minimum watch time in seconds (30s + 5s buffer)
MAX_CONCURRENT_BROWSERS = 2  # Limit concurrent browser instances
PROFILES_DIR = "/tmp/firefox_profiles"
os.makedirs(PROFILES_DIR, exist_ok=True)

# Setup logging instead of print locks
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(threadName)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('view_bot')

# Reference sites and user agents
REFERRAL_SITES = [
    "https://www.google.com/search?q=ca+khúc+hay+2023",
    "https://www.google.com/search?q=youtube+music+videos",
    "https://www.google.com/search?q=youtube+trending",
    "https://www.youtube.com/feed/trending",
    "https://www.youtube.com/"
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
]

# Global semaphore to limit concurrent browser instances
browser_semaphore = threading.Semaphore(MAX_CONCURRENT_BROWSERS)
# Global counter for completed views
completed_views = 0
views_lock = threading.Lock()

def get_optimized_firefox_options(session_id, view_num):
    """Create optimized Firefox options to reduce resource usage"""
    options = Options()
    
    # Essential headless settings
    options.add_argument("--headless")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1024x768")  # Reduced window size
    
    # Memory optimization preferences
    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)
    options.set_preference("browser.cache.offline.enable", False)
    options.set_preference("network.http.use-cache", False)
    options.set_preference("media.volume_scale", "0.0")
    
    # Disable unnecessary features
    options.set_preference("browser.tabs.remote.autostart", False)
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("app.update.enabled", False)
    options.set_preference("extensions.update.enabled", False)
    options.set_preference("browser.download.manager.addToRecentDocs", False)
    
    # Lower content process limit
    options.set_preference("dom.ipc.processCount", 1)
    
    # Lower memory limits
    options.set_preference("browser.sessionhistory.max_entries", 5)
    options.set_preference("browser.sessionhistory.max_total_viewers", 1)
    
    # Use low-end device mode
    options.set_preference("layers.acceleration.disabled", True)
    
    # Use random user agent
    user_agent = random.choice(USER_AGENTS)
    options.set_preference("general.useragent.override", user_agent)
    
    # Profile management
    profile_path = os.path.join(PROFILES_DIR, f"profile-{session_id}-{view_num}")
    os.makedirs(profile_path, exist_ok=True)
    options.set_preference("profile", profile_path)
    
    return options

def simulate_human_behavior(driver):
    """Simulate minimal human-like behavior to reduce resource usage"""
    try:
        # Wait for video player to load with reduced timeout
        video = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.TAG_NAME, "video"))
        )
        
        # Reduced interactions
        time.sleep(random.uniform(3, 5))
        
        # Only perform one random action with 30% probability
        if random.random() < 0.3:
            action = random.choice([
                lambda: driver.find_element(By.TAG_NAME, 'body').send_keys('k'),  # Pause/play
                lambda: driver.execute_script("window.scrollBy(0, 300);"),  # Scroll down
                lambda: driver.find_element(By.TAG_NAME, 'body').send_keys('m'),  # Mute
            ])
            action()
    
    except (TimeoutException, NoSuchElementException) as e:
        logger.warning(f"Could not interact with video: {str(e)}")

def view_video(url, session_id, views_per_thread, view_counter):
    """View video function with resource optimizations"""
    views_completed = 0
    
    while views_completed < views_per_thread:
        # Use semaphore to limit concurrent browser instances
        with browser_semaphore:
            driver = None
            try:
                # Get optimized Firefox options
                options = get_optimized_firefox_options(session_id, views_completed)
                
                # Create Firefox service with minimal logging
                service = Service(
                    executable_path='/usr/local/bin/geckodriver',
                    log_path=os.devnull
                )
                
                # Initialize driver
                driver = webdriver.Firefox(service=service, options=options)
                driver.set_page_load_timeout(20)  # Set timeout for page loads
                
                # Access referral site with timeout handling
                referral_site = random.choice(REFERRAL_SITES)
                logger.info(f"Thread {session_id}: Accessing {referral_site}")
                
                try:
                    driver.get(referral_site)
                    time.sleep(random.uniform(1, 3))  # Reduced wait time
                except TimeoutException:
                    logger.warning(f"Thread {session_id}: Timeout accessing referral site, continuing...")
                
                # Access target video
                logger.info(f"Thread {session_id}: Accessing target video {url}")
                try:
                    driver.get(url)
                    
                    # Wait for video player with reasonable timeout
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "video"))
                    )
                    
                    # Try to start video playback
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
                    except Exception:
                        pass  # Ignore if autoplay works
                    
                    # Calculate watch time
                    watch_time = random.uniform(MIN_WATCH_TIME, MIN_WATCH_TIME + 10)  # Reduced max additional time
                    
                    # Minimal human behavior simulation
                    simulate_human_behavior(driver)
                    
                    logger.info(f"Thread {session_id}: Watching video for {watch_time:.1f} seconds")
                    
                    # Sleep in smaller chunks to allow for quicker cleanup if needed
                    chunks = 5
                    chunk_time = watch_time / chunks
                    for _ in range(chunks):
                        time.sleep(chunk_time)
                        if driver is None:  # Check if driver was closed
                            break
                    
                    # Update view counter
                    views_completed += 1
                    with views_lock:
                        view_counter[0] += 1
                        total = view_counter[0]
                    
                    logger.info(f"Thread {session_id}: Completed {views_completed}/{views_per_thread} views (Total: {total})")
                
                except TimeoutException:
                    logger.warning(f"Thread {session_id}: Could not load video within timeout")
                
                # Reduced delay between views
                time.sleep(random.uniform(2, 5))
            
            except Exception as e:
                logger.error(f"Thread {session_id} error: {str(e)}")
            
            finally:
                # Ensure driver is properly closed to free resources
                if driver:
                    try:
                        driver.quit()
                    except Exception as e:
                        logger.error(f"Thread {session_id}: Error closing driver: {str(e)}")
                
                # Clean up profile directory to free disk space
                try:
                    profile_path = os.path.join(PROFILES_DIR, f"profile-{session_id}-{views_completed}")
                    if os.path.exists(profile_path):
                        import shutil
                        shutil.rmtree(profile_path, ignore_errors=True)
                except Exception:
                    pass

def main():
    url = "https://www.youtube.com/watch?v=OFQQt_g4ghE"  # Target video URL
    total_views = 1000  # Total views target
    num_threads = 10  # Increased thread count with limited concurrent browsers
    
    logger.info(f"Starting {total_views} views for video: {url}")
    logger.info(f"Using {num_threads} threads with max {MAX_CONCURRENT_BROWSERS} concurrent browsers")
    
    # Views counter shared between threads
    view_counter = [0]
    
    # Calculate views per thread
    views_per_thread = total_views // num_threads
    remaining_views = total_views % num_threads
    
    # Create and run threads with resource management
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for i in range(num_threads):
            thread_views = views_per_thread + (1 if i < remaining_views else 0)
            futures.append(executor.submit(view_video, url, i+1, thread_views, view_counter))
        
        # Wait for all threads to complete
        wait(futures)
    
    logger.info(f"Completed {view_counter[0]} views!")

if __name__ == "__main__":
    main()