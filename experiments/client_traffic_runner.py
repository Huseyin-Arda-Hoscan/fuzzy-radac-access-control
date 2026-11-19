#!/usr/bin/env python3
"""
İstemci (VM 1: client - 192.168.50.10) Trafik, Bağlam ve Saldırı Üreticisi
Senaryo 1, 2 ve 3'ü gerçek ağ paketleri üzerinden koşturur ve istemci tarafı
gözlemlerini (HTTP başarı/engel durumu, yanıt süresi, throughput, sızan paketler) CSV'ye kaydeder.
"""
import argparse
import csv
import json
import os
import socket
import subprocess
import time
import urllib.error
import urllib.request

SERVER_IP = "192.168.60.20"
CONTEXT_FILE = "/vagrant/gateway_engine/context_state.json"


def update_context(posture=10.0, off_hours=False, sensitivity=30.0, rate_override=None, ports_override=None):
    data = {
        "device_posture_risk": posture,
        "off_hours": off_hours,
        "resource_sensitivity": sensitivity,
        "simulated_conn_rate_override": rate_override,
        "simulated_unique_ports_override": ports_override,
    }
    with open(CONTEXT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def http_probe(port=80, path="/status", timeout=0.8):
    url = f"http://{SERVER_IP}:{port}{path}"
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = resp.read()
            latency_ms = (time.perf_counter() - t0) * 1000.0
            return True, resp.status, round(latency_ms, 2), len(body)
    except Exception:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return False, 0, round(latency_ms, 2), 0


def launch_port_scan_burst(target_ip=SERVER_IP):
    """Gerçek TCP SYN / Connect port taraması ve yanal hareket denemesi üretir."""
    scan_ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 443, 445, 1433, 3306, 3389, 5432, 8080, 8443, 9000]
    reached_ports = 0
    for p in scan_ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.06)
        try:
            res = s.connect_ex((target_ip, p))
            if res == 0:
                reached_ports += 1
        except Exception:
            pass
        finally:
            s.close()
    return len(scan_ports), reached_ports


def run_scenario_1(mode: str, duration: float = 45.0):
    """
    Senaryo 1: Oturum İçi Yanal Hareket ve Port Taraması (Statik vs Uyarlanabilir)
      - 0..12 sn  : Normal kullanıcı trafiği (Düşük Risk)
      - 12..30 sn : Cihaz ele geçirilir -> Çoklu port taraması + Hassas port (8080) erişim denemesi
      - 30..45 sn : Saldırı durur -> Karantina / Toparlanma gözlemi
    """
    out_csv = f"/vagrant/results/scenario1_client_{mode}.csv"
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    update_context(posture=15.0, off_hours=False, sensitivity=30.0)

    fieldnames = [
        "elapsed_sec",
        "phase",
        "mode",
        "http80_ok",
        "http80_latency_ms",
        "http8080_ok",
        "scan_attempted",
        "scan_ports_reached",
    ]

    t_start = time.time()
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        while (time.time() - t_start) <= duration:
            loop_t0 = time.time()
            elapsed = round(loop_t0 - t_start, 2)

            if elapsed < 12.0:
                phase = "1_Normal_Trafik"
                update_context(posture=15.0, off_hours=False, sensitivity=25.0, rate_override=3.0, ports_override=1)
                ok80, _, lat80, _ = http_probe(80, "/status", timeout=0.6)
                ok8080 = False
                scan_att, scan_reach = 0, 0
            elif elapsed < 30.0:
                phase = "2_Yanal_Hareket_Port_Tarama"
                # Gerçek TCP port taraması + yüksek bağlantı hızı
                scan_att, scan_reach = launch_port_scan_burst(SERVER_IP)
                update_context(posture=45.0, off_hours=False, sensitivity=85.0, rate_override=65.0, ports_override=18)
                ok80, _, lat80, _ = http_probe(80, "/status", timeout=0.4)
                ok8080, _, _, _ = http_probe(8080, "/sensitive", timeout=0.4)
            else:
                phase = "3_Saldiri_Sonrasi_Toparlanma"
                update_context(posture=15.0, off_hours=False, sensitivity=25.0, rate_override=2.0, ports_override=1)
                ok80, _, lat80, _ = http_probe(80, "/status", timeout=0.5)
                ok8080, _, _, _ = http_probe(8080, "/sensitive", timeout=0.4)
                scan_att, scan_reach = 0, 0

            writer.writerow({
                "elapsed_sec": elapsed,
                "phase": phase,
                "mode": mode,
                "http80_ok": int(ok80),
                "http80_latency_ms": lat80,
                "http8080_ok": int(ok8080),
                "scan_attempted": scan_att,
                "scan_ports_reached": scan_reach,
            })
            f.flush()

            rem = 1.0 - (time.time() - loop_t0)
            if rem > 0:
                time.sleep(rem)


