#!/usr/bin/env python3
"""
PyCharm Canlı Sunum Başlatıcısı — ADIM 3: İSTEMCİ VE SALDIRI SİMÜLASYONU
Sunum sırasında otomatik olarak 4 adımı sırayla çalıştırır:
Normal trafik -> Bağlam değişimi -> Nmap port taraması -> Karantina doğrulaması.
(Ekstra tuşlama gerekmez; adımlar sırayla otomatik akar.)
"""
import json
import os
import subprocess
import sys
import time

VAGRANT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTEXT_FILE = os.path.join(VAGRANT_DIR, "gateway_engine", "context_state.json")


def set_context_state(state_dict):
    with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
        json.dump(state_dict, f, indent=2)


def run_on_client(label, cmd):
    print(f"\n>>> {label}", flush=True)
    res = subprocess.run(["vagrant", "ssh", "client", "-c", cmd], cwd=VAGRANT_DIR)
    if res.returncode != 0:
        print(f"[Uyarı] İstemci komutu kod {res.returncode} ile döndü.", flush=True)


print("=" * 65, flush=True)
print(" [VM 1: CLIENT - 192.168.50.10] Canlı Bağlam & Saldırı Demosu", flush=True)
print(" Not: Adımlar otomatik sırayla çalışır, tuşlama gerekmez.", flush=True)
print("=" * 65, flush=True)

set_context_state({
    "device_posture_risk": 10,
    "off_hours": False,
    "resource_sensitivity": 25,
    "simulated_conn_rate_override": 2,
    "simulated_unique_ports_override": 1,
})
run_on_client(
    "1. Rota Kontrolü ve Normal Trafik (Düşük Risk - Port 80)",
    "sudo ip route replace 192.168.60.0/24 via 192.168.50.2 && "
    "sleep 1 && curl -m 3 -s http://192.168.60.20:80/status || echo '[HATA] Sunucuya ulaşılamadı (Gateway çalışıyor mu?)'",
)

time.sleep(2)
set_context_state({
    "device_posture_risk": 55,
    "off_hours": True,
    "resource_sensitivity": 45,
    "simulated_conn_rate_override": 25,
    "simulated_unique_ports_override": 2,
})
run_on_client(
    "2. Bağlam Değişimi (Mesai Dışı + Zafiyetli Cihaz -> Hız Kısıtlama)",
    "sleep 1.5 && curl -m 3 -s http://192.168.60.20:80/status || echo '[BİLGİ] Hız kısıtlaması veya zaman aşımı'",
)

time.sleep(2)
set_context_state({
    "device_posture_risk": 85,
    "off_hours": True,
    "resource_sensitivity": 85,
    "simulated_conn_rate_override": 70,
    "simulated_unique_ports_override": 18,
})
run_on_client(
    "3. Yanal Hareket / Nmap Port Taraması Başlatılıyor (Kritik Risk -> Karantina)",
    "sleep 1 && nmap -Pn -p 22,80,443,8080 192.168.60.20 || true",
)

time.sleep(2)
run_on_client(
    "4. Karantina Sonrası Tekrar Erişim Denemesi (Paketlerin Engellendiğini Gör)",
    "curl -m 2 -s http://192.168.60.20:80/status || echo '[ENGELLENDİ] Gateway PEP cihazı karantinaya aldı!'",
)

if sys.stdin and sys.stdin.isatty():
    try:
        input("\nDemo tamamlandı. Kapatmak için Enter'a basın...")
    except EOFError:
        pass
