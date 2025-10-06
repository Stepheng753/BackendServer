from flask import request, redirect, url_for
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import os
import pickle
from .helpers import get_absolute_path

OAUTH_FILE = get_absolute_path('../keys/oauth-acc-api-key.json')
TOKEN_PICKLE_FILE = get_absolute_path('../keys/token.pickle')
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar'
]

def get_credentials():
    """Gets valid user credentials from storage or initiates OAuth2 flow."""
    creds = None
    if os.path.exists(TOKEN_PICKLE_FILE):
        with open(TOKEN_PICKLE_FILE, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                creds = None  # Force re-authentication

    return creds


def initiate_oauth_flow(redirect_uri, final_redirect=None):
    """
    Generates the authorization URL for the OAuth flow.
    The user's browser should be redirected to this URL.
    """
    flow = InstalledAppFlow.from_client_secrets_file(OAUTH_FILE, SCOPES)
    flow.redirect_uri = redirect_uri
    authorization_url, _ = flow.authorization_url(prompt='consent', state=final_redirect)
    return authorization_url


def process_oauth_callback(redirect_uri, authorization_response):
    """
    Processes the callback from Google, fetches the token, and saves it.
    """
    flow = InstalledAppFlow.from_client_secrets_file(OAUTH_FILE, SCOPES)
    flow.redirect_uri = redirect_uri

    flow.fetch_token(authorization_response=authorization_response)
    creds = flow.credentials

    with open(TOKEN_PICKLE_FILE, 'wb') as token:
        pickle.dump(creds, token)


def login_oauth(final_redirect='index'):
    """
    Handles both starting the OAuth 2.0 flow and processing the callback.
    final_redirect may be an endpoint name or a full URL.
    """
    if 'code' in request.args:
        redirect_uri = url_for('login_oauth', _external=True)
        process_oauth_callback(redirect_uri, request.url)
        state = request.args.get('state') or final_redirect
        return redirect(url_for(state))

    redirect_uri = url_for('login_oauth', _external=True)
    auth_url = initiate_oauth_flow(redirect_uri, final_redirect)
    return redirect(auth_url)
