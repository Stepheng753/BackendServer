from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import os.path
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

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                creds = None  # Force re-authentication

        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(OAUTH_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open(TOKEN_PICKLE_FILE, 'wb') as token:
            pickle.dump(creds, token)

    return creds
