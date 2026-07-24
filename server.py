import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import subprocess

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot is alive and running! Health check passed.")
        
    def log_message(self, format, *args):
        # Suppress log messages for health checks to keep logs clean
        pass

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    print(f"✅ Starting Render health check server on port {port}...")
    server.serve_forever()

def run_bot():
    print("🤖 Starting bot scheduler...")
    subprocess.run(["python", "main.py", "schedule"])

if __name__ == "__main__":
    # Start the HTTP server in a separate thread to satisfy Render and UptimeRobot
    server_thread = threading.Thread(target=run_http_server, daemon=True)
    server_thread.start()
    
    # Run the main bot loop
    run_bot()
