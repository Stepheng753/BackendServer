# Hostinger DNS, Dynamic DNS & Certbot SSL Setup Guide

This guide details how to configure domain names on **Hostinger**, route subdomains to your home server using **Dynamic DNS (DDNS)**, and provision free, automated **Let's Encrypt SSL/TLS certificates** using **Certbot**.

---

## 1. Architecture & DNS Flow

Residential internet connections use dynamic WAN IP addresses that change whenever the modem restarts or the ISP reallocates IP leases. 

To host services reliably on `stepheng753.com` without purchasing a costly static IP from your ISP:

```
[Public Visitor] ───> https://dev.stepheng753.com
                              │
                              ▼
           [Hostinger DNS (CNAME record)]
           dev.stepheng753.com ➔ flash-server.tplinkdns.com
                              │
                              ▼
           [TP-Link Deco DDNS]
           Resolves to your current Router WAN IP (e.g. 76.x.x.x)
                              │
                              ▼
           [Router Port Forwarding (Port 443)]
           Forwards incoming HTTPS to Home Server (192.168.68.55:443)
                              │
                              ▼
           [Server Nginx Reverse Proxy]
           Terminates SSL via Let's Encrypt Certbot Certificate
           Routes traffic to internal backend (Unix socket / Docker / PM2)
```

---

## 2. Hostinger DNS Management (hPanel)

