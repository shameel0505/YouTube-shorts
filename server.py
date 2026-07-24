import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess

def init_secrets():
    # Render doesn't easily support editable secret files, so we read JSON from env vars and write them to disk.
    
    # 1. YouTube Client Secret
    yt_secret = os.environ.get("YOUTUBE_CLIENT_SECRET_RAW")
    if yt_secret:
        with open("client_secret.json", "w") as f:
            f.write(yt_secret)
            
    # 2. YouTube Token
    yt_token = os.environ.get("YOUTUBE_TOKEN_RAW")
    if yt_token:
        with open("token.json", "w") as f:
            f.write(yt_token)
            
    # 3. NotebookLM Storage State
    nblm_state = os.environ.get("NOTEBOOKLM_STORAGE_STATE_RAW")
    if nblm_state:
        # Docker runs as root, so home is /root
        profile_dir = "/root/.notebooklm/profiles/default"
        os.makedirs(profile_dir, exist_ok=True)
        with open(os.path.join(profile_dir, "storage_state.json"), "w") as f:
            f.write(nblm_state)
            
    print("✅ Secrets initialized from environment variables.")

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        if self.path in ['/health', '/']:
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
            
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            # Read comprehensive pipeline state
            state_data = {}
            try:
                import json
                state_file = os.path.join(os.path.dirname(__file__), "memory", "pipeline_state.json")
                if os.path.exists(state_file):
                    with open(state_file, "r") as f:
                        state_data = json.load(f)
            except Exception as e:
                state_data = {"error": f"Could not read state: {e}"}
                
            from datetime import datetime, timezone
            utc_now = datetime.now(timezone.utc)
            
            response = {
                "status": "healthy",
                "service": "youtube-shorts-bot",
                "server_time_utc": utc_now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "pipeline_state": state_data
            }
            
            import json
            self.wfile.write(json.dumps(response, indent=4).encode("utf-8"))
            
        elif self.path.startswith('/force-trigger'):
            # Simple security: require the Telegram bot token as a password
            from urllib.parse import urlparse, parse_qs
            query = parse_qs(urlparse(self.path).query)
            token = query.get('token', [''])[0]
            
            if token != os.environ.get("TELEGRAM_BOT_TOKEN", "NO_TOKEN"):
                self.send_response(401)
                self.end_headers()
                self.wfile.write(b"Unauthorized. Please provide the correct ?token=... in the URL.")
                return
                
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Run the dispatcher in the background so the HTTP request completes instantly
            print("🚀 MANUAL TRIGGER RECEIVED! Spawning dispatcher...", flush=True)
            subprocess.Popen(["python", "main.py", "resume-check"])
            
            self.wfile.write(b"<h2>Success!</h2><p>Manual trigger received. The dispatcher is now running in the background.</p><p>Check the Render logs to watch it work!</p>")
            
        elif self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"YouTube Shorts Bot is online.")
        else:
            self.send_response(404)
            self.end_headers()
            
    def log_message(self, format, *args):
        # Suppress log messages for health checks to keep logs clean
        pass

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Starting Render health check server on port {port}...", flush=True)
    server.serve_forever()

def run_bot():
    print("🤖 Starting bot scheduler...", flush=True)
    subprocess.run(["python", "main.py", "schedule"])

if __name__ == "__main__":
    init_secrets()
    
    # Start the HTTP server in a separate thread to satisfy Render and UptimeRobot
    server_thread = threading.Thread(target=run_http_server, daemon=True)
    server_thread.start()
    
    # Run the main bot loop
    run_bot()
