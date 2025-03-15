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

# Thời gian xem tối thiểu để được tính là view (>30s)
MIN_WATCH_TIME = 35  # Thêm 5s để đảm bảo

# Danh sách các trang để mô phỏng việc tìm đến video từ nguồn hợp lệ
REFERRAL_SITES = [
    "https://www.google.com/search?q=ca+khúc+hay+2023",
    "https://www.google.com/search?q=youtube+music+videos",
    "https://www.google.com/search?q=youtube+trending",
    "https://www.youtube.com/feed/trending",
    "https://www.youtube.com/"
]

# User agents khác nhau để tạo sự đa dạng
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
]

# Khóa tạo đồng bộ cho việc in ra console
print_lock = threading.Lock()

# Tạo thư mục cho profile firefox nếu chưa tồn tại
PROFILES_DIR = "/tmp/firefox_profiles"
os.makedirs(PROFILES_DIR, exist_ok=True)

def simulate_human_behavior(driver):
    """Mô phỏng hành vi người dùng thực: cuộn trang, dừng video, tiếp tục, thay đổi âm lượng"""
    try:
        # Đợi cho đến khi player video được tải
        video = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "video"))
        )
        
        # Tương tác với video như người thật sau 5-10 giây xem
        time.sleep(random.uniform(5, 10))
        
        # Hành động ngẫu nhiên: tạm dừng và tiếp tục
        if random.random() > 0.5:
            driver.find_element(By.TAG_NAME, 'body').send_keys('k')  # Phím tắt pause/play
            time.sleep(random.uniform(1, 3))
            driver.find_element(By.TAG_NAME, 'body').send_keys('k')  # Tiếp tục phát
        
        # Đôi khi cuộn xuống để xem bình luận
        if random.random() > 0.7:
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(random.uniform(2, 5))
            driver.execute_script("window.scrollBy(0, -500);")  # Cuộn lại lên video
        
        # Thỉnh thoảng thay đổi âm lượng
        if random.random() > 0.6:
            driver.find_element(By.TAG_NAME, 'body').send_keys(random.choice(['m', '0']))  # Tắt/bật tiếng hoặc đặt âm lượng về 0

    except (TimeoutException, NoSuchElementException) as e:
        with print_lock:
            print(f"Không thể tương tác với video: {str(e)}")

