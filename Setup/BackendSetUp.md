# Flask and Gunicorn Backend Deployment Guide

This guide explains how to deploy your Flask backend application under a production-grade environment using Gunicorn as the WSGI server and Nginx as the reverse proxy.

> [!IMPORTANT]
> This guide uses placeholder example values. Your specific server configuration (actual usernames, paths, domains, and subdomains) must only be defined in your local, git-ignored [setup.conf](./setup.conf).

## Example Configuration Values
The examples throughout this guide assume the following configuration:
- **Example Domain**: `dev.example.com`
- **Example Server Username**: `example-user`
- **Example Project Directory**: `/home/example-user/BackendServer/Flask-App`
- **Example Virtual Environment**: `/home/example-user/BackendServer/Flask-App/.venv`
- **Example Unix Socket**: `unix:/tmp/flask_api.sock`
- **Example Systemd Service**: `my_flask_api.service`

---

## 1. Preparing the Flask Application for Production

During local development, you might run Flask using `app.run()`. In a production environment, this server is inefficient and insecure. Instead, we use Gunicorn to run the application instance directly.

### 1.1. Application Code Adaptation
Ensure that your main application file (e.g., [app.py](../Flask-App/app.py)) exports the Flask `app` object without calling blocking servers inside `__main__`:

```python
# app.py
from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return {"status": "success", "message": "Production backend running!"}

# Prevent app.run() from triggering when Gunicorn imports the module
if __name__ == "__main__":
    # ONLY used for local fallback testing, not production
    app.run(host="0.0.0.0", port=5000)
```

---

## 2. Setting Up Gunicorn WSGI Server

Gunicorn will start multiple worker processes to handle incoming requests concurrently. It communicates locally with Nginx using a Unix domain socket.

### 2.1. Install Gunicorn
First, install Gunicorn in your python virtual environment:
```bash
cd /home/example-user/BackendServer/Flask-App
source .venv/bin/activate
pip install gunicorn
```

### 2.2. Create Systemd Service File
To run Gunicorn in the background and ensure it automatically restarts on crash or server boot, configure a systemd service.

Create the service file:
```bash
sudo nano /etc/systemd/system/my_flask_api.service
```

Add the following content (adjusting paths and users based on your local configurations):
```ini
[Unit]
Description=Gunicorn instance to serve dev.example.com API
After=network.target

[Service]
User=example-user
Group=www-data
WorkingDirectory=/home/example-user/BackendServer/Flask-App
Environment="PATH=/home/example-user/BackendServer/Flask-App/.venv/bin"
ExecStart=/home/example-user/BackendServer/Flask-App/.venv/bin/gunicorn \
          --workers 3 \
          --bind unix:/tmp/flask_api.sock \
          -m 007 \
          app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

#### Directive Explanations:
- `User`: Runs as your local server account.
- `Group=www-data`: The group ownership matches the Nginx service group. This is required so Nginx has permission to read/write to the Gunicorn socket.
- `workers 3`: Standard calculation: `(2 * Cores) + 1`. Adjust based on your server capacity.
- `bind unix:/tmp/flask_api.sock`: Instructs Gunicorn to listen on a high-performance local Unix socket.
- `-m 007`: Sets the file permission of the socket so only Gunicorn and Nginx (`www-data` group) can access it.
- `app:app`: Directs Gunicorn to load the variable `app` from file `app.py`.

---

## 3. Controlling Gunicorn Service

After saving the service file, manage it using the standard systemd commands:

```bash
# 1. Reload systemd to detect the new service file
sudo systemctl daemon-reload

# 2. Start the service
sudo systemctl start my_flask_api.service

# 3. Enable the service to run on server boot
sudo systemctl enable my_flask_api.service

# 4. Check that the service is running successfully
sudo systemctl status my_flask_api.service
```

### Viewing Logs:
If Gunicorn encounters Python errors or fails to start, read the logs directly:
```bash
sudo journalctl -u my_flask_api.service -n 50 --no-pager
```

---

## 4. Connecting Nginx to Gunicorn

Now, update Nginx to route external requests hitting `dev.example.com` to Gunicorn's Unix socket file.

### 4.1. Server Block Location
Edit your subdomain configuration file:
```bash
sudo nano /etc/nginx/sites-available/dev.example.com
```

### 4.2. Location Setup
Ensure the location block points to your Gunicorn socket:
```nginx
server {
    listen 443 ssl;
    server_name dev.example.com;

    # SSL Configs go here...

    location / {
        # Connect Nginx to Gunicorn Unix socket
        proxy_pass http://unix:/tmp/flask_api.sock;
        
        # Standard proxy headers
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # Forward actual client connection details to Flask
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;

        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
        send_timeout 300s;
    }
}
```

For configuration patterns details, check the template file [nginx.conf.template](./nginx.conf.template).

### 4.3. Test & Deploy Nginx Changes
Validate the syntax first:
```bash
sudo nginx -t
```
If successful, reload Nginx:
```bash
sudo systemctl reload nginx
```
*(You can also use the workspace skill cheat sheet for helper commands: [nginx_setup Skill](../.agents/skills/nginx_setup/SKILL.md)).*
