#!/usr/bin/env python3
"""
PyCharm Canlı Sunum Başlatıcısı — ADIM 1: HEDEF SUNUCU (VM 3)
PyCharm'dan doğrudan Run'a basarak hedef sunucu servislerini (Port 80 & 8080)
başlatır ve gelen canlı erişim loglarını PyCharm konsolunda gösterir.
"""
import os
import subprocess
import sys

VAGRANT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def wait_if_interactive():
    if sys.stdin and sys.stdin.isatty():
        try:
            input("\nKapatmak için Enter'a basın...")
        except EOFError:
            pass


print("=" * 60, flush=True)
print(" [VM 3: SERVER - 192.168.60.20] Hedef Servisler Başlatılıyor...", flush=True)
print(" - Port 80   : Genel Intranet Servisi", flush=True)
print(" - Port 8080 : Hassas Finans / Veri Tabanı API", flush=True)
print("=" * 60, flush=True)

remote_cmd = (
    "sudo ip route replace 192.168.50.0/24 via 192.168.60.2; "
    "sudo systemctl restart target-services.service; "
    "sudo mkdir -p /vagrant/results; "
    "sudo touch /vagrant/results/server_access_log.jsonl; "
    "echo '[SERVER HAZIR] Canli erisim loglari dinleniyor...'; "
    "tail -n 5 -f /vagrant/results/server_access_log.jsonl"
)

try:
    res = subprocess.run(["vagrant", "ssh", "server", "-c", remote_cmd], cwd=VAGRANT_DIR)
    if res.returncode != 0:
        print(f"\n[HATA] Sunucu bağlantısı sonlandı (kod: {res.returncode}).", flush=True)
        wait_if_interactive()
        sys.exit(res.returncode)
except KeyboardInterrupt:
    print("\n[Bilgi] Sunucu izleme durduruldu (servis arka planda aktif kalır).", flush=True)
    sys.exit(0)
