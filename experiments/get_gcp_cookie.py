import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv
import undetected_chromedriver as uc

load_dotenv()

def run_manual_login():
    options = uc.ChromeOptions()
    
    # Use a completely separate profile folder for the GCP test
    # This guarantees Google treats it as a brand new, independent session!
    options.add_argument("--incognito")

    driver = uc.Chrome(options=options, version_main=149)

    print("🌍 Navigating to NotebookLM...")
    driver.get("https://notebooklm.google.com/")
    
    print("\n========================================================")
    print("🛑 PLEASE LOG IN MANUALLY IN THE OPEN BROWSER WINDOW! 🛑")
    print("========================================================\n")
    
    timeout = 180
    start_time = time.time()
    while time.time() - start_time < timeout:
        if "accounts.google.com" not in driver.current_url and "notebooklm.google.com" in driver.current_url:
            break
        time.sleep(2)
        print("Waiting for you to log in...")
    
    print("\n✅ Login detected! Saving cookies...")
    time.sleep(5)
    
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

    state_path = Path(os.getcwd()) / "experiments" / "gcp_storage_state.json"
    
    with open(state_path, "w") as f:
        json.dump(state, f, indent=2)

    print(f"🎉 Successfully saved isolated GCP cookies to: {state_path}")
    driver.quit()

if __name__ == "__main__":
    run_manual_login()
