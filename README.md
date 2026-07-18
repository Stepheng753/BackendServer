# Backend Server

This directory contains resources for deploying and managing a general-purpose backend server.

## Setup Guides

Deployment instructions are split into two documents:

1. **[ServerSetUp.md](./Setup/ServerSetUp.md)**: Details the network/server-level infrastructure including TP-Link Deco DDNS, port forwarding, Hostinger DNS/subdomain setup, and Let's Encrypt manual DNS challenge.
2. **[BackendSetUp.md](./Setup/BackendSetUp.md)**: Details backend application deployment using Gunicorn and Nginx reverse proxying to a local Unix socket.

### Supplemental Configuration & Assets

- **[setup.conf](./Setup/setup.conf)**: Local configuration values (server IPs, ports, DDNS hostname, active subdomains). *Note: This file is ignored by Git to prevent leak of internal configurations.*
- **[nginx.conf.template](./Setup/nginx.conf.template)**: Configuration blueprints for reverse-proxying with Nginx (Unix sockets, TCP ports, and static frontend assets).
- **[nginx_setup Skill](./.agents/skills/nginx_setup/SKILL.md)**: Agent-facing workspace skill specifying systemd, certbot, and Nginx validation procedures.

## Flask-App

The **[Flask-App](./Flask-App/)** directory serves as the centralized backend codebase. It implements a general Flask application structure that can be run with Gunicorn in production mode.

---

For detailed instructions, refer to **[ServerSetUp.md](./Setup/ServerSetUp.md)** for network mapping and **[BackendSetUp.md](./Setup/BackendSetUp.md)** for application installation.