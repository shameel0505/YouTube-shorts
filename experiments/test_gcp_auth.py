import os
import asyncio
import requests
from notebooklm.client import NotebookLMClient

def send_telegram_message(message: str):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Telegram credentials missing!")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Failed to send telegram message: {e}")

async def main():
    state_path = "/app/gcp_storage_state.json"
    
    if not os.path.exists(state_path):
        msg = "🔴 GCP Auth Test Failed: gcp_storage_state.json not found in the container."
        print(msg)
        send_telegram_message(msg)
        return

    print("Checking NotebookLM authentication...")
    
    try:
        # Override the HOME dir so it doesn't try to look in ~
        os.environ["HOME"] = "/tmp"
        
        async with NotebookLMClient.from_storage(state_path) as client:
            notebooks = await client.notebooks.list()
            msg = f"🟢 <b>GCP Auth Valid!</b>\nSuccessfully loaded {len(notebooks)} notebooks. The cookie is surviving on Google's IPs!"
            print(msg)
            send_telegram_message(msg)
            
    except Exception as e:
        msg = f"🔴 <b>GCP Auth Expired!</b>\nGoogle killed the session on GCP.\nError: {str(e)}"
        print(msg)
        send_telegram_message(msg)

if __name__ == "__main__":
    asyncio.run(main())
