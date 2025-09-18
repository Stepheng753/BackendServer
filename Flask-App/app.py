#!/usr/bin/env python3

from flask import Flask
from flask_cors import CORS
from index.index import render_endpoints, check_auth
from WeddingInvitations.rsvp import rsvp_endpoint
from NextdoorScraper.nextdoor_scraper import scrape_nextdoor_posts_endpoint, get_log_file
from TutoringCalc.calc_pay import calc_tutoring_pay_endpoint

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

app.add_url_rule("/rsvp", "rsvp", rsvp_endpoint, methods=["POST"])

app.add_url_rule("/scrape-nextdoor-posts", "scrape_nextdoor_posts_endpoint", scrape_nextdoor_posts_endpoint, methods=["GET"])

app.add_url_rule("/get-nextdoor-log", "get_nextdoor_log", get_log_file, methods=["GET"])

app.add_url_rule("/calc-tutoring-pay", "calc_tutoring_pay_endpoint", calc_tutoring_pay_endpoint, methods=["GET"])