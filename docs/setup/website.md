# Deploying Websites & Services with Nginx Reverse Proxy

This guide covers how to deploy and expose any website, web application, or backend service on this server. It details Nginx configuration patterns, automated SSL certificate issuance via Certbot, and process management.

---

## 1. Nginx Architecture & Directory Conventions

Nginx handles edge traffic on ports 80, 443, and 8463, terminating SSL certificates and routing requests locally:

* **`/etc/nginx/sites-available/`**: Storage for all virtual host configuration files. One file per subdomain.
* **`/etc/nginx/sites-enabled/`**: Symlinks pointing to active files in `sites-available/`.
* **Zero-Downtime Reload**: Never stop Nginx to update configuration. Always test syntax and reload:
  ```bash
  sudo nginx -t && sudo systemctl reload nginx
  ```

---

## 2. The 4 Common Project Deployment Patterns

Select the pattern that matches your application's architecture:

### Pattern 1: Static Website (React / Vite / Next.js Export / HTML)
Used for single-page applications or static websites that do not require a Node.js server at runtime.

1. **Build the production assets**:
   ```bash
   cd /home/flash-server/Development/my-frontend
   npm install && npm run build
   # Assets are generated in /home/flash-server/Development/my-frontend/dist
   ```
2. **Create Nginx configuration** (`/etc/nginx/sites-available/mysite.stepheng753.com`):
   ```nginx
   server {
       listen 80;
       server_name mysite.stepheng753.com;

       root /home/flash-server/Development/my-frontend/dist;
       index index.html;

       # Enable gzip compression
       gzip on;
       gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

       location / {
           try_files $uri $uri/ /index.html;
       }

       # Cache static assets
       location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
           expires 30d;
           add_header Cache-Control "public, no-transform";
       }
   }
   ```
3. Enable and secure:
   ```bash
   sudo ln -s /etc/nginx/sites-available/mysite.stepheng753.com /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   sudo certbot --nginx -d mysite.stepheng753.com
   ```

---

### Pattern 2: Node.js / PM2 Application (e.g. AIU Platform)
Used for fullstack Node.js, Express, or Next.js applications requiring background server execution and WebSockets.

1. **Start application with PM2**:
   ```bash
   cd /home/flash-server/Development/AIU/aiu-backend
   pm2 start index.js --name "aiu-backend"
   pm2 save
   ```
2. **Create Nginx configuration** (`/etc/nginx/sites-available/AIU.stepheng753.com`):
   ```nginx
   server {
       listen 80;
       server_name AIU.stepheng753.com;

       # Serve static frontend
       location / {
           root /home/flash-server/Development/AIU/aiu-web/dist;
           try_files $uri $uri/ /index.html;
       }

       # Proxy API requests to PM2 Node.js process on port 3000
       location /api/ {
           proxy_pass http://127.0.0.1:3000/;
           proxy_http_version 1.1;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }

       # WebSocket endpoint
       location /ws {
           proxy_pass http://127.0.0.1:3000/ws;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_read_timeout 86400s;
           proxy_send_timeout 86400s;
       }
   }
   ```
3. Enable and secure:
   ```bash
   sudo ln -s /etc/nginx/sites-available/AIU.stepheng753.com /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   sudo certbot --nginx -d AIU.stepheng753.com
   ```

---

### Pattern 3: Docker Container Service (e.g. Immich, n8n, qBittorrent)
Used for containerized applications listening on a local port.

1. **Start Docker Compose service**:
   ```bash
   cd /home/flash-server/Services/N8N
   docker compose up -d
   # Service exposes port 5678 locally
   ```
2. **Create Nginx configuration** (`/etc/nginx/sites-available/n8n.stepheng753.com`):
   ```nginx
   server {
       listen 80;
       server_name n8n.stepheng753.com;

       client_max_body_size 50M;

       location / {
           proxy_pass http://127.0.0.1:5678;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_read_timeout 300s;
       }
   }
   ```
3. Enable and secure:
   ```bash
   sudo ln -s /etc/nginx/sites-available/n8n.stepheng753.com /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   sudo certbot --nginx -d n8n.stepheng753.com
   ```

---

### Pattern 4: Python / Gunicorn Flask API (BackendServer)
Used for Python WSGI applications communicating through high-performance local Unix domain sockets.

1. **Systemd Service Unit** (`/etc/systemd/system/dev_stepheng753_com_api.service`):
   ```ini
   [Unit]
   Description=Gunicorn API service for dev.stepheng753.com
   After=network.target

   [Service]
   User=flash-server
   Group=www-data
   WorkingDirectory=/home/flash-server/Development/BackendServer
   Environment="PATH=/home/flash-server/Development/BackendServer/.venv/bin"
   Environment="OAUTHLIB_INSECURE_TRANSPORT=1"
   ExecStart=/home/flash-server/Development/BackendServer/.venv/bin/gunicorn \
             --workers 4 \
             --bind unix:/tmp/dev_stepheng753_com_api.sock \
             -m 007 \
             --timeout 300 \
             app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   Start service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable --now dev_stepheng753_com_api.service
   ```

2. **Nginx Configuration** (`/etc/nginx/sites-available/dev.stepheng753.com`):
   ```nginx
   # Handle custom ISP redirect port if port 80 is blocked
   server {
       listen 8463;
       server_name dev.stepheng753.com;
       return 301 https://$host$request_uri;
   }

   server {
       listen 80;
       server_name dev.stepheng753.com;
       return 301 https://$host$request_uri;
   }

   server {
       listen 443 ssl;
       server_name dev.stepheng753.com;

       client_max_body_size 10M;

       location / {
           proxy_pass http://unix:/tmp/dev_stepheng753_com_api.sock;
           proxy_http_version 1.1;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_read_timeout 300s;
       }
   }
   ```
3. Enable and obtain SSL certificate with Certbot.

---

## 3. Checklist for Launching Any New Website

Follow this checklist whenever launching a new subdomain:

1. [ ] **DNS CNAME**: In registrar, point `<subdomain>` to `flash-server.tplinkdns.com`.
2. [ ] **App Running**: Verify the app responds locally on its port (e.g. `curl http://127.0.0.1:3000`).
3. [ ] **Nginx Config**: Create `/etc/nginx/sites-available/<subdomain>.stepheng753.com` using the appropriate pattern.
4. [ ] **Symlink**: `sudo ln -s /etc/nginx/sites-available/<subdomain>.stepheng753.com /etc/nginx/sites-enabled/`.
5. [ ] **Syntax Test**: `sudo nginx -t`.
6. [ ] **Reload**: `sudo systemctl reload nginx`.
7. [ ] **SSL Certificate**: `sudo certbot --nginx -d <subdomain>.stepheng753.com`.
8. [ ] **Verification**: Open `https://<subdomain>.stepheng753.com` in a browser.

---

## 4. Related Setup Documentation

* **[Server Hardware & Environment Setup](file:///home/stepheng753/Development/BackendServer/docs/setup/server.md)**: Host OS, UFW firewall, Docker CE, storage drives, and background timers.
* **[Hostinger DNS & Certbot SSL Guide](file:///home/stepheng753/Development/BackendServer/docs/setup/dns-and-ssl.md)**: Hostinger DNS CNAME records, dynamic DNS routing, router port forwarding, and Let's Encrypt automated certificate issuance.

