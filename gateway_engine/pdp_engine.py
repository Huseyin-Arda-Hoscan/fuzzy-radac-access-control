#!/usr/bin/env python3
"""
Politika Karar Noktası (PDP - Policy Decision Point)
Referanslar:
- [1] NIST SP 800-162 (ABAC) & [2] NIST SP 800-207 (Zero Trust)
- [5] Atlam vd. (2018) - Bulanık Mantık / Risk-Tabanlı Uyarlanabilir Erişim Kontrolü
- [9] Bradatsch vd. (2024) - Skor-Tabanlı Ağ Düzlemi Erişim Kontrolü ve Dinamik Eşik
- [10] Lee vd. (2017) - Durumsal Farkındalık Tabanlı RAdAC
"""
import time


def trapmf(x, a, b, c, d):
    """Yamuk (Trapezoidal) Bulanık Üyelik Fonksiyonu."""
    if x <= a or x >= d:
        return 0.0
    elif b <= x <= c:
        return 1.0
    elif a < x < b:
        return (x - a) / float(b - a)
    else:
        return (d - x) / float(d - c)


class PDPEngine:
    def __init__(self, mode="adaptive"):
        """
        mode:
          - 'static'  : Klasik NAC/ACL (İlk doğrulama sonrası oturum boyu sabit ALLOW)
          - 'adaptive': Bağlam ve Davranış Duyarlı Bulanık/Skor Tabanlı RAdAC Motoru
        """
        self.mode = mode
        self.history_score = 10.0  # Geçmiş risk hafızası (EWMA - güvenin yavaş kazanılıp hızlı kaybedilmesi)

    def evaluate(self, context_features: dict) -> dict:
        """
        Girdi Öznitelikleri (PIP'ten gelen):
          - device_posture_risk : [0..100] (0: Tam yamalı/kurumsal, 50: Eksik yama/BYOD, 85: Zafiyetli/Antivirüs kapalı)
          - off_hours           : bool (Mesai dışı erişim mi?)
          - resource_sensitivity: [0..100] (Hedef servisin kritikliği, örn. Port 80 -> 25, Port 8080 -> 80)
          - conn_rate           : float (Saniyedeki yeni bağlantı / istek sayısı)
          - unique_ports        : int (Son penceredeki farklı hedef port sayısı - port tarama göstergesi)
          - syn_unanswered      : int (Yarı-açık / yanıtsız SYN bağlantı sayısı)
        """
        t_start = time.perf_counter_ns()

        if self.mode == "static":
            # Klasik statik erişim kontrolü: Oturum başında izin verildi, oturum içi değişimlere bakılmaz
            t_end = time.perf_counter_ns()
            return {
                "mode": "static",
                "risk_score": 10.0,
                "dynamic_threshold": 100.0,
                "tier": "TIER_0_ALLOW",
                "action": "ACCEPT",
                "decision_time_us": round((t_end - t_start) / 1000.0, 2),
                "components": {
                    "posture": 10.0,
                    "temporal": 0.0,
                    "rate_anomaly": 0.0,
                    "scan_anomaly": 0.0,
                },
            }

        # --- UYARLANABİLİR (ADAPTIVE) BULANIK + SKOR TABANLI HESAPLAMA ---
        posture_risk = float(context_features.get("device_posture_risk", 10.0))
        off_hours = bool(context_features.get("off_hours", False))
        res_sens = float(context_features.get("resource_sensitivity", 30.0))
        conn_rate = float(context_features.get("conn_rate", 1.0))
        unique_ports = int(context_features.get("unique_ports", 1))
        syn_unanswered = int(context_features.get("syn_unanswered", 0))

        # 1. Zaman ve Kaynak Bağlam Riski
        temporal_risk = 25.0 if off_hours else 5.0 #Mesai dışı risk
        context_subscore = min(100.0, 0.65 * posture_risk + 0.35 * temporal_risk) #cihazın güvenlik durumu + hedef durumu için birleşik risk puanı

        # 2. Trafik Hızı (Conn/s) Bulanık Üyelik Değerlendirmesi
        mu_rate_low = trapmf(conn_rate, -1, 0, 8, 15)
        mu_rate_med = trapmf(conn_rate, 10, 18, 35, 50)
        mu_rate_high = trapmf(conn_rate, 40, 60, 1000, 2000)
        rate_anomaly_score = (mu_rate_low * 5.0 + mu_rate_med * 55.0 + mu_rate_high * 95.0) / max(
            0.001, (mu_rate_low + mu_rate_med + mu_rate_high) #ağırlıklı ortalama hesabında paydaya 0 gelince bölünmesi sıkıntı olduğu için eklenen güvenlik katsayısı
        )

        # 3. Yanal Hareket / Port Tarama Bulanık Üyelik Değerlendirmesi
        effective_scan_metric = unique_ports + (syn_unanswered * 0.5)
        mu_scan_normal = trapmf(effective_scan_metric, -1, 0, 2, 4)
        mu_scan_suspicious = trapmf(effective_scan_metric, 3, 5, 8, 12)
        mu_scan_attack = trapmf(effective_scan_metric, 9, 14, 1000, 2000)
        scan_anomaly_score = (
            mu_scan_normal * 5.0 + mu_scan_suspicious * 65.0 + mu_scan_attack * 98.0
        ) / max(0.001, (mu_scan_normal + mu_scan_suspicious + mu_scan_attack))

        # 4. Birleşik Anlık Risk Skoru (Maksimum baskın tehdit + bağlamsal ağırlık)
        behavioral_peak = max(rate_anomaly_score, scan_anomaly_score)
        instant_risk = min(
            100.0,
            0.30 * context_subscore + 0.70 * behavioral_peak
            if behavioral_peak > 40.0
            else 0.60 * context_subscore + 0.40 * behavioral_peak,
        ) #0 ila 100

        # 5. Asimetrik Güven/Risk Hafızası (Risk hızlı yükselir, tehdit bitince kademeli düşer)
        if instant_risk >= self.history_score:
            final_risk = 0.80 * instant_risk + 0.20 * self.history_score
        else:
            final_risk = 0.35 * instant_risk + 0.65 * self.history_score
        self.history_score = final_risk #risk skoru yükselirken hızlı tepki verir ani düşüşlerde daha yavaş tepki verir kalıcı tehtidlere karşı etkin bir koruma

        # 6. Bradatsch vd. [9] yaklaşımı: Kaynak hassasiyetine göre dinamik eşik ayarlama
        # Kaynak çok hassassa (örn. 8080 finans API), karantina ve kısıtlama eşikleri aşağı çekilir
        sensitivity_shift = max(0.0, (res_sens - 30.0) * 0.15)
        th_tier1 = max(20.0, 30.0 - sensitivity_shift)
        th_tier2 = max(45.0, 60.0 - sensitivity_shift)
        th_tier3 = max(65.0, 80.0 - sensitivity_shift)

        if final_risk <= th_tier1:
            tier = "TIER_0_ALLOW"
            action = "ACCEPT"
        elif final_risk <= th_tier2:
            tier = "TIER_1_RATELIMIT"
            action = "RATE_LIMIT_256KBIT"
        elif final_risk <= th_tier3:
            tier = "TIER_2_RESTRICT"
            action = "BLOCK_SENSITIVE_PORTS"
        else:
            tier = "TIER_3_QUARANTINE"
            action = "DROP_QUARANTINE"

        t_end = time.perf_counter_ns()
        return {
            "mode": "adaptive",
            "risk_score": round(final_risk, 2),
            "instant_risk": round(instant_risk, 2),
            "dynamic_threshold": round(th_tier3, 2),
            "tier": tier,
            "action": action,
            "decision_time_us": round((t_end - t_start) / 1000.0, 2),
            "components": {
                "posture": round(posture_risk, 1),
                "temporal": round(temporal_risk, 1),
                "rate_anomaly": round(rate_anomaly_score, 1),
                "scan_anomaly": round(scan_anomaly_score, 1),
            },
        }
