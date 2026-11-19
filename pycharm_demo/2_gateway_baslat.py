#!/usr/bin/env python3
"""
PyCharm Canlı Sunum Başlatıcısı — ADIM 2: GATEWAY (PIP + PDP + PEP)
PyCharm'dan Run'a bastığınızda Gateway üzerindeki uyarlanabilir karar motorunu
canlı başlatır ve her 0.8 sn'deki Risk Skoru + PEP Aksiyonunu ekrana basar.
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


print("=" * 70, flush=True)
print(" [VM 2: GATEWAY - 192.168.50.2 / 60.2] PIP -> PDP -> PEP Başlatılıyor", flush=True)
print(" Mod: Uyarlanabilir (Adaptive Fuzzy + Dinamik Eşik RAdAC)", flush=True)
print("=" * 70, flush=True)

remote_cmd = (
    "sudo sysctl -w net.ipv4.ip_forward=1 >/dev/null && "
    "sudo python3 -u /vagrant/gateway_engine/live_demo_gateway.py"
)

try:
    res = subprocess.run(["vagrant", "ssh", "gateway", "-c", remote_cmd], cwd=VAGRANT_DIR)
    if res.returncode != 0:
        print(f"\n[HATA] Gateway bağlantısı sonlandı (kod: {res.returncode}).", flush=True)
        wait_if_interactive()
        sys.exit(res.returncode)
except KeyboardInterrupt:
    print("\n[Bilgi] Gateway karar motoru durduruldu.", flush=True)
    sys.exit(0)
