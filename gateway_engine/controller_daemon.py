#!/usr/bin/env python3
"""
Gateway Üzerinde Çalışan Ana Kontrol Döngüsü (PIP -> PDP -> PEP)
Her 0.5 saniyede bir telemetri + bağlam verisini okur, risk skorunu hesaplar,
ağ katmanı kuralını (iptables + tc) uygular ve CSV loguna kaydeder.
"""
import argparse #Komut satırından parametre almanı sağlar (kontrol döngüsün ne sıklıkla olsun gb )
import csv
import os
import signal #Düzgün çıkış ve sistem yönetimi
import sys #aynı şekilde
import time

from pdp_engine import PDPEngine #(projenin kendi modüllerinden alınan yapılar)
from pep_enforcer import PEPEnforcer
from pip_collector import PIPCollector

RUNNING = True


def handle_sig(signum, frame): #Klavyeden ctrl c yapınca  çöküyor
    global RUNNING
    RUNNING = False


signal.signal(signal.SIGINT, handle_sig) # program durunca hata veriyor diye yazdım bunları
signal.signal(signal.SIGTERM, handle_sig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["static", "adaptive"], default="adaptive")
    parser.add_argument("--interval", type=float, default=0.5) #kontrol döngüsü adımları kaç saniyede bir tekrarlanıyor önce 1 yaptım ama örnekleme nmap taramalarını kaçırdı o yüzden 0.5 e çektim hocam.
    parser.add_argument("--duration", type=float, default=60.0)
    parser.add_argument("--output", type=str, default="/vagrant/results/gateway_metrics.csv")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True) #hata oluşturn başta diye yazdım.

    pip = PIPCollector() #veri topla
    pdp = PDPEngine(mode=args.mode) #analiz yap
    pep = PEPEnforcer() #çıktı ver

    fieldnames = [
        "elapsed_sec",
        "timestamp",
        "mode",
        "device_posture_risk",
        "off_hours",
        "resource_sensitivity",
        "conn_rate",
        "unique_ports",
        "raw_pkt_rate",
        "risk_score",
        "dynamic_threshold",
        "tier",
        "action",
        "pdp_decision_us",
        "pep_enforce_ms",
    ]

    t_start = time.time()
    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        while RUNNING and (time.time() - t_start) <= args.duration:
            loop_t0 = time.time()
            features = pip.collect()
            decision = pdp.evaluate(features)
            enforce_ms = pep.enforce(decision["tier"])

            row = {
                "elapsed_sec": round(loop_t0 - t_start, 2),
                "timestamp": round(loop_t0, 3),
                "mode": args.mode,
                "device_posture_risk": features["device_posture_risk"],
                "off_hours": int(features["off_hours"]),
                "resource_sensitivity": features["resource_sensitivity"],
                "conn_rate": features["conn_rate"],
                "unique_ports": features["unique_ports"],
                "raw_pkt_rate": features["raw_pkt_rate"],
                "risk_score": decision["risk_score"],
                "dynamic_threshold": decision["dynamic_threshold"],
                "tier": decision["tier"],
                "action": decision["action"],
                "pdp_decision_us": decision["decision_time_us"],
                "pep_enforce_ms": enforce_ms,
            }
            writer.writerow(row)
            f.flush()

            sleep_rem = args.interval - (time.time() - loop_t0)
            if sleep_rem > 0:
                time.sleep(sleep_rem)

    pep.cleanup()


if __name__ == "__main__":
    main()
