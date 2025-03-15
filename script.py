import time
import random
import threading
import subprocess
import os
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import concurrent.futures

# Minimum watch time to count as a view (>30s)
MIN_WATCH_TIME = 35  # Added 5s to ensure

# List of referral sites to simulate coming from legitimate sources
REFERRAL_SITES = [
    "https://www.google.com/search?q=ca+khúc+hay+2023",
    "https://www.google.com/search?q=youtube+music+videos",
    "https://www.google.com/search?q=youtube+trending",
    "https://www.youtube.com/feed/trending",
    "https://www.youtube.com/"
]

# Various user agents for diversity
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
]

# Lock for synchronized console printing
print_lock = threading.Lock()

# Create directory for Firefox profiles if it doesn't exist
PROFILES_DIR = "/tmp/firefox_profiles"
os.makedirs(PROFILES_DIR, exist_ok=True)

# Create directory for logs
LOGS_DIR = "/tmp/logs"
os.makedirs(LOGS_DIR, exist_ok=True)

# Environment variables with defaults
NUM_THREADS = int(os.environ.get("NUM_THREADS", 3))
TOTAL_VIEWS = int(os.environ.get("TOTAL_VIEWS", 1000))
TARGET_URL = os.environ.get("TARGET_URL", "https://www.youtube.com/watch?v=OFQQt_g4ghE")
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", 3))

def simulate_human_behavior(driver):
    """Simulate real user behavior: scrolling, pausing video, resuming, changing volume"""
    try:
        # Wait until video player loads
        video = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "video"))
        )
        
        # Interact with video like a real person after 5-10 seconds of viewing
        time.sleep(random.uniform(5, 10))
        
        # Random action: pause and resume
        if random.random() > 0.5:
            driver.find_element(By.TAG_NAME, 'body').send_keys('k')  # Shortcut for pause/play
            time.sleep(random.uniform(1, 3))
            driver.find_element(By.TAG_NAME, 'body').send_keys('k')  # Resume playback
        
        # Sometimes scroll down to view comments
        if random.random() > 0.7:
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(random.uniform(2, 5))
            driver.execute_script("window.scrollBy(0, -500);")  # Scroll back to video
        
        # Occasionally change volume
        if random.random() > 0.6:
            driver.find_element(By.TAG_NAME, 'body').send_keys(random.choice(['m', '0']))  # Mute/unmute or set volume to 0

    except (TimeoutException, NoSuchElementException) as e:
        with print_lock:
            print(f"Cannot interact with video: {str(e)}")

def create_driver(session_id, profile_id):
    """Create a Firefox WebDriver instance with proper configuration"""
    options = Options()
    
    # Enable headless mode properly
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Use random user agent
    user_agent = random.choice(USER_AGENTS)
    options.set_preference("general.useragent.override", user_agent)
    
    # Critical settings for stability in containerized environments
    options.set_preference("media.volume_scale", "0.0")
    options.set_preference("browser.sessionstore.resume_from_crash", False)
    options.set_preference("toolkit.startup.max_resumed_crashes", -1)
    options.set_preference("media.autoplay.default", 0)
    options.set_preference("media.autoplay.blocking_policy", 0)
    options.set_preference("media.autoplay.allow-muted", True)
    options.set_preference("media.autoplay.enabled.user-gestures-needed", False)
    
    # Set up new profile for each session
    profile_path = os.path.join(PROFILES_DIR, f"profile-{session_id}-{profile_id}")
    os.makedirs(profile_path, exist_ok=True)
    options.set_preference("profile", profile_path)
    
    # Disable notifications and updates
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("app.update.enabled", False)
    
    # Disable GPU acceleration
    options.set_preference("layers.acceleration.disabled", True)
    
    # Configure marionette
    options.set_preference("marionette.enabled", True)
    options.set_preference("marionette.log.level", "Trace")  # Increase logging level
    
    # Performance settings
    options.set_preference("network.http.connection-timeout", 10)
    options.set_preference("dom.ipc.processCount", 1)
    options.set_preference("javascript.options.mem.gc_frequency", 1500)
    
    # Set log path and create service
    log_path = os.path.join(LOGS_DIR, f"geckodriver-{session_id}-{profile_id}.log")
    service = Service(
        executable_path='/usr/local/bin/geckodriver',
        log_path=log_path
    )
    
    try:
        # Create driver with proper configuration - FIXED: removed service_log_path
        driver = webdriver.Firefox(
            service=service, 
            options=options
        )
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        with print_lock:
            print(f"Thread {session_id}: Failed to create Firefox driver: {str(e)}")
        return None

