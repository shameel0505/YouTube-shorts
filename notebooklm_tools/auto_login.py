import os
import time
import json
import zipfile
from urllib.parse import urlparse
from pathlib import Path
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyotp

load_dotenv()

def run_login():
    email = os.environ.get("GOOGLE_EMAIL")
    password = os.environ.get("GOOGLE_PASSWORD")
    totp_secret = os.environ.get("GOOGLE_TOTP_SECRET")

    if not email or not password:
        print("❌ Error: GOOGLE_EMAIL or GOOGLE_PASSWORD not set in environment.")
        return False

    # Launch undetected-chromedriver
    options = uc.ChromeOptions()
    # options.add_argument('--headless') # Keep headed so we don't trigger headless blocks
    
    # Disable macOS Keychain to prevent the "iCloud Keychain" popup from blocking automation
    options.add_argument('--password-store=basic')
    options.add_argument('--use-mock-keychain')
    # Completely disable WebAuthn so Google doesn't even try to ask for a passkey or phone prompt!
    options.add_argument('--disable-features=WebAuthentication')

    # We use a custom user data dir so cookies persist naturally in selenium too
    user_data_dir = Path.home() / ".notebooklm" / "chrome_profile"
    
    # We specify version_main=149 because your local Chrome is version 149, preventing driver mismatch errors.
    driver = uc.Chrome(options=options, version_main=149)

    try:
        print(f"🌍 Navigating to StackOverflow to backdoor Google Login for {email}...")
        # Going to StackOverflow's login page first, because Google's anti-bot is much weaker for 3rd party OAuth!
        driver.get("https://stackoverflow.com/users/login")
        wait = WebDriverWait(driver, 15)

        # Click "Log in with Google"
        try:
            google_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, '[data-provider="google"]')))
            google_btn.click()
            print("✅ Clicked 'Log in with Google'")
        except Exception as e:
            print("❌ Failed to find StackOverflow Google button.")
            driver.save_screenshot("debug_so_button.png")
            raise e

        # Now we are on the Google OAuth screen, which is much less strictly monitored
        time.sleep(3)

        # 1. Email
        try:
            email_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"], input#identifierId')))
            email_field.send_keys(email)
            driver.find_element(By.ID, "identifierNext").click()
            print("✅ Email submitted.")
        except Exception as e:
            print("❌ Failed to find email field on OAuth screen.")
            driver.save_screenshot("debug_login_email.png")

        time.sleep(5)

        # 2. Password (and bypassing Passkey/Phone prompts)
        try:
            # Check if Google is asking to use a passkey or phone prompt instead of showing the password field
            time.sleep(3)
            try:
                try_another_way = driver.find_elements(By.XPATH, "//*[contains(text(), 'Try another way')]")
                if try_another_way:
                    print("⚠️ Passkey/Phone prompt detected. Clicking 'Try another way'...")
                    try_another_way[0].click()
                    time.sleep(2)
                    enter_password = driver.find_elements(By.XPATH, "//*[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'password')]")
                    if enter_password:
                        # Click the deepest element that contains the word password
                        driver.execute_script("arguments[0].click();", enter_password[-1])
                        time.sleep(2)
                    else:
                        print("❌ Could not find the 'password' option in the list. Available options:")
                        # Print all text in the dialog to see what options Google is actually offering
                        dialog_items = driver.find_elements(By.XPATH, "//div[@role='button'] | //li | //div[contains(@class, 'vxx8jf')]")
                        for item in dialog_items:
                            if item.text.strip():
                                print(f"  - {item.text.strip()}")
            except Exception:
                pass

            password_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="password"], input[name="Passwd"]')))
            password_field.send_keys(password)
            driver.find_element(By.ID, "passwordNext").click()
            print("✅ Password submitted.")
        except Exception as e:
            print("❌ Failed to find password field. Google blocked login.")
            driver.save_screenshot("debug_login_password.png")
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("📄 Saved page source to debug_page.html")
            raise e

        time.sleep(6)

        # 3. 2FA Check
        if "challenge" in driver.current_url or "signin/v2" in driver.current_url:
            print("⚠️ Challenge detected (2FA/Recovery).")
            try:
                # Look for Authenticator option
                auth_options = driver.find_elements(By.XPATH, "//*[contains(text(), 'Get a verification code from the Google Authenticator app')]")
                if auth_options:
                    auth_options[0].click()
                    time.sleep(3)

                totp_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="tel"]')))
                if totp_secret:
                    print("🔐 Generating TOTP code...")
                    totp = pyotp.TOTP(totp_secret)
                    code = totp.now()
                    totp_input.send_keys(code)
                    
                    next_btns = driver.find_elements(By.XPATH, "//button//*[contains(text(), 'Next')] | //button[@id='totpNext']")
                    if next_btns:
                        driver.execute_script("arguments[0].click();", next_btns[0])
                    print(f"✅ Submitted 2FA Code: {code}")
                    time.sleep(6)
                else:
                    print("❌ 2FA required but GOOGLE_TOTP_SECRET not provided!")
                    return False
            except Exception as e:
                print("❌ Could not handle the challenge automatically.")
                driver.save_screenshot("debug_login_challenge_error.png")

        # 4. Save state for Playwright format
        print("🧠 Navigating to NotebookLM...")
        driver.get("https://notebooklm.google.com/")
        time.sleep(8) # let cookies settle

        if "accounts.google.com" in driver.current_url:
             print("❌ Login failed. Still trapped on login page.")
             driver.save_screenshot("debug_login_failed.png")
             return False
             
        # Extract cookies from Selenium and save in Playwright format
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

        # Save to the exact path Playwright expects later
        state_path = Path.home() / ".notebooklm" / "profiles" / "default" / "storage_state.json"
        state_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2)

        print(f"🎉 Successfully captured Google cookies and saved to {state_path}")
        return True

    finally:
        driver.quit()

if __name__ == "__main__":
    run_login()
