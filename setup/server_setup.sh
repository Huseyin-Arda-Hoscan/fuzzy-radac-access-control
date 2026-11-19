#!/usr/bin/env bash
set -e

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-pip net-tools curl iperf3 tcpdump

# İstemci alt ağına (192.168.50.0/24) dönüş trafiğini Gateway (192.168.60.2) üzerinden yönlendir
ip route replace 192.168.50.0/24 via 192.168.60.2

# Kalıcı rota ve arka plan HTTP servisleri
cat << 'EOF' > /etc/systemd/system/target-services.service
[Unit]
Description=Target Corporate Web and Sensitive Services
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /vagrant/server_app/target_server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now target-services.service

echo "[OK] Server kurulumu ve rotasi tamamlandi."
