# Server and Network Configuration Guide

This guide explains how to configure the server network environment, router settings, domain mapping, and Nginx reverse proxy. 

> [!IMPORTANT]
> This guide uses placeholder example values. Your specific server configuration (actual IPs, ports, domains, and subdomains) must only be defined in your local, git-ignored [setup.conf](./setup.conf).

## Example Configuration Values
The examples throughout this guide assume the following network layout:
- **Example Domain**: `example.com`
- **Example DDNS Hostname**: `homeserver.tplinkdns.com` (managed by router)
- **Example Local Server IP**: `192.168.1.100` (internal host IP)
- **Example Router Gateway IP**: `192.168.1.1`
- **Example Ports**:
  - HTTP Redirect Port: `8080` (used if standard port 80 is blocked by ISP)
  - HTTP standard Port: `80`
  - HTTPS secure Port: `443`
- **Example Subdomains**: `dev.example.com`, `api.example.com`, `app.example.com`

---

## 0. Overview: Request Flow Direction

The diagram below maps how a request traverses the internet from a client's browser, through DNS and the home router, to the individual services running on your server (`192.168.1.100`).

```mermaid
graph TD
    Client[Client Browser] -->|dns lookup| Hostinger[DNS Registrar Zone]
    Hostinger -->|cname resolve| DDNS[Router DDNS: homeserver.tplinkdns.com]
    DDNS -->|public ip| Router[Router Gateway: 192.168.1.1]
    
    subgraph Router Port Forwarding
        Router -->|Port 80 / 8080| NginxRedirect[Nginx HTTP Redirect]
        Router -->|Port 443| NginxHTTPS[Nginx Reverse Proxy]
    end

    subgraph Internal Server: 192.168.1.100
        NginxRedirect -->|301 Redirect| Client
        NginxHTTPS -->|proxy_pass unix socket| Gunicorn[Gunicorn / Flask dev.example.com]
        NginxHTTPS -->|proxy_pass localhost:3000| App2[Service 2 api.example.com]
        NginxHTTPS -->|proxy_pass localhost:5678| App3[Service 3 app.example.com]
    end
```

For specific system and application configurations, refer to:
- [setup.conf](./setup.conf) - Local configuration variables.
- [BackendSetUp.md](./BackendSetUp.md) - Gunicorn and Flask application deployment.

---

## 1. Dynamic DNS (DDNS)

A Dynamic DNS hostname automatically points to your home network's public IP address, which your ISP dynamically changes.

### Option A (Recommended): Router-Level DDNS (TP-Link Deco / Other)
DDNS is best configured directly within the router hardware via its administrative interface or app. This is more stable than terminal-based scripts because the hardware instantly detects WAN changes.

If using a TP-Link Deco system:
1. Open the **Deco App** on your mobile device.
2. Navigate to **More** (bottom right menu) -> **Advanced** -> **DDNS**.
3. Toggle DDNS **ON**.
4. Register your domain prefix (e.g., `homeserver`) to bind to `tplinkdns.com`.
5. Your hostname becomes: `homeserver.tplinkdns.com`.

### Option B: Terminal Client (DUC)
If you prefer a terminal-based third-party solution (like No-IP), you can install the Dynamic Update Client (DUC) on your Linux server:

```bash
cd /tmp
wget http://www.no-ip.com/client/linux/noip-duc-linux.tar.gz
tar xf noip-duc-linux.tar.gz
cd noip-2.1.9-1/
sudo make install
```
Configure the DUC with your provider credentials and your registered hostname.

---

## 2. Router Port Forwarding

Port forwarding tells your router which local device should receive traffic hitting specific external ports.

### Configuration Target (Example values)
- **Gateway IP**: `192.168.1.1`
- **Server Local IP**: `192.168.1.100`

### Forwarding Rules Table
Open your router's administrative page or app, navigate to **Port Forwarding** / **Virtual Servers**, and add the following rules pointing to your server's local IP:

| Rule Name | External Port | Internal Port | Protocol | Device IP | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **HTTP** | `80` | `80` | TCP | `192.168.1.100` | Required for standard HTTP redirects and ACME SSL validation challenges. |
| **HTTPS** | `443` | `443` | TCP | `192.168.1.100` | Primary entry point for all secure web traffic. |
| **HTTP_REDIRECT** | `8080` | `8080` | TCP | `192.168.1.100` | Custom port used for HTTP-to-HTTPS redirect if standard port 80 is blocked by your ISP. |

> [!NOTE]
> Many residential internet service providers (ISPs) block incoming traffic on standard port 80. If your ISP blocks port 80, you can configure a custom redirect port (e.g., `8080`). Alternatively, if you always connect directly via HTTPS (`https://`), you can omit the HTTP/HTTP_REDIRECT forwarding rules entirely since HTTPS (443) traffic will still route correctly.

---

## 3. DNS Configuration (Registrar)

You must configure DNS records to route your custom domain and subdomains to your home router. Because the public IP is dynamic, you route subdomains to your DDNS hostname using **CNAME** records.

### How to configure CNAMEs (e.g., Hostinger / GoDaddy):
1. Log in to your **DNS Registrar's Control Panel**.
2. Navigate to your domain's **DNS Zone Editor**.
3. Create the following records:

| Type | Name (Host/Subdomain) | Points to (Value) | TTL |
| :--- | :--- | :--- | :--- |
| `CNAME` | `dev` | `homeserver.tplinkdns.com` | Default |
| `CNAME` | `api` | `homeserver.tplinkdns.com` | Default |
| `CNAME` | `app` | `homeserver.tplinkdns.com` | Default |

---

## 4. Nginx Server Configuration

Nginx receives incoming HTTP/HTTPS traffic on the server, matches the domain header, and proxies the request to the right service.

### 4.1. Installation
Install Nginx and verify it starts:
```bash
sudo apt update
sudo apt install nginx -y
sudo systemctl start nginx
```

### 4.2. Configurations Template
Configurations are managed under `/etc/nginx/sites-available/` and symlinked to `/etc/nginx/sites-enabled/`. Refer to [nginx.conf.template](./nginx.conf.template) for exact structural blocks.

---

## 5. SSL Certificates (Let's Encrypt manual DNS challenge)

Since your home server is behind a router, using Let's Encrypt's DNS challenge is the most robust way to secure your subdomains.

### 5.1. Run Certbot Manual Challenge
Execute the command for your subdomain:
```bash
sudo certbot certonly --manual --preferred-challenges dns -d dev.example.com
```

### 5.2. Deploy the DNS TXT Record
Certbot will pause and provide a challenge:
- **Record Name**: `_acme-challenge.dev.example.com`
- **Record Type**: `TXT`
- **Value**: `YOUR_UNIQUE_CHALLENGE_STRING`

1. Go to your registrar's **DNS Zone Editor**.
2. Add a `TXT` record with the exact Name/Value.
3. Wait 1–2 minutes, then hit **Enter** in your terminal to complete verification.
4. Certbot outputs certificates to `/etc/letsencrypt/live/dev.example.com/`.

---

## 6. Nginx Workspace Skill
For troubleshooting, syntax validation, and reloading Nginx without service disruption, consult the custom agent workspace skill:
- [nginx_setup Skill Instructions](../.agents/skills/nginx_setup/SKILL.md)
