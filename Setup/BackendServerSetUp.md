# Setting Up a Homeserver as a Backend Server

This guide outlines the steps to configure a homeserver as a backend server, including Nginx setup for reverse proxying and SSL, Gunicorn as a production WSGI server for Flask, Dynamic DNS (DDNS) configuration, and Certbot for Let's Encrypt SSL certificates.

## 0. Overview: Request Flow Direction

The following diagram and explanation outline the flow of a typical web request from a client to the production Flask application running with Gunicorn:

1. **Web Request (Flask) at Domain:**
   A user sends a request to the public domain (e.g., `https://{SUBDOMAIN}.{DOMAIN NAME}`).

2. **Hostinger (DNS):**
   The domain's DNS records (managed at Hostinger) point the domain or subdomain to the Dynamic DNS (DDNS) hostname. (e.g., `{SUBDOMAIN}.{DOMAIN NAME}` -> `{DDNS HOST NAME}`).

3. **Dynamic DNS (DDNS):**
   The DDNS provider (e.g., No-IP) keeps the hostname updated with the current public IP address of the homeserver. (e.g., `{DDNS HOST NAME}`).

4. **Router (External Port):**
   The router receives the request on the forwarded external port (e.g., 443 for HTTPS) and forwards it to the server's internal IP and port. (e.g., `{DDNS HOST NAME}:443` -> `{ROUTER}:443`).

5. **Server (Internal Port, Nginx):**
   The Ubuntu server running Nginx receives the request on the internal port. Nginx acts as a reverse proxy, handling SSL termination and forwarding the request. (e.g., `{ROUTER}:443`  -> `{INTERNAL_IP}:{INTERNAL_PORT}`).

6. **Production App (Gunicorn):**
   Nginx proxies the request to the Gunicorn WSGI server via a Unix socket. Gunicorn serves the Flask application in production mode. (e.g., `unix:/tmp/my_flask_api.sock`).

7. **Flask Code (Backend Server):**
   Gunicorn runs the actual Flask backend application code, which processes the request and returns a response. (e.g., `app:app` in `app.py`).

**Flow Summary:**
Client → Hostinger DNS → DDNS → Router (Port Forwarding) → Server (Nginx) → Gunicorn → Flask App

## 1. Nginx Installation and Configuration

Nginx is used as a reverse proxy to direct incoming traffic to a Flask application and to handle SSL termination.

### 1.1. Install Nginx

First, update the package list and install Nginx:

```bash
sudo apt update
sudo apt install nginx
```

### 1.2. Nginx Server Block Configuration

Create a new Nginx server block configuration file for ```{DOMAIN NAME}```. This configuration handles HTTP to HTTPS redirection and proxies requests to the Flask application running on ```localhost:{INTERNAL_PORT}```.

The configuration file ```/etc/nginx/sites-available/{DOMAIN NAME}``` should contain:

```nginx
# This block handles HTTP requests on port {HTTP_REDIRECT_PORT}
# It redirects them to the new HTTPS (port {HTTPS_PORT}) server block.
# If the ISP blocks port {HTTPS_PORT}, this redirect won't work externally.
server {
    listen {HTTP_REDIRECT_PORT}; # Current working HTTP port
    server_name {DOMAIN NAME};

    # Redirect all HTTP traffic on port {HTTP_REDIRECT_PORT} to HTTPS on default port {HTTPS_PORT}
    return 301 https://$host$request_uri;
}

# This is the NEW server block for HTTPS traffic
server {
    listen {HTTPS_PORT} ssl;          # Nginx listens for HTTPS connections on standard port {HTTPS_PORT}
    listen [::]:{HTTPS_PORT} ssl;     # For IPv6, if applicable
    server_name {DOMAIN NAME};

    # Paths to Let's Encrypt SSL certificate files
    # These paths are where Certbot saves the certificates after the DNS challenge.
    ssl_certificate /etc/letsencrypt/live/{DOMAIN NAME}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{DOMAIN NAME}/privkey.pem;

    # Recommended SSL settings for security and performance
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers on;

    # Proxy_pass configuration to the Flask app
    location / {
        proxy_pass http://localhost:{INTERNAL_PORT}; # Flask app's internal port
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;

        # Add these headers for proper proxying with SSL, they help Flask understand the original request details
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 1.3. Enable and Restart Nginx

After creating the configuration file, create a symbolic link to enable it, test the Nginx configuration, and then restart the Nginx service:

```bash
sudo ln -s /etc/nginx/sites-available/{DOMAIN NAME} /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 2. Dynamic DNS (DDNS) Setup with No-IP

Since most residential internet connections have dynamic IP addresses, a DDNS service is essential to ensure the domain always points to the homeserver's current public IP. No-IP is used for this purpose.

