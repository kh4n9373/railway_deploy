import time
import random
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import concurrent.futures
import os

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

def view_video(url, session_id, views_per_thread):
    """Function to view video with strategies to count as valid views"""
    views_completed = 0
    
    while views_completed < views_per_thread:
        driver = None  # Initialize driver variable
        try:
            options = Options()
            
            # Set up Firefox headless properly for Railway.app environment
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            
            # Use random user agent
            user_agent = random.choice(USER_AGENTS)
            options.set_preference("general.useragent.override", user_agent)
            
            # Disable unnecessary features to avoid errors
            options.set_preference("media.volume_scale", "0.0")
            options.set_preference("browser.download.folderList", 2)
            options.set_preference("browser.download.manager.showWhenStarting", False)
            options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")
            
            # Set up new profile for each session
            profile_path = os.path.join(PROFILES_DIR, f"profile-{session_id}-{views_completed}")
            os.makedirs(profile_path, exist_ok=True)
            options.set_preference("profile", profile_path)
            
            # Disable notifications and some features to avoid errors
            options.set_preference("dom.webnotifications.enabled", False)
            options.set_preference("app.update.enabled", False)
            
            # Disable GPU to avoid issues in Docker
            options.set_preference("layers.acceleration.disabled", True)
            
            # Additional preferences for Railway.app stability
            options.set_preference("network.http.connection-timeout", 10)
            options.set_preference("marionette.enabled", True)
            options.set_preference("marionette.port", 2828)
            options.set_preference("dom.ipc.processCount", 1)
            options.set_preference("browser.tabs.remote.autostart", False)
            options.set_preference("browser.tabs.remote.autostart.2", False)
            
            # Try to handle browser session properly
            options.set_preference("browser.sessionstore.resume_from_crash", False)
            options.log.level = "trace"  # Enable detailed logging
            
            service = Service(executable_path='/usr/local/bin/geckodriver')
            service.log_path = f"/tmp/geckodriver-{session_id}.log"  # Enable logging
            
            # Create driver with proper timeout
            driver = webdriver.Firefox(service=service, options=options)
            driver.set_page_load_timeout(30)  # Set page load timeout
            
            # Try to set window size before accessing the page
            try:
                driver.set_window_size(1366, 768)
            except Exception as e:
                with print_lock:
                    print(f"Thread {session_id}: Could not set window size: {str(e)}")
            
            # First access one of the referral sites
            referral_site = random.choice(REFERRAL_SITES)
            with print_lock:
                print(f"Thread {session_id}: Accessing {referral_site}")
            
            driver.get(referral_site)
            time.sleep(random.uniform(2, 5))
            
            # If on YouTube, search and click on related videos
            if "youtube.com" in referral_site:
                try:
                    # Search on YouTube
                    search_box = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.NAME, "search_query"))
                    )
                    search_terms = ["ca khúc hay", "bài hát mới", "music video 2023"]
                    search_box.send_keys(random.choice(search_terms))
                    search_box.send_keys(Keys.RETURN)
                    time.sleep(random.uniform(3, 6))
                except Exception as e:
                    with print_lock:
                        print(f"Thread {session_id}: Cannot search on YouTube: {str(e)}")
            
            # Then access the target video
            with print_lock:
                print(f"Thread {session_id}: Accessing target video {url}")
                
            driver.get(url)
            
            try:
                # Wait for video player to appear
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "video"))
                )
                
                # Make video autoplay
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
                except Exception as e:
                    with print_lock:
                        print(f"Thread {session_id}: Cannot start video playback: {str(e)}")
                
                # Random watch time (over 30 seconds to count as a valid view)
                watch_time = random.uniform(MIN_WATCH_TIME, MIN_WATCH_TIME + 60)
                
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
            time.sleep(random.uniform(5, 15))
        
        except Exception as e:
            with print_lock:
                print(f"Thread {session_id} encountered an error: {str(e)}")
        
        finally:
            try:
                if driver is not None:  # Only try to quit if driver was initialized
                    driver.quit()
            except Exception as e:
                with print_lock:
                    print(f"Thread {session_id}: Error when closing driver: {str(e)}")
                
        # Add random delay between browser sessions
        time.sleep(random.uniform(3, 8))


def main():
    url = "https://www.youtube.com/watch?v=OFQQt_g4ghE"  # Target video URL
    total_views = 1000  # Total number of views needed
    num_threads = 5  # Reduced number of parallel threads for Railway.app

    print(f"Starting to generate {total_views} views for video: {url}")
    print(f"Using {num_threads} parallel threads")

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

    print(f"Completed {total_views} views!")

if __name__ == "__main__":
    main()