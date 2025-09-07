#!/usr/bin/env python3

from flask import Flask
from flask_cors import CORS
from WeddingInvitations.rsvp import rsvp_endpoint
from NextdoorScraper.nextdoor_scraper import scrape_nextdoor_posts_endpoint
from TutoringCalc.calc_pay import calc_tutoring_pay_endpoint

app = Flask(__name__)
CORS(app)

def hello_world():
    return "Welcome to Stephen Giang's Server!"

app.add_url_rule("/", "hello_world", hello_world)

app.add_url_rule("/rsvp", "rsvp", rsvp_endpoint, methods=["POST"])

app.add_url_rule("/scrape-nextdoor-posts", "scrape_nextdoor_posts_endpoint", scrape_nextdoor_posts_endpoint, methods=["GET"])

app.add_url_rule("/calc-tutoring-pay", "calc_tutoring_pay_endpoint", calc_tutoring_pay_endpoint, methods=["GET"])

if __name__ == "__main__":
    app.run(debug=True)