### 2.1. Choose and Set Up a Third-Party DDNS Provider (No-IP)

1. **Create a No-IP Account:** Go to noip.com and sign up for a free account.

2. **Create a Hostname:** Log in to the No-IP dashboard.
    - Navigate to the "Dynamic DNS" section and click "Create Hostname".
    - Hostname: Choose a name (e.g., ```{DDNS HOST NAME}```).
    - Domain: Select a free domain option.
    - The full DDNS hostname will be something like ```{DDNS HOST NAME}```. The IP address field will be automatically filled.
    - Click "Create Hostname".
    - **Important:** Free No-IP accounts require hostname confirmation every 30 days via email.

### 2.2. Install and Configure the DDNS Client on the Ubuntu Server

Install the No-IP Dynamic Update Client (DUC) on the Ubuntu server to automatically update the IP address with No-IP.

```bash
# Navigate to a temporary directory
cd /tmp/
# Download the client software
sudo wget http://www.no-ip.com/client/linux/noip-duc-linux.tar.gz
# Unpack the downloaded file
sudo tar xf noip-duc-linux.tar.gz
# Navigate into the new directory
cd noip-2.1.9-1/
# Compile and install the client
sudo make install
```

During installation, the setup will prompt for No-IP account credentials:

-   Enter the No-IP email address and password.
-   The default update interval (30 minutes) is usually sufficient.
-   Press Enter for 'N' (No) when asked to run a script on a successful update.

The No-IP client will launch after configuration and keep the ```{DDNS HOST NAME}``` hostname updated.

## 3. DNS Configuration (Hostinger)

This step involves configuring the domain's DNS records to point to the homeserver.

### 3.1. Point the Subdomain to the Home's Public IP

Configure an A record in the Hostinger DNS settings for ```{DOMAIN NAME}```.

1. **Find the Public IP:** Find the public IP address by searching "what is my IP" on Google.

2. **Log in to Hostinger:** Go to the Hostinger dashboard.

3. **Navigate to DNS Zone Editor:** Find the DNS settings for the main domain.

4. **Create a New A Record:**
    - Type: ```A```
    - Name: ```{SUBDOMAIN}```
    - Points to: ```{DDNS HOST NAME}``` (the DDNS hostname)
    - TTL: Leave as default (or set a low value like 300 seconds if IP changes are anticipated).

Note: Most residential internet connections have a dynamic IP address. Using a DDNS service like ```{DDNS HOST NAME}``` ensures the domain always points to the current public IP.

## 4. Router Port Forwarding

The router needs to be configured to direct incoming web traffic (HTTP and HTTPS) to the Ubuntu server's local IP address. For example, the Ubuntu server's local IP might be ```{INTERNAL_IP}```.

### 4.1. Access the Router's Settings

This typically involves typing the router's IP address (e.g., ```192.168.1.1``` or ```192.168.0.1```) into a web browser.

### 4.2. Configure Port Forwarding Rules

Locate the "Port Forwarding," "Virtual Servers," or "Applications & Gaming" section in the router's settings and create the following rules:

-   Rule 1 (HTTP Redirect):
    -   Service/Application Name: ```HTTP_REDIRECT```
    -   External Port: ```{HTTP_REDIRECT_PORT}```
    -   Internal Port: ```{HTTP_REDIRECT_PORT}```
    -   Protocol: ```TCP```
    -   Device/Internal IP: ```{INTERNAL_IP}```

-   Rule 2 (HTTPS):
    -   Service/Application Name: ```HTTPS```
    -   External Port: ```443```
    -   Internal Port: ```443```
    -   Protocol: ```TCP```
    -   Device/Internal IP: ```{INTERNAL_IP}```

-   Rule 3 (HTTP - Optional, if not handled by Nginx redirect):
    -   Service/Application Name: ```HTTP```
    -   External Port: ```80```
    -   Internal Port: ```80```
    -   Protocol: ```TCP```
    -   Device/Internal IP: ```{INTERNAL_IP}```
    -   Note: The Nginx configuration's redirect from port ```{HTTP_REDIRECT_PORT}``` to ```443``` means direct external access to port ```80``` might not be necessary if {HTTP_REDIRECT_PORT} is the primary entry point for HTTP before redirection. However, forwarding ```80``` is good practice if any external services might try to access it directly.

## 5. Obtaining SSL Certificates with Certbot (DNS Challenge)

Certbot with the DNS challenge can be used to obtain SSL certificates from Let's Encrypt, which is crucial for securing HTTPS traffic. This method is recommended when the server isn't directly exposed on ports {HTTP_PORT}/{HTTPS_PORT} for validation or when using a wildcard certificate.

