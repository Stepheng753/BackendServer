---
name: nginx_setup
description: Manage, test, reload, and configure Nginx server blocks for subdomains on stepheng753.com.
---

# Nginx Configuration and Management Skill

This skill guides the agent in editing, deploying, testing, and troubleshooting Nginx server block configurations.

## Core Operations

### 1. Test Nginx Configuration
Before applying changes, always run a dry run check to prevent crashing the server block routing:
```bash
sudo nginx -t
```

### 2. Reload Nginx (Zero Downtime)
Use reload to apply new configurations without interrupting current active connections:
```bash
sudo systemctl reload nginx
```
*(Alternatively, you can run `./reload_nginx.sh` if in the local script directory).*

### 3. Service Status
Check if Nginx is active and running:
```bash
sudo systemctl status nginx
```

---

## Directory Structure and Symlinks

Nginx configurations are stored in `sites-available` and symlinked to `sites-enabled` to activate:
- **Available Site Configs**: `/etc/nginx/sites-available/`
- **Active Site Configs**: `/etc/nginx/sites-enabled/`

### Activating a Site Configuration
To enable a configuration file (e.g., `dev.example.com`):
```bash
sudo ln -sf /etc/nginx/sites-available/dev.example.com /etc/nginx/sites-enabled/
```
*(Always test syntax with `sudo nginx -t` and reload `sudo systemctl reload nginx` immediately after).*

---

## Creating Nginx Files from the Template

To create a new subdomain configuration from the generic template:
1. Locate the generic template in [nginx.conf.template](../../Setup/nginx.conf.template).
2. Identify the appropriate template style for the target subdomain (Unix socket, Static + API, or Local Port).
3. Copy the configuration block to `/etc/nginx/sites-available/<subdomain>.<domain_name>`, replacing placeholders with the server configuration details inside the local, git-ignored [setup.conf](../../Setup/setup.conf).
4. Run certbot for SSL setup:
   ```bash
   sudo certbot --nginx -d <subdomain>.<domain_name>
   ```

---

## SSL Certificates with Certbot

To obtain certificates for a new subdomain using DNS manual challenge:
```bash
sudo certbot certonly --manual --preferred-challenges dns -d SUBDOMAIN.example.com
```

### Automatic Certbot Insertion
Running `sudo certbot --nginx -d SUBDOMAIN.example.com` will automatically edit Nginx config files to append the following:
```nginx
ssl_certificate /etc/letsencrypt/live/SUBDOMAIN.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/SUBDOMAIN.example.com/privkey.pem;
include /etc/letsencrypt/options-ssl-nginx.conf;
ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
```

---

## Troubleshooting Common Errors

### 1. Nginx Port Conflict
If `nginx -t` fails reporting "address already in use":
```bash
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :443
```

### 2. Permission Denied on Unix Sockets
If Nginx returns `502 Bad Gateway` when trying to proxy to Gunicorn:
- Check that the Unix socket (e.g., `/tmp/flask_api.sock`) exists.
- Check permissions on the socket. Gunicorn must start with `-m 007` and Nginx/Gunicorn must share access groups (typically both user or `www-data`).
- Check Gunicorn status: `sudo systemctl status my_flask_api.service`.
