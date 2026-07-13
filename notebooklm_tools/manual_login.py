import os
import time
import json
from urllib.parse import urlparse
from pathlib import Path
from dotenv import load_dotenv
import undetected_chromedriver as uc

load_dotenv()

def run_manual_login():
    options = uc.ChromeOptions()

    user_data_dir = Path.home() / ".notebooklm" / "chrome_profile"
    driver = uc.Chrome(options=options, version_main=149)

    print("🌍 Navigating to NotebookLM...")
    driver.get("https://notebooklm.google.com/")
    
    print("\n========================================================")
    print("🛑 PLEASE LOG IN MANUALLY IN THE OPEN BROWSER WINDOW! 🛑")
    print("========================================================\n")
    
    # Wait until the URL changes to indicate a successful login to NotebookLM
    timeout = 180
    start_time = time.time()
    while time.time() - start_time < timeout:
        if "accounts.google.com" not in driver.current_url and "notebooklm.google.com" in driver.current_url:
            break
        time.sleep(2)
        print("Waiting for you to log in...")
    
    print("\n✅ Login detected! Saving cookies...")
    time.sleep(5)  # Let cookies settle
    
    selenium_cookies = driver.get_cookies()
    playwright_cookies = []
    for c in selenium_cookies:
        pc = {
            "name": c["name"],
            "value": c["value"],
            "domain": c["domain"],
            "path": c["path"],
            "expires": c.get("expiry", -1),
            "httpOnly": c.get("httpOnly", False),
            "secure": c.get("secure", False),
            "sameSite": c.get("sameSite", "Lax")
        }
        playwright_cookies.append(pc)

    state = {
        "cookies": playwright_cookies,
        "origins": []
    }

    state_path = Path.home() / ".notebooklm" / "profiles" / "default" / "storage_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)

    print(f"🎉 Cookies saved to {state_path}!")
    print("You can now safely copy these cookies to GitHub Secrets.")
    driver.quit()

if __name__ == "__main__":
    run_manual_login()
