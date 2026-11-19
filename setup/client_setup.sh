#!/usr/bin/env bash
set -e

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-pip nmap hping3 net-tools curl iperf3

# Hedef sunucu alt ağına (192.168.60.0/24) giden trafiği Gateway (192.168.50.2) üzerinden yönlendir
ip route replace 192.168.60.0/24 via 192.168.50.2

echo "[OK] Client kurulumu ve rotasi tamamlandi."
