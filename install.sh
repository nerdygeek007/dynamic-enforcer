#!/bin/bash
if [ "$EUID" -ne 0 ]; then
  echo "[-] FATAL: Please run as root (sudo ./install.sh)"
  exit 1
fi

echo "[*] Initializing MVD Deployment Sequence..."

# Map configuration to /etc/ (System Standards)
mkdir -p /etc/mvd-security
cp config/mvd_config.json /etc/mvd-security/
echo "[+] Configuration mapped to /etc/mvd-security/"

# Map binary to /usr/local/bin/
cp src/mvd_agent.py /usr/local/bin/
chmod +x /usr/local/bin/mvd_agent.py
echo "[+] Daemon binary mapped to /usr/local/bin/"

# Hook into OS boot routines
cp systemd/mvd.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable mvd.service
systemctl start mvd.service

echo "[+] Deployment Complete."
echo "[+] MVD is now running headless. Check logs with: systemctl status mvd"