### 5.1. Run Certbot with the DNS Challenge Command

On the server, execute the following command to instruct Certbot to use the manual DNS challenge:

```bash
sudo certbot certonly --manual --preferred-challenges dns -d {DOMAIN NAME}
```

Certbot will pause and provide a ```TXT``` record name (e.g., ```_acme-challenge.dev```) and a unique value.

### 5.2. Add the TXT Record to the DNS Management Interface

This step is critical for proving ownership of the domain.

1. **Log in to the domain registrar's website or DNS hosting provider's control panel** (e.g., Hostinger).
2. **Navigate to the DNS management section for ```{DOMAIN NAME}```**.
3. **Add a new DNS record with the details provided by Certbot:**
    -   Type: ```TXT```
    -   Name/Host/Subdomain: Enter the exact hostname Certbot provides (e.g., ```_acme-challenge.dev```).
        -   Example: If Certbot gives ```_acme-challenge.dev.{DOMAIN NAME}```, and the DNS provider has a field specifically for the subdomain part, enter ```_acme-challenge.dev```. If it's a full "host" field, paste the entire value.
    -   Value/Target/Text: Enter the unique long string provided by Certbot (e.g., ```YOUR_NEW_UNIQUE_LONG_STRING_HERE_PROVIDED_BY_CERTBOT```).
    -   TTL (Time To Live): Set this to a low value (e.g., 300 seconds or 5 minutes) to speed up propagation.

After adding the TXT record, return to the server and press Enter to allow Certbot to verify the record and issue the SSL certificate.

Following these steps ensures that the homeserver is accessible via a custom domain with secure HTTPS connections, providing a robust backend for applications.

## 6. Setting Up Gunicorn
Running your Flask application with app.run() is only suitable for development. For production, you need a robust WSGI server like Gunicorn.

### 6.1. Install Gunicorn
First, install Gunicorn, preferably within your Flask project's virtual environment.

```bash
cd /path/to/your/flask/app # Navigate to your project directory
source venv/bin/activate    # Activate your virtual environment
pip install gunicorn
deactivate                  # Deactivate when done
```

### 6.2. Modify Your Flask App for Gunicorn
Gunicorn will directly import your Flask application instance. You should remove or comment out the ```app.run()``` line that you use for local development.

Example ```app.py``` modification:
```python
from flask import Flask

app = Flask(__name__) # This 'app' instance is what Gunicorn will look for

@app.route('/')
def hello_world():
    return 'Hello World from Production Flask App!'

# Remove or comment out this block for production deployment with Gunicorn
# if __name__ == '__main__':
#    app.run(host="0.0.0.0", port={INTERNAL_PORT}, debug=True)
```

### 6.3. Create a Systemd Service File for Gunicorn
This file tells systemd how to run and manage your Gunicorn process, ensuring it starts automatically on boot and recovers if it crashes.

1. **Create the service file:**
```bash
sudo nano /etc/systemd/system/my_flask_api.service # Choose a descriptive name, e.g., my_flask_api.service
```
2. **Add the following content, making sure to replace the placeholders:**
```ini
[Unit]
Description=Gunicorn instance for my Flask app
After=network.target

[Service]
User=your_username
# REPLACE: Your non-root server username

Group=www-data
# Specific Group for Nginx/web server access (No Need to Replace)

WorkingDirectory=/path/to/your/flask/app_dir
# REPLACE: Absolute path to your Flask project directory (e.g., /home/user/my_flask_api)

Environment="PATH=/path/to/your/venv/bin"
# REPLACE: Absolute path to your virtual environment's 'bin' directory (e.g., /home/user/my_flask_api/venv/bin)

ExecStart=/path/to/your/venv/bin/gunicorn --workers 4 --bind unix:/tmp/my_flask_api.sock -m 007 app:app
# REPLACE (/path/to/your/venv/bin/gunicorn): Path to gunicorn executable in your venv
# REPLACE (/tmp/my_flask_api.sock): A unique name for your Unix socket file
# 'app:app' means Gunicorn looks for 'app' instance in 'app.py' (change if your main file/instance name differs)

# Explanation of ExecStart:
# --workers 4: (Adjust based on CPU cores, typically 2*CPU_CORES + 1)
# --bind unix:/tmp/my_flask_api.sock: Gunicorn listens on a Unix socket (more efficient than TCP port for local comms)
# -m 007: Sets permissions on the socket for Nginx to access
# app:app: Tells Gunicorn to look for the 'app' variable in the 'app.py' file
Restart=always

[Install]
WantedBy=multi-user.target
```

### 6.4. Enable and Start the Gunicorn Service
After saving the service file:

1. **Reload the systemd daemon: This makes systemd aware of your new or modified service file.**
```bash
sudo systemctl daemon-reload
```

