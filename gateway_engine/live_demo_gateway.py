#!/usr/bin/env python3
"""
Canlı PyCharm Demo Gateway Döngüsü (VM 2: GATEWAY).
PIP -> PDP (Adaptive Fuzzy + Dinamik Eşik) -> PEP zincirini çalıştırır
ve her döngüde Risk Skoru ile PEP aksiyonunu terminale basar.
"""
import signal
import sys
import time

sys.path.insert(0, "/vagrant/gateway_engine")
from pip_collector import PIPCollector
from pdp_engine import PDPEngine
from pep_enforcer import PEPEnforcer


def main():
    pip = PIPCollector()
    pdp = PDPEngine(mode="adaptive")
    pep = PEPEnforcer()

    # Önceki demodan kalan kural varsa temizle
    pep.cleanup()

    def handle_exit(signum, frame):
        pep.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_exit)
    signal.signal(signal.SIGINT, handle_exit)

    print("Süre(s) | BağlantıHızı | PortSayısı | RiskSkoru | Eşik | Kademe (PEP Aksiyonu)", flush=True)
    print("-" * 78, flush=True)
    t0 = time.time()

    try:
        while True:
            f = pip.collect()
            d = pdp.evaluate(f)
            pep.enforce(d["tier"])
            print(
                f"{time.time() - t0:6.1f}s | {f['conn_rate']:11.1f} | "
                f"{f['unique_ports']:10d} | {d['risk_score']:9.2f} | "
                f"{d['dynamic_threshold']:4.0f} | {d['tier']} ({d['action']})",
                flush=True,
            )
            time.sleep(0.8)
    except KeyboardInterrupt:
        pass
    finally:
        pep.cleanup()


if __name__ == "__main__":
    main()