def view_video(url, session_id, views_per_thread):
    """Hàm xem video với các chiến lược để được tính là view hợp lệ"""
    views_completed = 0
    
    while views_completed < views_per_thread:
        options = Options()
        
        # Thiết lập Firefox headless đúng cách
        options.add_argument("--headless")
        options.add_argument("--disable-dev-shm-usage")  # Hạn chế lỗi bộ nhớ chia sẻ
        options.add_argument("--no-sandbox")  # Tắt sandbox để tránh lỗi
        options.add_argument("--window-size=1280x1024")
                
        # Sử dụng user agent ngẫu nhiên
        user_agent = random.choice(USER_AGENTS)
        options.set_preference("general.useragent.override", user_agent)
        
        # Vô hiệu hóa một số tính năng không cần thiết để tránh lỗi
        options.set_preference("media.volume_scale", "0.0")
        options.set_preference("browser.download.folderList", 2)
        options.set_preference("browser.download.manager.showWhenStarting", False)
        options.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/octet-stream")
        
        # Thiết lập profile mới cho từng phiên
        profile_path = os.path.join(PROFILES_DIR, f"profile-{session_id}-{views_completed}")
        os.makedirs(profile_path, exist_ok=True)
        options.set_preference("profile", profile_path)
        
        # Vô hiệu hóa thông báo và một số tính năng để tránh lỗi
        options.set_preference("dom.webnotifications.enabled", False)
        options.set_preference("app.update.enabled", False)
        
        # Tắt GPU để tránh sự cố trên Docker
        options.set_preference("layers.acceleration.disabled", True)
        
        # Không cần thiết lập -profile hay -private nữa vì đã dùng set_preference
        
        service = Service(executable_path='/usr/local/bin/geckodriver')
        
        try:
            driver = webdriver.Firefox(service=service, options=options)
            
            # Thử thiết lập kích thước cửa sổ trước khi truy cập trang
            driver.set_window_size(1366, 768)
            
            # Đầu tiên truy cập vào một trong các trang giới thiệu
            referral_site = random.choice(REFERRAL_SITES)
            with print_lock:
                print(f"Thread {session_id}: Truy cập {referral_site}")
            
            driver.get(referral_site)
            time.sleep(random.uniform(2, 5))
            
            # Nếu đang ở trang YouTube, tìm kiếm và click vào video liên quan
            if "youtube.com" in referral_site:
                try:
                    # Tìm kiếm trên YouTube
                    search_box = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.NAME, "search_query"))
                    )
                    search_terms = ["ca khúc hay", "bài hát mới", "music video 2023"]
                    search_box.send_keys(random.choice(search_terms))
                    search_box.send_keys(Keys.RETURN)
                    time.sleep(random.uniform(3, 6))
                except Exception as e:
                    with print_lock:
                        print(f"Thread {session_id}: Không thể tìm kiếm trên YouTube: {str(e)}")
            
            # Sau đó truy cập video mục tiêu
            with print_lock:
                print(f"Thread {session_id}: Truy cập video mục tiêu {url}")
                
            driver.get(url)
            
            try:
                # Đợi cho video player xuất hiện
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.TAG_NAME, "video"))
                )
                
                # Làm cho video tự động phát
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.SPACE)
                except Exception as e:
                    with print_lock:
                        print(f"Thread {session_id}: Không thể bắt đầu phát video: {str(e)}")
                
                # Thời gian xem ngẫu nhiên (trên 30 giây để được tính là view hợp lệ)
                watch_time = random.uniform(MIN_WATCH_TIME, MIN_WATCH_TIME + 60)
                
                # Mô phỏng hành vi người dùng trong khi xem
                simulate_human_behavior(driver)
                
                with print_lock:
                    print(f"Thread {session_id}: Đang xem video trong {watch_time:.1f} giây")
                
                # Đợi hết thời gian xem
                time.sleep(watch_time)
                
                views_completed += 1
                with print_lock:
                    print(f"Thread {session_id}: Hoàn thành {views_completed}/{views_per_thread} views")
            
            except TimeoutException:
                with print_lock:
                    print(f"Thread {session_id}: Không thể tải video trong thời gian chờ")
            
            # Thời gian nghỉ ngẫu nhiên giữa các lần xem để tránh bị phát hiện
            time.sleep(random.uniform(5, 15))
        
        except Exception as e:
            with print_lock:
                print(f"Thread {session_id} gặp lỗi: {str(e)}")
        
        finally:
            try:
                driver.quit()
            except Exception as e:
                with print_lock:
                    print(f"Thread {session_id}: Lỗi khi đóng driver: {str(e)}")
                
        # Tạo độ trễ ngẫu nhiên giữa các lần mở trình duyệt mới
        time.sleep(random.uniform(3, 8))


url = "https://www.youtube.com/watch?v=OFQQt_g4ghE"  # URL video mục tiêu
total_views = 1000  # Tổng số view cần đạt
num_threads = 5  # Số luồng chạy song song

print(f"Bắt đầu cày {total_views} views cho video: {url}")
print(f"Sử dụng {num_threads} luồng chạy song song")

# Chia số views cho mỗi thread
views_per_thread = total_views // num_threads
remaining_views = total_views % num_threads

# Tạo và chạy các threads
with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
    futures = []
    for i in range(num_threads):
        # Phân bổ số view còn dư vào các thread đầu tiên
        thread_views = views_per_thread + (1 if i < remaining_views else 0)
        futures.append(executor.submit(view_video, url, i+1, thread_views))
    
    # Đợi tất cả các thread hoàn thành
    concurrent.futures.wait(futures)

print(f"Đã hoàn thành {total_views} views!")