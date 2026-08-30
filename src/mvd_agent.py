import json, sys, os, time, re, ipaddress, subprocess

# ENVIRONMENT PATHING LOGIC
PROD_CONFIG = "/etc/mvd-security/mvd_config.json"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEV_CONFIG = os.path.join(SCRIPT_DIR, "../config/mvd_config.json")

# Use /etc/ if it exists (systemd), otherwise use local config (dev)
CONFIG_PATH = PROD_CONFIG if os.path.exists(PROD_CONFIG) else DEV_CONFIG

IP_REGEX = re.compile(r"(?P<ip>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
BLOCKLIST = set()
ATTEMPTS = {}

def get_iptables_path():
    for path in ["/usr/sbin/iptables", "/sbin/iptables", "/usr/bin/iptables", "/bin/iptables"]:
        if os.path.exists(path) and os.access(path, os.X_OK):
            return path
    return None

IPTABLES_CMD = get_iptables_path()

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"[-] FATAL: Configuration not found at {CONFIG_PATH}")
        sys.exit(1)
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[-] FATAL: Invalid JSON structure. {e}")
        sys.exit(1)

def block_ip(ip):
    if not IPTABLES_CMD or ip in BLOCKLIST: return
    print(f"[!] KERNEL DROP INITIATED: {ip} via {IPTABLES_CMD}")
    try:
        subprocess.run([IPTABLES_CMD, "-A", "INPUT", "-s", ip, "-j", "DROP"], check=True)
        BLOCKLIST.add(ip)
        print(f"[+] Successfully injected Netfilter hook for {ip}")
    except subprocess.CalledProcessError as e:
        print(f"[-] FAILED to inject rule: {e}")

def process_line(line, config):
    for sig in config["signatures"]:
        if sig in line:
            match = IP_REGEX.search(line)
            if match:
                ip_str = match.group("ip")
                try:
                    ipaddress.IPv4Address(ip_str)
                    if not (ip_str.startswith("127.") or ip_str.startswith("10.")):
                        ATTEMPTS[ip_str] = ATTEMPTS.get(ip_str, 0) + 1
                        if ATTEMPTS[ip_str] >= config['threshold']:
                            block_ip(ip_str)
                except ValueError:
                    pass

def main():
    if not IPTABLES_CMD:
        print("[-] FATAL: iptables is not installed or accessible.")
        sys.exit(1)
        
    config = load_config()
    print(f"[*] Config loaded from {CONFIG_PATH}")
    print("[*] MVD Agent Online. Hooking files...")
    
    files = []
    for target in config["targets"]:
        log_path = target["file"]
        if os.path.exists(log_path):
            f = open(log_path, "r")
            f.seek(0, 2)
            files.append(f)
            print(f"[+] Hooked {log_path}")
            
    try:
        while True:
            data_read = False
            for f in files:
                line = f.readline()
                if line:
                    process_line(line, config)
                    data_read = True
            if not data_read: time.sleep(0.5)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