def view_video(url, session_id, views_per_thread):
    """Function to view video with strategies to count as valid views"""
    views_completed = 0
    profile_id = 0
    max_retries = MAX_RETRIES
    
    while views_completed < views_per_thread:
        driver = None
        profile_id += 1
        retry_count = 0
        
        while retry_count < max_retries and driver is None:
            try:
                # Verify Firefox is running properly before creating driver
                with print_lock:
                    print(f"Thread {session_id}: Starting Firefox (attempt {retry_count + 1})...")
                
                # Create the driver
                driver = create_driver(session_id, profile_id)
                if driver is None:
                    raise Exception("Failed to initialize driver")
                
                with print_lock:
                    print(f"Thread {session_id}: Firefox driver created successfully")
                
                # Try to set window size
                try:
                    driver.set_window_size(1366, 768)
                except Exception:
                    # Not critical if this fails
                    pass
                
                break  # Driver created successfully
                
            except Exception as e:
                retry_count += 1
                with print_lock:
                    print(f"Thread {session_id}: Firefox init attempt {retry_count} failed: {str(e)}")
                
                if driver is not None:
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None
                
                # Process management - check for stray Firefox processes
                try:
                    subprocess.run(["pkill", "-f", "firefox"], stderr=subprocess.DEVNULL)
                    subprocess.run(["pkill", "-f", "geckodriver"], stderr=subprocess.DEVNULL)
                except:
                    pass
                    
                # Wait before retrying
                time.sleep(random.uniform(3, 5))
        
        # If we couldn't create a driver after all retries, skip this iteration
        if driver is None:
            with print_lock:
                print(f"Thread {session_id}: Failed to create Firefox driver after {max_retries} attempts. Skipping.")
            time.sleep(random.uniform(10, 20))
            continue
        
        # Proceed with browser automation
        try:
            # First access one of the referral sites
            referral_site = random.choice(REFERRAL_SITES)
            with print_lock:
                print(f"Thread {session_id}: Accessing {referral_site}")
            
            # Use get with try/except to handle timeouts
            try:
                driver.get(referral_site)
                time.sleep(random.uniform(2, 5))
            except:
                with print_lock:
                    print(f"Thread {session_id}: Timeout on referral site. Continuing to target URL.")
            
            # Then access the target video
            with print_lock:
                print(f"Thread {session_id}: Accessing target video {url}")
            
            try:
                driver.get(url)
            except:
                with print_lock:
                    print(f"Thread {session_id}: Timeout accessing target URL. Skipping this attempt.")
                continue
            
            try:
                # Wait for video player to appear
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "video"))
                )
                
                # Try to start video with multiple methods
                try:
                    # Method 1: Space key
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
                    time.sleep(1)
                    
                    # Method 2: Click on video player
                    video_player = driver.find_element(By.TAG_NAME, 'video')
                    video_player.click()
                    
                    # Method 3: Execute JavaScript to play video
                    driver.execute_script("document.getElementsByTagName('video')[0].play()")
                    
                except Exception as e:
                    with print_lock:
                        print(f"Thread {session_id}: Cannot start video playback: {str(e)}")
                
                # Random watch time (over 30 seconds to count as a valid view)
                watch_time = random.uniform(MIN_WATCH_TIME, MIN_WATCH_TIME + 30)
                
                # Simulate user behavior while watching
                simulate_human_behavior(driver)
                
                with print_lock:
                    print(f"Thread {session_id}: Watching video for {watch_time:.1f} seconds")
                
                # Wait for the watch time
                time.sleep(watch_time)
                
                views_completed += 1
                with print_lock:
                    print(f"Thread {session_id}: Completed {views_completed}/{views_per_thread} views")
            
            except TimeoutException:
                with print_lock:
                    print(f"Thread {session_id}: Could not load video within timeout period")
            
            # Random pause between views to avoid detection
            time.sleep(random.uniform(3, 8))
        
        except WebDriverException as e:
            with print_lock:
                print(f"Thread {session_id} encountered WebDriverException: {str(e)}")
        
        except Exception as e:
            with print_lock:
                print(f"Thread {session_id} encountered an error: {str(e)}")
        
        finally:
            # Always ensure the driver is properly closed
            try:
                if driver is not None:
                    driver.quit()
            except Exception as e:
                with print_lock:
                    print(f"Thread {session_id}: Error when closing driver: {str(e)}")
                
                # Force kill Firefox processes if normal quit fails
                try:
                    subprocess.run(["pkill", "-f", f"firefox.*{session_id}"], stderr=subprocess.DEVNULL)
                except:
                    pass
        
        # Add random delay between browser sessions
        delay = random.uniform(5, 10)
        with print_lock:
            print(f"Thread {session_id}: Waiting {delay:.1f} seconds before next attempt")
        time.sleep(delay)


def main():
    # Get configuration from environment variables
    url = TARGET_URL
    total_views = TOTAL_VIEWS
    num_threads = NUM_THREADS
    
    print(f"Starting to generate {total_views} views for video: {url}")
    print(f"Using {num_threads} parallel threads")
    
    # Check system resources
    try:
        import psutil
        memory = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()
        print(f"System info: {cpu_count} CPUs, {memory.total / (1024*1024):.1f}MB total memory, {memory.available / (1024*1024):.1f}MB available")
        
        # Adjust threads based on available resources
        recommended_threads = max(1, min(cpu_count, int(memory.available / (1024*1024*1024) * 2)))
        if recommended_threads < num_threads:
            print(f"Warning: {num_threads} threads might be too many for available resources. Consider using {recommended_threads} threads instead.")
    except:
        print("Could not check system resources")

    # Divide views among threads
    views_per_thread = total_views // num_threads
    remaining_views = total_views % num_threads
    
    # Create and run threads
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for i in range(num_threads):
            # Distribute remaining views to the first threads
            thread_views = views_per_thread + (1 if i < remaining_views else 0)
            futures.append(executor.submit(view_video, url, i+1, thread_views))
        
        # Wait for all threads to complete
        concurrent.futures.wait(futures)

    print(f"Completed generating views for: {url}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Shutting down...")
        # Force kill Firefox and geckodriver processes
        try:
            subprocess.run(["pkill", "-f", "firefox"], stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "geckodriver"], stderr=subprocess.DEVNULL)
        except:
            pass
        sys.exit(0)