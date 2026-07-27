with open("server.py", "r") as f:
    code = f.read()

new_class = '''class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_HEAD(self):
        if self.path in ['/health', '/']:
            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
            
    def do_GET(self):'''

new_code = code.replace('class HealthCheckHandler(BaseHTTPRequestHandler):\n    def do_GET(self):', new_class)

with open("server.py", "w") as f:
    f.write(new_code)
print("Patched do_HEAD!")
