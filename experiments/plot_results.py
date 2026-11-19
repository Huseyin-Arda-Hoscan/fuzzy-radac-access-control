#!/usr/bin/env python3
"""
Deney Sonuçlarını Görselleştirme Betiği (Pazartesi Sunumu & Rapor İçin 3 Grafik + Özet Tablo)
"""
import csv
import json
import os
import matplotlib.pyplot as plt
import numpy as np

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def read_csv(filename):
    path = os.path.join(RESULTS_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def plot_scenario_1():
    gw_adapt = read_csv("scenario1_gateway_adaptive.csv")
    cli_static = read_csv("scenario1_client_static.csv")
    cli_adapt = read_csv("scenario1_client_adaptive.csv")
    if not gw_adapt or not cli_static or not cli_adapt:
        print("[UYARI] Senaryo 1 CSV dosyalari eksik.")
        return None

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    t_gw = [float(r["elapsed_sec"]) for r in gw_adapt]
    risk = [float(r["risk_score"]) for r in gw_adapt]
    thresh = [float(r["dynamic_threshold"]) for r in gw_adapt]

    ax1.plot(t_gw, risk, color="#d62728", linewidth=2.5, label="Uyarlanabilir Risk Skoru R(t)")
    ax1.plot(t_gw, thresh, color="#1f77b4", linestyle="--", linewidth=1.8, label="Dinamik Karantina Eşiği")
    ax1.axvspan(12, 30, color="#ffcccc", alpha=0.35, label="Saldırı Fazı (Port Taraması & Yanal Hareket)")
    ax1.set_ylabel("Risk Skoru (0 - 100)", fontsize=11, fontweight="bold")
    ax1.set_title("Senaryo 1: Oturum İçi Yanal Hareket Tespiti ve Dinamik Risk Evrimi", fontsize=12, fontweight="bold")
    ax1.set_ylim(0, 105)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper right")

    t_st = [float(r["elapsed_sec"]) for r in cli_static]
    s_st = np.cumsum([int(r["scan_ports_reached"]) + int(r["http8080_ok"]) for r in cli_static])
    t_ad = [float(r["elapsed_sec"]) for r in cli_adapt]
    s_ad = np.cumsum([int(r["scan_ports_reached"]) + int(r["http8080_ok"]) for r in cli_adapt])

    ax2.plot(t_st, s_st, color="#7f7f7f", linewidth=2.5, linestyle="-.", label="Statik NAC/ACL (Sızan Zararlı Bağlantı)")
    ax2.plot(t_ad, s_ad, color="#2ca02c", linewidth=2.5, label="Uyarlanabilir RAdAC (PEP Karantina Koruması)")
    ax2.axvspan(12, 30, color="#ffcccc", alpha=0.35)
    ax2.set_xlabel("Zaman (Saniye)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Kümülatif Sızan Port/İstek", fontsize=11, fontweight="bold")
    ax2.set_title("Statik vs. Uyarlanabilir Kontrol: Hedef Sunucuya Sızan Başarılı Saldırı Bağlantıları", fontsize=11, fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper left")

    plt.tight_layout()
    out_path = os.path.join(RESULTS_DIR, "grafik1_yanal_hareket_karsilastirma.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[OK] Grafik 1 kaydedildi: {out_path}")

    # Özet istatistikler
    first_quarantine = next((float(r["elapsed_sec"]) for r in gw_adapt if r["tier"] == "TIER_3_QUARANTINE"), None)
    return {
        "static_leaked_total": int(s_st[-1]) if len(s_st) else 0,
        "adaptive_leaked_total": int(s_ad[-1]) if len(s_ad) else 0,
        "quarantine_trigger_sec": first_quarantine,
    }


def plot_scenario_2():
    rows = read_csv("scenario2_tiers.csv")
    gw_rows = read_csv("scenario2_gateway.csv")
    if not rows:
        print("[UYARI] Senaryo 2 CSV dosyasi eksik.")
        return None

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6.5), sharex=True)

    t_cli = [float(r["elapsed_sec"]) for r in rows]
    kbps = [float(r["throughput_kbps"]) for r in rows]

    if gw_rows:
        t_gw = [float(r["elapsed_sec"]) for r in gw_rows]
        risk = [float(r["risk_score"]) for r in gw_rows]
        ax1.plot(t_gw, risk, color="#ff7f0e", linewidth=2.5, label="Bağlam + Davranış Risk Skoru")
        ax1.axhline(30, color="green", linestyle=":", label="Kademe 1 Eşiği (Hız Kısıtlama)")
        ax1.axhline(60, color="orange", linestyle=":", label="Kademe 2 Eşiği (Hassas Port Engeli)")
        ax1.axhline(80, color="red", linestyle=":", label="Kademe 3 Eşiği (Karantina)")
        ax1.set_ylabel("Risk Skoru", fontsize=11, fontweight="bold")
        ax1.set_title("Senaryo 2: Bağlam Değişimine Göre 4 Kademeli Politika Geçişi (Tier 0 → Tier 3)", fontsize=12, fontweight="bold")
        ax1.set_ylim(0, 105)
        ax1.grid(True, linestyle=":", alpha=0.6)
        ax1.legend(loc="upper left", fontsize=9)

    ax2.plot(t_cli, kbps, color="#1f77b4", marker="o", linewidth=2.2, label="İstemci Efektif Bant Genişliği (Kbps)")
    ax2.set_xlabel("Zaman (Saniye)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Throughput (Kbps)", fontsize=11, fontweight="bold")
    ax2.set_title("PEP (tc + iptables) Kademeli Kısıtlamanın Ağ Trafik Hızına Etkisi", fontsize=11, fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper right")

    plt.tight_layout()
    out_path = os.path.join(RESULTS_DIR, "grafik2_kademeli_kisitlama_throughput.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[OK] Grafik 2 kaydedildi: {out_path}")

    # Kademe ortalamaları
    stage_stats = {}
    for r in rows:
        st = r["stage"]
        stage_stats.setdefault(st, []).append(float(r["throughput_kbps"]))
    return {k: round(sum(v) / len(v), 1) for k, v in stage_stats.items()}


def plot_scenario_3():
    gw_st = read_csv("scenario1_gateway_static.csv")
    gw_ad = read_csv("scenario1_gateway_adaptive.csv")
    perf_path = os.path.join(RESULTS_DIR, "scenario3_performance_and_fp.json")
    perf = {}
    if os.path.exists(perf_path):
        with open(perf_path, "r", encoding="utf-8") as f:
            perf = json.load(f)

    if not gw_st or not gw_ad:
        print("[UYARI] Senaryo 3 icin gateway CSV dosyalari eksik.")
        return None

    pdp_st_us = np.mean([float(r["pdp_decision_us"]) for r in gw_st])
    pdp_ad_us = np.mean([float(r["pdp_decision_us"]) for r in gw_ad])
    pep_changes = [float(r["pep_enforce_ms"]) for r in gw_ad if float(r["pep_enforce_ms"]) > 0.5]
    pep_avg_ms = np.mean(pep_changes) if pep_changes else 0.0

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

    # Sol grafik: PDP Karar Süresi (µs)
    labels = ["Statik NAC/ACL", "Uyarlanabilir Fuzzy RAdAC"]
    vals = [pdp_st_us, pdp_ad_us]
    bars1 = ax1.bar(labels, vals, color=["#7f7f7f", "#1f77b4"], width=0.5)
    ax1.set_ylim(0, max(vals) * 1.25)
    ax1.set_ylabel("Ortalama Karar Süresi (Mikrosaniye - µs)", fontweight="bold")
    ax1.set_title("PDP Karar Motoru Hesaplama Maliyeti", fontweight="bold")
    ax1.grid(axis="y", linestyle=":", alpha=0.6)
    for b in bars1:
        ax1.text(b.get_x() + b.get_width() / 2, b.get_height() + max(vals) * 0.03, f"{b.get_height():.1f} µs", ha="center", fontweight="bold")

    # Sağ grafik: Meşru Yoğun Trafik Doğruluğu vs Saldırı Engelleme
    burst_ok = perf.get("legitimate_burst_allowed", 0)
    burst_tot = perf.get("legitimate_burst_total", 15)
    fp_pct = perf.get("false_quarantine_rate_pct", 0.0)
    rtt_ms = perf.get("avg_http_rtt_ms", 0.0)

    metrics_lbl = ["Meşru Yoğun Erişim\nBaşarı Oranı (%)", "Yanlış Karantina\nOranı - FPR (%)"]
    metrics_val = [100.0 - fp_pct, fp_pct]
    bars2 = ax2.bar(metrics_lbl, metrics_val, color=["#2ca02c", "#d62728"], width=0.5)
    ax2.set_ylim(0, 115)
    ax2.set_ylabel("Oran (%)", fontweight="bold")
    ax2.set_title(f"Doğruluk Analizi (Ort. HTTP RTT: {rtt_ms:.2f} ms)", fontweight="bold")
    ax2.grid(axis="y", linestyle=":", alpha=0.6)
    for b in bars2:
        ax2.text(b.get_x() + b.get_width() / 2, b.get_height() + 2, f"%{b.get_height():.1f}", ha="center", fontweight="bold")

    plt.tight_layout()
    out_path = os.path.join(RESULTS_DIR, "grafik3_performans_ve_false_positive.png")
    plt.savefig(out_path, dpi=300)
    plt.close()
    print(f"[OK] Grafik 3 kaydedildi: {out_path}")

    return {
        "pdp_static_avg_us": round(pdp_st_us, 2),
        "pdp_adaptive_avg_us": round(pdp_ad_us, 2),
        "pep_rule_apply_avg_ms": round(pep_avg_ms, 2),
        "avg_http_rtt_ms": rtt_ms,
        "false_quarantine_rate_pct": fp_pct,
        "legitimate_burst_allowed": f"{burst_ok}/{burst_tot}",
    }


if __name__ == "__main__":
    s1 = plot_scenario_1()
    s2 = plot_scenario_2()
    s3 = plot_scenario_3()
    summary = {"scenario_1": s1, "scenario_2_avg_kbps": s2, "scenario_3": s3}
    sum_path = os.path.join(RESULTS_DIR, "experiment_summary.json")
    with open(sum_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print("\n=== DENEY ÖZETİ ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
