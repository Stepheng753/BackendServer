#!/usr/bin/env python3

import os
from flask import Flask
from flask_cors import CORS
from index.index import render_endpoints, check_auth

app = Flask(__name__, template_folder='index', static_folder='static')
CORS(app)

@app.before_request
def auth():
    return check_auth()

@app.route("/")
def index():
    return render_endpoints(app)

@app.route("/test")
def test():
    return {"status": "success", "message": "Hello, World!"}