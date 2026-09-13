# Linux Host Server Setup & Maintenance Guide

This document is a comprehensive runbook for provisioning, hardening, and maintaining the **host machine** (`flash-server`), including operating system setup, firewall security, runtimes, systemd daemon management, disk mounts, and background system maintenance.

---

## 1. Initial Machine Provisioning (Ubuntu 24.04 LTS)

### 1.1. System Updates & Core Packages
Run system package upgrades and install primary compilation and networking utilities:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential curl wget git ufw htop net-tools software-properties-common ca-certificates gnupg lsb-release
```

### 1.2. Administrative User & Sudo
Ensure your non-root administrative user (`flash-server`) is configured:
```bash
sudo adduser flash-server
sudo usermod -aG sudo flash-server
```

### 1.3. UFW Firewall Hardening
Configure the host firewall to deny untracked incoming traffic while permitting essential services:
```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Remote access
sudo ufw allow 22/tcp      # OpenSSH
sudo ufw allow 3389/tcp    # GNOME Remote Desktop (RDP, optional)

# Web & Edge traffic
sudo ufw allow 80/tcp      # HTTP (Let's Encrypt ACME & redirects)
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 8463/tcp    # ISP redirect port (if port 80 is blocked by residential ISP)

# Local Area Network Only (Samba Windows File Sharing)
sudo ufw allow from 192.168.68.0/22 to any port 139,445 proto tcp

sudo ufw enable
```

---

## 2. Runtimes & Toolchain Installation

### 2.1. Python 3.12+ & Virtual Environments
Ubuntu 24.04 enforces PEP 668 (externally managed environments). Always install `python3-venv` and use isolated virtual environments:
```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev
```

### 2.2. Node.js 22 LTS & PM2
Install Node.js via the official NodeSource repository:
```bash
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g pm2

# Enable PM2 auto-resurrection on system boot:
pm2 startup systemd
# Run the command printed by the output (with sudo)
```

### 2.3. Docker Engine & Docker Compose (v2)
Install the official Docker Engine (Docker CE) with Docker Compose v2:
```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Grant your user docker access without sudo
sudo usermod -aG docker $USER
newgrp docker
```

### 2.4. Nginx Web Server & Certbot
```bash
sudo apt install -y nginx certbot python3-certbot-nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 2.5. Tailscale Mesh VPN
Tailscale provides encrypted, zero-configuration remote access to your server across NATs and firewalls:
```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
# Authenticate in browser to join your tailnet (e.g. 100.66.69.41)
```

---

## 3. Storage Disks & Media Shares Mounts (`/etc/fstab`)

On `flash-server`, dedicated NTFS drives provide high-capacity storage for media, photos, and backups.

### 3.1. NTFS-3G Driver
Install the NTFS driver for stable read/write mounting:
```bash
sudo apt install -y ntfs-3g
```

### 3.2. Permanent Mount Configuration in `/etc/fstab`
Create mount target directories:
```bash
sudo mkdir -p /media/NetworkShare/Dragon-Ball
sudo mkdir -p /media/NetworkShare/Photos
sudo mkdir -p /media/NetworkShare/CapCut-Videos
sudo mkdir -p /media/NetworkShare/TV-Series
```

Inspect disk UUIDs with `sudo blkid`, then append mount entries to `/etc/fstab`:
```ini
# /etc/fstab entries for media drives
/dev/sdb1  /media/NetworkShare/Dragon-Ball    ntfs-3g  defaults,uid=1000,gid=1000,umask=022  0  0
/dev/sdc1  /media/NetworkShare/Photos         ntfs-3g  defaults,uid=1000,gid=1000,umask=022  0  0
/dev/sdd1  /media/NetworkShare/CapCut-Videos  ntfs-3g  defaults,uid=1000,gid=1000,umask=022  0  0
/dev/sde2  /media/NetworkShare/TV-Series      ntfs-3g  defaults,uid=1000,gid=1000,umask=022  0  0
```

Verify mount validity without rebooting:
```bash
sudo mount -a
df -h
```

---

## 4. Router Port Forwarding & Dynamic DNS (DDNS)

Because residential ISPs assign dynamic WAN IP addresses, your router must update a DDNS record and forward external incoming ports to your server (`192.168.68.55`).

### 4.1. Router-Level DDNS (TP-Link Deco)
1. Open the **Deco App** on your smartphone.
2. Go to **More** -> **Advanced** -> **DDNS**.
3. Enable DDNS and register your prefix: `flash-server`.
4. Your permanent router hostname becomes: `flash-server.tplinkdns.com`.

### 4.2. Port Forwarding Rules Table
In your router settings, forward the following external ports to `192.168.68.55`:

| Rule Name | External Port | Internal Port | Protocol | Destination IP | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **HTTP** | `80` | `80` | TCP | `192.168.68.55` | Let's Encrypt ACME verification & HTTP redirect |
| **HTTPS** | `443` | `443` | TCP | `192.168.68.55` | Secure web traffic for all subdomains |
| **HTTP_REDIRECT** | `8463` | `8463` | TCP | `192.168.68.55` | Fallback HTTP-to-HTTPS redirect if ISP blocks port 80 |

### 4.3. DNS Registrar CNAME Records
At your domain registrar (e.g. Cloudflare, Hostinger), add CNAME records pointing your subdomains to your router DDNS hostname:
```
dev   CNAME  flash-server.tplinkdns.com
pics  CNAME  flash-server.tplinkdns.com
vids  CNAME  flash-server.tplinkdns.com
n8n   CNAME  flash-server.tplinkdns.com
AIU   CNAME  flash-server.tplinkdns.com
```

---

## 5. System Maintenance & Automated Timers

Verify that essential background systemd timers are active:
```bash
systemctl list-timers
```

* **`certbot.timer`**: Automatically renews Let's Encrypt certificates twice daily.
* **`fstrim.timer`**: Runs weekly SSD TRIM operations on root SSD storage.
* **`logrotate.timer`**: Daily rotation and compression of system and application logs to prevent disk exhaustion.
* **`sysstat-collect.timer`**: Periodically samples system hardware counters.

---

## 6. Server Health & Monitoring

The host server metrics (CPU load, thermal zones, memory, storage utilization, and top processes) are monitored live via the **Monitoring Module**:
* URL: `https://dev.stepheng753.com/monitoring`
* Telemetry API: `https://dev.stepheng753.com/api/monitoring/system`

---

## 7. Related Setup Documentation

* **[Hostinger DNS & Certbot SSL Guide](file:///home/stepheng753/Development/BackendServer/docs/setup/dns-and-ssl.md)**: Hostinger DNS CNAME configuration, dynamic DNS routing, port forwarding, and Let's Encrypt automated certificate issuance.
* **[Website & Nginx Projects Deployment](file:///home/stepheng753/Development/BackendServer/docs/setup/website.md)**: Nginx reverse proxy configurations, PM2 process management, Docker web containers, and Python WSGI socket deployment.

