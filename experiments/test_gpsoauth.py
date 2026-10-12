import gpsoauth
import requests
import json
import getpass
import time
from urllib.parse import parse_qs

# Create a random Android ID (16 hex chars)
android_id = "9774d56d682e549c"

def test_gpsoauth():
    print("="*50)
    print("🤖 gpsoauth Web Cookie Extraction Experiment 🤖")
    print("="*50)
    print("IMPORTANT: You MUST use an App Password, NOT your normal Google Password!")
    print("Generate one here: https://myaccount.google.com/apppasswords\n")
    
    email = input("Enter Google Email: ").strip()
    password = getpass.getpass("Enter Google App Password (16 characters): ").strip().replace(" ", "")

    print(f"\n[1] Spoofing Android Device and getting Master Token for {email}...")
    master_response = gpsoauth.perform_master_login(email, password, android_id)
    
    if "Token" not in master_response:
        print("❌ Master Login Failed!")
        print("Response:", master_response)
        print("\nMake sure you are using an APP PASSWORD, not your main password, and that it was typed correctly without spaces.")
        return

    master_token = master_response["Token"]
    print("✅ Master Token acquired successfully!")

    print("\n[2] Exchanging Master Token for OAuth Web Token (uberauth)...")
    # 'uberauth' is the magical undocumented scope that grants permission to generate web cookies
    oauth_response = gpsoauth.perform_oauth(
        email, 
        master_token, 
        android_id, 
        service="uberauth",
        app="com.google.android.gms",
        client_sig="38918a453d07199354f8b19af05ec6562ced5788"
    )

    if "Auth" not in oauth_response:
        print("❌ OAuth Exchange Failed!")
        print("Response:", oauth_response)
        return

    oauth_token = oauth_response["Auth"]
    print("✅ OAuth Token acquired successfully!")

    print("\n[3] Generating Web Cookies from OAuth Token...")
    # Hit the undocumented MergeSession endpoint which takes an uberauth token and spits out valid browser cookies
    merge_url = f"https://accounts.google.com/MergeSession?uberauth={oauth_token}&continue=https://notebooklm.google.com/&source=android"
    
    # We must allow redirects to collect all the cookies
    session = requests.Session()
    # Spoof a standard Chrome browser header so the cookies are optimized for web use
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    })
    
    res = session.get(merge_url, allow_redirects=True)
    
    print("\n✅ Cookies Generated:")
    
    playwright_cookies = []
    has_sid = False
    
    for cookie in session.cookies:
        print(f"  - {cookie.name}: {cookie.value[:10]}... (expires: {cookie.expires})")
        if cookie.name in ["SID", "SSID", "__Secure-1PSID"]:
            has_sid = True
            
        playwright_cookies.append({
            "name": cookie.name,
            "value": cookie.value,
            "domain": cookie.domain,
            "path": cookie.path,
            "expires": cookie.expires if cookie.expires else -1,
            "httpOnly": cookie.has_nonstandard_attr('HttpOnly'),
            "secure": cookie.secure,
            "sameSite": "Lax"
        })

    if not has_sid:
        print("\n⚠️ WARNING: Did not find critical SID cookies. The endpoint might have changed or rejected the token.")
    else:
        print("\n🎉 SUCCESS! Full web session cookies successfully generated via Android spoofing API.")
        
        # Save to test state file
        state = {
            "cookies": playwright_cookies,
            "origins": []
        }
        with open("experiments/test_storage_state.json", "w") as f:
            json.dump(state, f, indent=2)
        print("\n💾 Saved Playwright-compatible cookies to 'experiments/test_storage_state.json'")

if __name__ == "__main__":
    test_gpsoauth()
