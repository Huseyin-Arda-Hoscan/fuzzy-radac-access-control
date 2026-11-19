#!/usr/bin/env python3
"""
Politika Bilgi Noktası (PIP - Policy Information Point)
Gateway üzerinden geçen (192.168.50.10 -> 192.168.60.20) gerçek zamanlı bağlantı
ve paket özniteliklerini (/proc/net/nf_conntrack + arayüz sayaçları + context_state.json) toplar.
"""
import json
import os
import subprocess
import time

CONTEXT_FILE = "/vagrant/gateway_engine/context_state.json"


class PIPCollector:
    def __init__(self, client_ip="192.168.50.10", server_ip="192.168.60.20"):
        self.client_ip = client_ip
        self.server_ip = server_ip
        self.last_pkt_count = self._get_forward_packets()
        self.last_time = time.time()

    def _get_forward_packets(self) -> int:
        try:
            out = subprocess.check_output(["iptables", "-L", "FORWARD", "-v", "-n", "-x"], text=True) #forward zinciri (log hatasız hesaplama için)
            total = 0
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[0].isdigit():
                    total += int(parts[0])
            return total
        except Exception:
            return 0

    def _inspect_conntrack(self):
        unique_ports = set()
        syn_sent_count = 0
        total_entries = 0
        sensitive_targeted = False

        # /proc/net/nf_conntrack veya conntrack -L üzerinden aktif akışları oku
        lines = []
        if os.path.exists("/proc/net/nf_conntrack"):
            try:
                with open("/proc/net/nf_conntrack", "r", encoding="utf-8") as f:
                    lines = f.readlines()
            except Exception:
                lines = []
        if not lines:
            try:
                out = subprocess.check_output(["conntrack", "-L"], stderr=subprocess.DEVNULL, text=True)
                lines = out.splitlines()
            except Exception:
                lines = []

        for line in lines:
            if f"src={self.client_ip}" in line and f"dst={self.server_ip}" in line:
                total_entries += 1
                if "SYN_SENT" in line or "TIME_WAIT" in line or "CLOSE" in line:
                    syn_sent_count += 1
                for token in line.split():
                    if token.startswith("dport="):
                        try:
                            p = int(token.split("=")[1])
                            unique_ports.add(p)
                            if p in (8080, 22, 9000):
                                sensitive_targeted = True
                        except ValueError:
                            pass
                        break

        return len(unique_ports), syn_sent_count, total_entries, sensitive_targeted

    def collect(self) -> dict:
        now = time.time()
        dt = max(0.1, now - self.last_time)
        curr_pkts = self._get_forward_packets()
        pkt_rate = max(0.0, (curr_pkts - self.last_pkt_count) / dt)
        self.last_pkt_count = curr_pkts
        self.last_time = now

        unique_ports, syn_unanswered, total_conns, sensitive_targeted = self._inspect_conntrack()

        # Bağlam dosyasını oku (cihaz duruşu, mesai saati vb.)
        ctx = {
            "device_posture_risk": 10.0,
            "off_hours": False,
            "resource_sensitivity": 30.0,
            "simulated_conn_rate_override": None,
            "simulated_unique_ports_override": None,
        }
        if os.path.exists(CONTEXT_FILE):
            try:
                with open(CONTEXT_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    ctx.update(loaded)
            except Exception:
                pass

        if sensitive_targeted and ctx["resource_sensitivity"] < 75.0:
            ctx["resource_sensitivity"] = 80.0

        conn_rate = (
            float(ctx["simulated_conn_rate_override"])
            if ctx.get("simulated_conn_rate_override") is not None
            else max(pkt_rate / 4.0, float(total_conns))
        )
        u_ports = (
            int(ctx["simulated_unique_ports_override"])
            if ctx.get("simulated_unique_ports_override") is not None
            else max(1, unique_ports)
        )

        return {
            "timestamp": now,
            "device_posture_risk": float(ctx["device_posture_risk"]),
            "off_hours": bool(ctx["off_hours"]),
            "resource_sensitivity": float(ctx["resource_sensitivity"]),
            "conn_rate": round(conn_rate, 2),
            "unique_ports": u_ports,
            "syn_unanswered": syn_unanswered,
            "raw_pkt_rate": round(pkt_rate, 2),
        }
