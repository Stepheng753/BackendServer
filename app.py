#!/usr/bin/env python3
import os

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

from flask import Flask
from flask_cors import CORS
from index.index import check_auth
from swagger.swagger import swagger_bp
from TutoringCalculator.routes import tutoring_bp

app = Flask(__name__)
CORS(app)

# Register Swagger documentation UI & OpenAPI spec
app.register_blueprint(swagger_bp)

# Register Tutoring Calculator endpoints (both top-level and with /TutoringCalculator prefix)
app.register_blueprint(tutoring_bp)
app.register_blueprint(tutoring_bp, name='tutoring_calculator', url_prefix='/TutoringCalculator')


@app.before_request
def auth():
    return check_auth()


@app.route("/test")
def test():
    return {"status": "success", "message": "Hello, World!"}


if __name__ == "__main__":
    from TutoringCalculator.config import CONFIG
    port = int(os.environ.get("PORT", CONFIG.get("PORT", 5000)))
    app.run(host="0.0.0.0", port=port, debug=True)