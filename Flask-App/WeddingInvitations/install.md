python -m venv venv
source venv/bin/activate

pip install Flask Flask-Cors gunicorn
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib gspread
pip install pytz