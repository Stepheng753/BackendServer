from flask import url_for, render_template, request, make_response
import base64
import os
from dotenv import load_dotenv

load_dotenv()


def render_endpoints(app):
    """
    Renders a welcome page with a list of all available endpoints.
    """
    endpoints_data = []
    exclude_endpoints = {'static', 'index', 'login_oauth'}
    # Iterate over all registered URL rules in the application
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        # We don't need to show the static endpoint
        if rule.endpoint not in exclude_endpoints:
            # Get the HTTP methods allowed for the endpoint, excluding HEAD and OPTIONS for brevity
            methods = sorted(rule.methods - {'HEAD', 'OPTIONS'})

            # Create a dictionary for each endpoint to pass to the template
            endpoints_data.append({
                'rule': rule.rule,
                'url': url_for(rule.endpoint, _external=True),
                'methods': methods
            })

    return render_template(
        'index.html',
        title="Flash Server",
        favicon_url=url_for('static', filename='flash.png'),
        image_url=url_for('static', filename='flash.gif'),
        endpoints=endpoints_data
    )


def check_auth():
    # Allow access to the root endpoint and static files without authentication
    if request.path.startswith('/static/'):
        return

    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Basic '):
        return make_response('Could not verify!', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

    auth_bytes = auth_header.split(' ')[1].encode('ascii')
    try:
        decoded_bytes = base64.b64decode(auth_bytes)
        decoded_string = decoded_bytes.decode('ascii')
        username, password = decoded_string.split(':', 1)
    except (base64.binascii.Error, ValueError):
        return make_response('Invalid authorization header.', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

    if username.lower() != os.getenv("USERNAME").lower() or password != os.getenv("PASSWORD"):
        return make_response('Could not verify!', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

    return None
