import gpsoauth
import requests
email = "shameel0505@gmail.com"
app_pwd = "khoyvcfxchxdbdkq"
main_pwd = "sH3698741"
android_id = "9774d56d682e549c"

print("Trying APP Password...")
res = gpsoauth.perform_master_login(email, app_pwd, android_id)
print(res)

print("\nTrying MAIN Password...")
res = gpsoauth.perform_master_login(email, main_pwd, android_id)
print(res)
