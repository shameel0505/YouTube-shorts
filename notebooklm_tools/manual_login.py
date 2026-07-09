import os
import time
import json
from urllib.parse import urlparse
from pathlib import Path
from dotenv import load_dotenv
import undetected_chromedriver as uc

load_dotenv()

def create_proxy_extension(proxy_url: str, dest_path: str):
    parsed = urlparse(proxy_url)
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {
            "scripts": ["background.js"]
        },
        "minimum_chrome_version":"22.0.0"
    }
    """
    background_js = f"""
    var config = {{
            mode: "fixed_servers",
            rules: {{
            singleProxy: {{
                scheme: "http",
                host: "{parsed.hostname}",
                port: parseInt({parsed.port})
            }},
            bypassList: ["localhost"]
            }}
        }};
    chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});
    function callbackFn(details) {{
        return {{
            authCredentials: {{
                username: "{parsed.username}",
                password: "{parsed.password}"
            }}
        }};
    }}
    chrome.webRequest.onAuthRequired.addListener(
                callbackFn,
                {{urls: ["<all_urls>"]}},
                ['blocking']
    );
    """
    os.makedirs(dest_path, exist_ok=True)
    with open(os.path.join(dest_path, "manifest.json"), "w") as f:
        f.write(manifest_json)
    with open(os.path.join(dest_path, "background.js"), "w") as f:
        f.write(background_js)
    return dest_path

def run_manual_login():
    options = uc.ChromeOptions()
    
    proxy_url = os.environ.get("WEBSHARE_PROXY")
    if proxy_url:
        print(f"🛡️ Configuring Chrome to tunnel through Webshare Proxy...")
        proxy_ext_dir = os.path.join(os.getcwd(), "proxy_auth_extension")
        create_proxy_extension(proxy_url, proxy_ext_dir)
        options.add_argument(f"--load-extension={proxy_ext_dir}")

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