2. **Enable the service:** This ensures Gunicorn starts automatically every time your server boots.
```bash
sudo systemctl enable my_flask_api.service
```

3. **Start the Gunicorn service:** Get your Gunicorn application running immediately.
```bash
sudo systemctl start my_flask_api.service
```

4. **Check the status:** Verify that Gunicorn is running correctly.
```bash
sudo systemctl status my_flask_api.service
```

## 7. Modifying Nginx for Gunicorn Proxy
We will need to point Nginx to the Gunicorn socket instead of the Flask development server. Modify the Nginx server block configuration for ```{DOMAIN NAME}``` to use the Unix socket created by Gunicorn.

1. **Edit your Nginx server block configuration file:**
```bash
sudo nano /etc/nginx/sites-available/{DOMAIN NAME}
```

2. **Update the `location /` block to proxy to the Gunicorn socket:**
```nginx
location / {
    proxy_pass http://unix:/tmp/my_flask_api.sock; # Pointing to the Gunicorn socket
}
```
- proxy_pass ```http://unix:/tmp/my_flask_api.sock;```: Make sure this path exactly matches the socket name you configured in your Gunicorn ```systemd``` service file.

3. **Test the Nginx configuration and reload Nginx:**
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## 8. Testing the Setup

After completing the setup, it's essential to test the configuration to ensure everything is working correctly.

### 8.1. Check Nginx Configuration

Run the following command to check the Nginx configuration for any errors:
```bash
sudo nginx -t
```
If there are no errors, you should see a message indicating that the configuration is successful.

### 8.2. Check Gunicorn Service
Check the status of the Gunicorn service to ensure it is running without issues:
```bash
sudo systemctl status my_flask_api.service
```
If the service is active and running, it indicates that Gunicorn has started successfully.
If there are any issues, check the logs for more details:
```bash
sudo journalctl -u my_flask_api.service
```

### 8.3. Test the Domain

Open a web browser and navigate to `https://{DOMAIN NAME}`. You should see the Flask application running, and the connection should be secure (indicated by a padlock icon in the address bar).
-   This should point to the Flask application running on port {INTERNAL_PORT} (```http://unix:tmp/my_flask_api.sock```), as configured in the Nginx server block.

### 8.4. Verify SSL Certificate

You can verify the SSL certificate by clicking on the padlock icon in the browser's address bar. Ensure that the certificate is issued by Let's Encrypt and is valid.

## 9. Troubleshooting Common Issues

### 9.1. Nginx Not Starting

If Nginx fails to start, check the error logs for details:
```bash
sudo journalctl -xe
```
Look for any errors related to the configuration file or SSL certificates.

### 9.2. SSL Certificate Issues

If you encounter issues with the SSL certificate, ensure that:
- The certificate files exist at the specified paths.
- The DNS TXT record was correctly added and propagated.
You can use tools like [SSL Labs](https://www.ssllabs.com/ssltest/) to test your SSL configuration.

### 9.3. DDNS Not Updating

If the DDNS hostname is not updating with your current public IP, check the No-IP client logs:
```bash
cat /var/log/noip2.log
```
Ensure that the client is running and that it has the correct credentials. You can also manually trigger an update with:
```bash
sudo noip2 -c /usr/local/etc/no-ip2.conf
```

### 9.4. Port Forwarding Issues

If you cannot access the server from outside your local network, ensure that:
- The port forwarding rules are correctly set up in the router.
- The router's firewall is not blocking the forwarded ports.
- The server's firewall (if enabled) allows incoming traffic on the relevant ports.

## 10. Conclusion

Setting up a homeserver as a backend server involves configuring Nginx for reverse proxying and SSL, setting up Dynamic DNS with No-IP, and obtaining SSL certificates using Certbot. By following this guide, you can ensure that your homeserver is accessible securely over the internet, providing a reliable backend for your applications.

## 11. Additional Resources

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Certbot Documentation](https://certbot.eff.org/docs/)
- [No-IP Dynamic Update Client](https://www.noip.com/support/knowledgebase/installing-the-no-ip-linux-dynamic-update-client/)
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Hostinger DNS Management](https://www.hostinger.com/tutorials/how-to-manage-dns-records)

## 12. Maintenance and Updates

Regularly check for updates to Nginx, Certbot, and the No-IP client to ensure security and functionality. Monitor the server logs for any issues and renew SSL certificates as needed (Certbot can automate this with a cron job).

**Note:** Replace all placeholders such as `{DOMAIN NAME}`, `{INTERNAL_PORT}`, `{INTERNAL_IP}`, `{DDNS HOST NAME}`, `{SUBDOMAIN}`, and `your_username` with actual values before applying these instructions.
