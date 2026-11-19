#!/usr/bin/env python3
"""
Hedef Kurumsal Sunucu (VM 3: server - 192.168.60.20)
- Port 80   : Genel Kurumsal Intranet Servisi (Düşük/Orta Hassasiyet)
- Port 8080 : Hassas Finans / Veri Tabanı API Servisi (Yüksek Hassasiyet)
Tüm gelen bağlantıları ve HTTP isteklerini zaman damgalı olarak loglar.
"""
import http.server
import json
import os
import socketserver
import threading
import time

LOG_DIR = "/vagrant/results"
os.makedirs(LOG_DIR, exist_ok=True)
ACCESS_LOG = os.path.join(LOG_DIR, "server_access_log.jsonl")
PAYLOAD_64KB = "A" * 65536  # Bant genişliği / throughput testi için 64 KB veri


def log_event(port, client_ip, path, status):
    entry = {
        "timestamp": time.time(),
        "port": port,
        "client_ip": client_ip,
        "path": path,
        "status": status,
    }
    try:
        with open(ACCESS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def make_handler(service_name, port_num):
    class CustomHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            client_ip = self.client_address[0]
            log_event(port_num, client_ip, self.path, 200)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if self.path.startswith("/bulk"):
                body = json.dumps({"service": service_name, "port": port_num, "data": PAYLOAD_64KB})
            else:
                body = json.dumps({
                    "service": service_name,
                    "port": port_num,
                    "status": "OK",
                    "timestamp": time.time(),
                })
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, format, *args):
            # Konsol kirliliğini önle
            return

    return CustomHandler


def run_port(port, name):
    server = ThreadedHTTPServer(("0.0.0.0", port), make_handler(name, port))
    server.serve_forever()


if __name__ == "__main__":
    t1 = threading.Thread(target=run_port, args=(80, "Intranet_Public_Portal"), daemon=True)
    t2 = threading.Thread(target=run_port, args=(8080, "Sensitive_Finance_DB_API"), daemon=True)
    t1.start()
    t2.start()
    print("[SERVER] Port 80 (Intranet) ve Port 8080 (Hassas API) aktif.")
    while True:
        time.sleep(3600)
