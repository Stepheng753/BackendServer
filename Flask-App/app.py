#!/usr/bin/env python3

from flask import Flask, request, jsonify
from flask_cors import CORS
from WeddingInvitations.rsvp import rsvp
from NextdoorScraper.nextDoorScraper import scrape_nextdoor_posts

app = Flask(__name__)
CORS(app)

@app.before_request
def before_request():
    headers = {'Access-Control-Allow-Origin': '*',
               'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
               'Access-Control-Allow-Headers': 'Content-Type',
               'Test-Header': 'Test-Value'}
    if request.method.lower() == 'options':
        return jsonify(headers), 200


def hello_world():
    return 'Welcome to my Server!'

@app.route("/scrape-nextdoor", methods=["GET"])
async def scrape_nextdoor():
    await scrape_nextdoor_posts()
    return jsonify({"status": "success"})

app.add_url_rule("/", "hello_world", hello_world)
app.add_url_rule("/rsvp", "rsvp", rsvp, methods=["POST"])


if __name__ == "__main__":
    app.run(debug=True)