### 2.1. Accessing Hostinger DNS Zone
1. Log into your **Hostinger Control Panel** at [hpanel.hostinger.com](https://hpanel.hostinger.com).
2. Navigate to **Domains** -> Select your domain (e.g., `stepheng753.com`).
3. In the left sidebar, click **DNS / Nameservers**.
4. Ensure the domain is using **Hostinger Default Nameservers** (e.g., `ns1.dns-parking.com` and `ns2.dns-parking.com`).

### 2.2. Setting Up Dynamic DNS (DDNS) CNAME Records
Instead of pointing every subdomain to an IP address (`A` record) that changes periodically, point your subdomains to your router's permanent DDNS hostname using **CNAME** records.

In the **Manage DNS records** section, add the following CNAME records:

| Type | Name (Host) | Points To (Target) | TTL | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **CNAME** | `dev` | `flash-server.tplinkdns.com` | `300` (or 1/2 hour) | Development backend & Swagger API (`dev.stepheng753.com`) |
| **CNAME** | `pics` | `flash-server.tplinkdns.com` | `300` | Immich Photo & Video Server (`pics.stepheng753.com`) |
| **CNAME** | `vids` | `flash-server.tplinkdns.com` | `300` | Jellyfin Media Streaming (`vids.stepheng753.com`) |
| **CNAME** | `n8n` | `flash-server.tplinkdns.com` | `300` | Workflow Automation Platform (`n8n.stepheng753.com`) |
| **CNAME** | `aiu` | `flash-server.tplinkdns.com` | `300` | AI University Web Application (`aiu.stepheng753.com`) |
| **CNAME** | `*` (Optional) | `flash-server.tplinkdns.com` | `300` | Catch-all wildcard for any new staging subdomains |

> [!TIP]
> Setting TTL to `300` (5 minutes) allows DNS changes to propagate rapidly across the internet when creating new subdomains or troubleshooting.

### 2.3. Testing Hostinger DNS Propagation
From your terminal or WSL, verify that your Hostinger CNAME record resolves to your TP-Link DDNS hostname and resolves to your public IP:

```bash
# Check CNAME record
dig CNAME dev.stepheng753.com +short
# Output should return: flash-server.tplinkdns.com.

# Check resolved public IP
dig A dev.stepheng753.com +short
# Output should return your router's public WAN IP
```

---

## 3. Router Port Forwarding & Firewall Prerequisite

Before Certbot can issue SSL certificates via HTTP-01 ACME challenge, your server must be reachable from the internet on standard web ports.

### 3.1. TP-Link Deco Port Forwarding
In your Deco smartphone app (**More** -> **Advanced** -> **NAT Forwarding** -> **Port Forwarding**):

1. **HTTP (ACME Challenge & Redirect)**:
   * Internal IP: `192.168.68.55`
   * Internal Port: `80`
   * External Port: `80`
   * Protocol: `TCP`
2. **HTTPS (Encrypted Web Traffic)**:
   * Internal IP: `192.168.68.55`
   * Internal Port: `443`
   * External Port: `443`
   * Protocol: `TCP`
3. **HTTP Fallback (ISP Port 80 Block Workaround)**:
   * If your ISP blocks inbound port 80, set external port `8463` to forward to internal port `8463`.

### 3.2. Host UFW Firewall
Ensure the Linux firewall on the host permits Nginx traffic:
```bash
sudo ufw allow 80/tcp comment 'Nginx HTTP / ACME'
sudo ufw allow 443/tcp comment 'Nginx HTTPS'
sudo ufw allow 8463/tcp comment 'Nginx HTTP Fallback Redirect'
sudo ufw status verbose
```

---

## 4. Certbot Installation & Configuration

Certbot is the official client for Let's Encrypt, an automated certificate authority providing free, valid TLS/SSL certificates.

### 4.1. Install Certbot and Nginx Plugin
On Ubuntu 24.04 LTS:
```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

Verify installation:
```bash
certbot --version
```

---

## 5. Provisioning SSL Certificates

### 5.1. Method 1: Automatic Nginx Configuration (Recommended)
If you already have Nginx server blocks created in `/etc/nginx/sites-available/` with `server_name` defined, Certbot can automatically verify ownership and configure SSL directives.

Run Certbot targeting your subdomains:
```bash
sudo certbot --nginx \
  -d dev.stepheng753.com \
  -d aiu.stepheng753.com \
  -d pics.stepheng753.com \
  -d vids.stepheng753.com \
  -d n8n.stepheng753.com
```

**During the interactive prompt:**
1. **Enter email address**: Used for urgent security and renewal notices from Let's Encrypt.
2. **Agree to Terms of Service**: Type `Y`.
3. **Opt-in/out to EFF newsletter**: Type `N` (optional).
4. **HTTPS Redirect**: Certbot will ask whether to redirect HTTP traffic to HTTPS. Select **2: Redirect** (or handle it manually using the templates in `docs/setup/website.md`).

### 5.2. Method 2: Standalone or Webroot Certificate Generation
If you want to obtain certificates before configuring Nginx:
```bash
# Temporarily stop Nginx if using standalone port 80
sudo systemctl stop nginx
sudo certbot certonly --standalone -d dev.stepheng753.com
sudo systemctl start nginx
```

Or using webroot with Nginx running:
```bash
sudo certbot certonly --webroot -w /var/www/html -d dev.stepheng753.com
```

### 5.3. Certificate File Locations
Once issued, Certbot saves certificates in `/etc/letsencrypt/live/<primary-domain>/`:

| File | Purpose | Nginx Directive |
| :--- | :--- | :--- |
| `fullchain.pem` | Full certificate chain (Server cert + intermediate certs) | `ssl_certificate` |
| `privkey.pem` | Private key of the certificate (Keep secret!) | `ssl_certificate_key` |
| `cert.pem` | Server certificate only (Generally not used alone) | — |
| `chain.pem` | Intermediate CA certificate (Used for OCSP stapling) | `ssl_trusted_certificate` |

---

## 6. Nginx SSL Hardening Configuration

To ensure an **A+ Rating** on Qualys SSL Labs, add hardened SSL parameters to `/etc/nginx/snippets/ssl-params.conf`:

```nginx
# /etc/nginx/snippets/ssl-params.conf

# Modern TLS protocols only (deprecate TLSv1 and TLSv1.1)
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_ciphers 'TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384';

# SSL Session optimizations
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
ssl_session_tickets off;

# OCSP Stapling (speeds up TLS handshakes)
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 1.1.1.1 valid=300s;
resolver_timeout 5s;

# HTTP Strict Transport Security (HSTS)
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
```

Include this snippet in each of your subdomain server blocks:
```nginx
server {
    listen 443 ssl http2;
    server_name dev.stepheng753.com;

    ssl_certificate /etc/letsencrypt/live/dev.stepheng753.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/dev.stepheng753.com/privkey.pem;
    include /etc/nginx/snippets/ssl-params.conf;

    location / {
        proxy_pass http://unix:/tmp/dev_stepheng753_com_api.sock;
        ...
    }
}
```

---

## 7. Automated SSL Certificate Renewal

Let's Encrypt certificates are valid for **90 days**. Certbot manages automated renewal natively.

### 7.1. Testing Renewal Dry Run
Run a renewal test to verify that the challenge works and certificates will renew without intervention:
```bash
sudo certbot renew --dry-run
```
If you see `Congratulations, all simulated renewals succeeded`, your setup is 100% automated.

### 7.2. Verifying Systemd Renewal Timer
Ubuntu installs a systemd timer that triggers `certbot renew` twice every day:
```bash
systemctl status certbot.timer
```

To automatically reload Nginx whenever certificates are renewed, add a deploy hook in `/etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh`:
```bash
sudo tee /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh << 'EOF'
#!/bin/bash
systemctl reload nginx
EOF

sudo chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh
```

---

## 8. Troubleshooting Common Issues

### Issue 1: `Challenge failed for domain ... (Connection refused / Timeout)`
* **Cause**: Inbound port `80` is not forwarded on the router, or UFW is blocking traffic.
* **Fix**: Check `sudo ufw status` and ensure TP-Link Deco forwards Port `80` -> `192.168.68.55:80`. Check ISP terms to see if port 80 is blocked inbound.

### Issue 2: `DNS problem: NXDOMAIN looking up A for ...`
* **Cause**: The Hostinger CNAME record has not propagated, or the subdomain spelling doesn't match.
* **Fix**: Run `dig CNAME <subdomain>.stepheng753.com` and wait 5–15 minutes for Hostinger DNS TTL to expire.

### Issue 3: `Too many certificates already issued for exact set of domains`
* **Cause**: Let's Encrypt has a rate limit of 5 duplicate certificates per week.
* **Fix**: Use `--dry-run` while debugging configurations, and reuse existing certificates in `/etc/letsencrypt/live/`.
