import httpx
from notebooklm.auth import save_cookies_to_storage
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

cookies = httpx.Cookies()
cookies.set("__Secure-1PSID", os.environ.get("GOOGLE_SECURE_1PSID"), domain=".google.com")
cookies.set("__Secure-3PSID", os.environ.get("GOOGLE_SECURE_3PSID"), domain=".google.com")
cookies.set("__Secure-1PAPISID", "yUTNndmZRqHw5Orp/AlGGWyhNgOgFYMKjo", domain=".google.com")
cookies.set("__Secure-3PAPISID", "yUTNndmZRqHw5Orp/AlGGWyhNgOgFYMKjo", domain=".google.com")
cookies.set("__Secure-1PSIDCC", "AKEyXzW3TzNhFCLt0szNzGj5IqfzMLKbEnK3baTHRRPufmvzrvJO02FPJCaTDhOhrm54T0HT", domain=".google.com")

path = Path("/Users/shameel/.notebooklm/profiles/default/storage_state.json")
path.parent.mkdir(parents=True, exist_ok=True)

res = save_cookies_to_storage(cookies, path, return_result=True)
print(f"Cookies injected successfully! Result: {res}")
