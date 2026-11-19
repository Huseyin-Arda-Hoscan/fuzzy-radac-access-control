#!/usr/bin/env bash
set -e

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-pip iptables iproute2 conntrack net-tools curl iperf3 tcpdump

# IP yönlendirmeyi (Forwarding) kalıcı ve anlık olarak aç
sysctl -w net.ipv4.ip_forward=1
grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf || echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf

# Varsayılan politikaları temizle ve FORWARD'a izin ver (PEP scripti dinamik yönetecek)
iptables -F
iptables -t nat -F
iptables -P FORWARD ACCEPT

echo "[OK] Gateway (PIP/PDP/PEP) kurulumu tamamlandi."
