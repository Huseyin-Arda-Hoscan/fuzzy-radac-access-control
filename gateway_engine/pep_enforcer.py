#!/usr/bin/env python3
"""
Politika Yürütme Noktası (PEP - Policy Enforcement Point)
PDP'den çıkan kademeli kararı (TIER_0 .. TIER_3) Linux ağ katmanında
iptables ve tc (Traffic Control) kuralları olarak gerçek zamanlı uygular.
"""
import subprocess
import time


class PEPEnforcer:
    def __init__(self, client_ip="192.168.50.10", server_ip="192.168.60.20"):
        self.client_ip = client_ip
        self.server_ip = server_ip
        self.current_tier = None #son uygulanan hesaplama sonucu -sistem yorulmasın diye
        self.client_iface = self._detect_iface_for_subnet("192.168.50.")
        self.server_iface = self._detect_iface_for_subnet("192.168.60.")
        self._init_chains()

    def _detect_iface_for_subnet(self, prefix="192.168.60.") -> str:
        try:
            out = subprocess.check_output(["ip", "-o", "-4", "addr", "show"], text=True)
            for line in out.splitlines():
                if prefix in line:
                    return line.split()[1]
        except Exception:
            pass
        return "eth2"

    def _run(self, cmd: list):
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

    def _init_chains(self):
        # Özel PEP zincirini oluştur ve FORWARD zincirinin başına bağla
        self._run(["iptables", "-N", "PEP_ENFORCE"])
        self._run(["iptables", "-F", "PEP_ENFORCE"])
        # Tekrarlı eklemeyi önlemek için önce varsa sil, sonra başa ekle
        self._run(["iptables", "-D", "FORWARD", "-j", "PEP_ENFORCE"])
        self._run(["iptables", "-I", "FORWARD", "1", "-j", "PEP_ENFORCE"])
        self._clear_tc()

    def _clear_tc(self):
        for iface in (self.client_iface, self.server_iface):
            if iface:
                self._run(["tc", "qdisc", "del", "dev", iface, "root"])

    def _apply_tc_rate(self, rate: str, burst: str):
        # Hem istemciye dönen yanıt (download -> client_iface) hem sunucuya giden trafik (upload -> server_iface) kısıtlanır
        for iface in (self.client_iface, self.server_iface):
            if iface:
                self._run([
                    "tc", "qdisc", "add", "dev", iface, "root",
                    "tbf", "rate", rate, "burst", burst, "latency", "50ms"
                ])

    def enforce(self, tier: str) -> float:
        """
        Kararı uygular ve uygulama gecikmesini (ms) döndürür.
        Eğer tier değişmemişse mevcut kuralı korur.
        """
        t0 = time.perf_counter_ns()
        if tier == self.current_tier:
            t1 = time.perf_counter_ns()
            return round((t1 - t0) / 1_000_000.0, 3)

        # Önce PEP zincirini ve tc kısıtlamasını temizle
        self._run(["iptables", "-F", "PEP_ENFORCE"])
        self._clear_tc()

        if tier == "TIER_0_ALLOW":
            # Tam erişim (paket sayacı için ACCEPT kuralı)
            self._run(["iptables", "-A", "PEP_ENFORCE", "-s", self.client_ip, "-d", self.server_ip, "-j", "ACCEPT"])

        elif tier == "TIER_1_RATELIMIT":
            # Orta risk: Bant genişliğini 256kbit ile sınırla (tc TBF)
            self._apply_tc_rate("256kbit", "16kbit")
            self._run([
                "iptables", "-A", "PEP_ENFORCE", "-s", self.client_ip, "-d", self.server_ip,
                "-m", "limit", "--limit", "15/sec", "--limit-burst", "20", "-j", "ACCEPT"
            ])
            self._run(["iptables", "-A", "PEP_ENFORCE", "-s", self.client_ip, "-d", self.server_ip, "-j", "DROP"])

        elif tier == "TIER_2_RESTRICT":
            # Yüksek risk: Hassas portları (8080, 22, 9000) tamamen kapat, sadece Port 80'e düşük hızda izin ver
            self._run([
                "iptables", "-A", "PEP_ENFORCE", "-s", self.client_ip, "-d", self.server_ip,
                "-p", "tcp", "-m", "multiport", "--dports", "8080,22,9000", "-j", "REJECT"
            ])
            self._apply_tc_rate("128kbit", "8kbit")
            self._run([
                "iptables", "-A", "PEP_ENFORCE", "-s", self.client_ip, "-d", self.server_ip,
                "-p", "tcp", "--dport", "80", "-m", "limit", "--limit", "5/sec", "-j", "ACCEPT"
            ])
            self._run(["iptables", "-A", "PEP_ENFORCE", "-s", self.client_ip, "-d", self.server_ip, "-j", "DROP"])

        elif tier == "TIER_3_QUARANTINE":
            # Kritik risk: Tam karantina (tüm paketleri anında DROP et)
            self._run(["iptables", "-A", "PEP_ENFORCE", "-s", self.client_ip, "-d", self.server_ip, "-j", "DROP"])

        self.current_tier = tier
        t1 = time.perf_counter_ns()
        return round((t1 - t0) / 1_000_000.0, 3)

    def cleanup(self):
        self._run(["iptables", "-F", "PEP_ENFORCE"])
        self._clear_tc()
        self.current_tier = None