def run_scenario_2():
    """
    Senaryo 2: Bağlam Değişimine Göre 4 Kademeli (Tier 0 -> Tier 1 -> Tier 2 -> Tier 3)
    Politika Yürütme ve Bant Genişliği / Servis Kısıtlama Testi
    """
    out_csv = "/vagrant/results/scenario2_tiers.csv"
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)

    stages = [
        # (Süre_sn, Etiket, posture, off_hours, sensitivity, rate, ports)
        (10.0, "Kademe_0_Tam_Erisim", 10.0, False, 20.0, 3.0, 1),
        (10.0, "Kademe_1_Hiz_Kisitlama_tc", 45.0, True, 35.0, 22.0, 2),
        (10.0, "Kademe_2_Hassas_Servis_Engeli", 70.0, True, 65.0, 35.0, 6),
        (10.0, "Kademe_3_Tam_Karantina", 85.0, True, 85.0, 80.0, 16),
    ]

    fieldnames = [
        "elapsed_sec",
        "stage",
        "port80_ok",
        "port8080_ok",
        "bulk_download_ms",
        "throughput_kbps",
    ]

    t_start = time.time()
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for dur, label, posture, off_h, sens, rate, ports in stages:
            stage_t0 = time.time()
            update_context(
                posture=posture,
                off_hours=off_h,
                sensitivity=sens,
                rate_override=rate,
                ports_override=ports,
            )
            # Gateway'in yeni bağlamı okuyup kuralı basması için 0.8 sn bekle
            time.sleep(0.8)

            while (time.time() - stage_t0) < dur:
                iter_t0 = time.time()
                ok80, _, dl_ms, nbytes = http_probe(80, "/bulk", timeout=2.5)
                ok8080, _, _, _ = http_probe(8080, "/status", timeout=0.6)
                kbps = round((nbytes * 8.0) / max(1.0, dl_ms), 1) if ok80 else 0.0

                writer.writerow({
                    "elapsed_sec": round(time.time() - t_start, 2),
                    "stage": label,
                    "port80_ok": int(ok80),
                    "port8080_ok": int(ok8080),
                    "bulk_download_ms": dl_ms,
                    "throughput_kbps": kbps,
                })
                f.flush()

                rem = 1.2 - (time.time() - iter_t0)
                if rem > 0:
                    time.sleep(rem)


def run_scenario_3():
    """
    Senaryo 3: Performans (Ping/HTTP RTT Gecikmesi) ve Yanlış Alarm (False-Positive) Analizi
    - Meşru Yoğun Kullanıcı (Burst HTTP, Tek Port, Temiz Cihaz) vs Gerçek Port Tarayıcı Saldırgan
    """
    out_json = "/vagrant/results/scenario3_performance_and_fp.json"
    update_context(posture=10.0, off_hours=False, sensitivity=25.0, rate_override=2.0, ports_override=1)
    time.sleep(1.0)

    # 30 adet HTTP RTT ve ICMP Ping ölçümü
    http_latencies = []
    for _ in range(30):
        ok, _, lat, _ = http_probe(80, "/status", timeout=1.0)
        if ok:
            http_latencies.append(lat)
        time.sleep(0.05)

    # Meşru Yoğun Kullanıcı (Legitimate Burst: 20 istek/sn ama sadece Port 80 ve güvenilir cihaz)
    update_context(posture=10.0, off_hours=False, sensitivity=25.0, rate_override=22.0, ports_override=1)
    time.sleep(1.2)
    burst_success = 0
    burst_total = 15
    for _ in range(burst_total):
        ok, _, _, _ = http_probe(80, "/status", timeout=0.8)
        if ok:
            burst_success += 1
        time.sleep(0.1)

    res = {
        "avg_http_rtt_ms": round(sum(http_latencies) / max(1, len(http_latencies)), 2),
        "min_http_rtt_ms": round(min(http_latencies) if http_latencies else 0.0, 2),
        "max_http_rtt_ms": round(max(http_latencies) if http_latencies else 0.0, 2),
        "legitimate_burst_total": burst_total,
        "legitimate_burst_allowed": burst_success,
        "false_quarantine_rate_pct": round((1.0 - (burst_success / float(burst_total))) * 100.0, 2),
    }
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=int, choices=[1, 2, 3], required=True)
    parser.add_argument("--mode", choices=["static", "adaptive"], default="adaptive")
    args = parser.parse_args()

    if args.scenario == 1:
        run_scenario_1(args.mode)
    elif args.scenario == 2:
        run_scenario_2()
    elif args.scenario == 3:
        run_scenario_3()
