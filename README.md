# Backend Server

This directory contains resources for deploying and managing a general-purpose Flask backend server.

## `BackendServerSetUp.md`

The `BackendServerSetUp.md` file provides a comprehensive, step-by-step guide for configuring a secure and production-ready backend server environment. It covers:

- Setting up Nginx as a reverse proxy and SSL terminator
- Deploying Flask applications with Gunicorn as the WSGI server
- Configuring Dynamic DNS (DDNS) for reliable remote access
- Obtaining and renewing SSL certificates with Let's Encrypt and Certbot
- Testing and troubleshooting the deployment

This guide is designed to help set up a robust backend server suitable for a variety of Flask-based projects.

## `Flask-App`

The `Flask-App` directory serves as an all-in-one backend server, providing a general Flask application that can be used to run computations or handle backend logic for any web project.
This setup allows multiple web projects to leverage a single, centralized Flask backend for processing and API needs.

You can place your Flask project code inside this directory and follow the setup instructions in `BackendServerSetUp.md` to deploy it as needed.

---

For detailed setup and deployment instructions, refer to [BackendServerSetUp.md](./Setup/BackendServerSetUp.md).