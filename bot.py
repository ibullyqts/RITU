import os
import sys
import time
import random
import datetime
import threading
import gc
import tempfile
import subprocess
import shutil
from concurrent.futures import ThreadPoolExecutor

# --- AUTO-INSTALLER ---
def install_dependencies():
    try:
        import selenium
        import selenium_stealth
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "selenium", "selenium-stealth"])

install_dependencies()

from selenium import webdriver
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options

# --- CONFIGURATION ---
THREADS = 4             
TOTAL_DURATION = 21600  # 6 Hours (Max GitHub Action Free Tier)
BURST_SPEED = (0.1, 0.3) 
SESSION_MIN_SEC = 120   

GLOBAL_SENT = 0
COUNTER_LOCK = threading.Lock()
BROWSER_LAUNCH_LOCK = threading.Lock()

def log_status(agent_id, msg):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    # GitHub automatically masks secrets in logs
    print(f"[{timestamp}] Agent {agent_id} | [Praveer-V100]: {msg}", flush=True)

def kill_ghost_chrome():
    try:
        subprocess.run("pkill -f chrome", shell=True, capture_output=True)
        subprocess.run("pkill -f chromedriver", shell=True, capture_output=True)
    except:
        pass

def get_driver(agent_id):
    with BROWSER_LAUNCH_LOCK:
        time.sleep(3) 
        options = Options()
        
        # 🐧 GITHUB LINUX HEADLESS OPTIMIZATIONS
        options.add_argument("--headless=new") 
        options.add_argument("--no-sandbox")            
        options.add_argument("--disable-dev-shm-usage") 
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--blink-settings=imagesEnabled=false") # Speed boost
        
        mobile_emulation = {
            "deviceMetrics": { "width": 375, "height": 812, "pixelRatio": 3.0 },
            "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
        }
        options.add_experimental_option("mobileEmulation", mobile_emulation)
        
        temp_dir = os.path.join(tempfile.gettempdir(), f"agent_{agent_id}_{int(time.time())}")
        options.add_argument(f"--user-data-dir={temp_dir}")

        driver = webdriver.Chrome(options=options)

        # 🪄 GITHUB RUNNER STEALTH
        stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Linux armv8l", 
            webgl_vendor="ARM",
            renderer="Mali-G76",
            fix_hairline=True,
        )
        driver.custom_temp_path = temp_dir
        return driver

def adaptive_inject(driver, element, text):
    try:
        driver.execute_script("""
            var el = arguments[0];
            el.focus();
            document.execCommand('insertText', false, arguments[1]);
            el.dispatchEvent(new Event('input', { bubbles: true }));
        """, element, text)
        
        try:
            btn = driver.find_element(By.XPATH, "//div[contains(text(), 'Send')] | //button[text()='Send']")
            driver.execute_script("arguments[0].click();", btn)
        except:
            element.send_keys(Keys.ENTER)
        return True
    except:
        return False

def run_life_cycle(agent_id, cookie, target, messages):
    global_start = time.time()
    while (time.time() - global_start) < TOTAL_DURATION:
        driver = None
        temp_path = None
        session_start = time.time()
        try:
            log_status(agent_id, "[START] Launching...")
            driver = get_driver(agent_id)
            temp_path = getattr(driver, 'custom_temp_path', None)
            
            driver.get("https://www.instagram.com/")
            time.sleep(2) 
            driver.add_cookie({'name': 'sessionid', 'value': cookie.strip(), 'path': '/', 'domain': '.instagram.com'})
            driver.refresh()
            time.sleep(5) 
            
            driver.get(f"https://www.instagram.com/direct/t/{target}/")
            time.sleep(5) 
            
            while (time.time() - session_start) < SESSION_MIN_SEC:
                try:
                    box = driver.find_element(By.XPATH, "//textarea | //div[@role='textbox']")
                    msg = random.choice(messages)
                    if adaptive_inject(driver, box, f"{msg} "):
                        with COUNTER_LOCK:
                            global GLOBAL_SENT
                            GLOBAL_SENT += 1
                        log_status(agent_id, f"[SENT] Global Total: {GLOBAL_SENT}")
                except:
                    time.sleep(1)
                    continue
                time.sleep(random.uniform(*BURST_SPEED))
        except: pass
        finally:
            if driver: driver.quit()
            if temp_path: shutil.rmtree(temp_path, ignore_errors=True)
            gc.collect() 
            time.sleep(2) 

def main():
    # 🔐 SECRETS EXTRACTION
    cookie = os.environ.get("INSTA_COOKIE")
    target = os.environ.get("TARGET_THREAD_ID")
    msg_raw = os.environ.get("MESSAGES", "Hello")
    messages = msg_raw.split("|")

    if not cookie or not target:
        print("❌ MISSING SECRETS: Ensure INSTA_COOKIE and TARGET_THREAD_ID are set.")
        sys.exit(1)

    print("\n" + "="*45)
    print("      PRAVEER V100 - GITHUB ENGINE")
    print("      STATUS: 4 AGENTS | HEADLESS")
    print("      MADE BY PRAVEER")
    print("="*45 + "\n")

    kill_ghost_chrome()

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            executor.submit(run_life_cycle, i+1, cookie, target, messages)

if __name__ == "__main__":
    main()
