import os
import pytz
PST = pytz.timezone('America/Los_Angeles')

def get_absolute_path(relative_path):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, relative_path)

ID_FILE = get_absolute_path('../keys/id.json')
DATE_SLASH_FORMAT_DBL = "%m/%d/%y"
DATE_DASH_FORMAT_DBL = "%m-%d-%y"
DATE_DOT_FORMAT_DBL = "%m.%d.%y"
DATE_SLASH_FORMAT_FULL = "%m/%d/%Y"
DATE_DASH_FORMAT_FULL = "%m-%d-%Y"
DATE_DOT_FORMAT_FULL = "%m.%d.%Y"
TIME_FORMAT = "%I:%M:%S %p"
DATETIME_FORMAT = f"{DATE_DOT_FORMAT_DBL} {TIME_FORMAT}"

DATE_FORMATS = [
    DATE_SLASH_FORMAT_DBL,
    DATE_DASH_FORMAT_DBL,
    DATE_DOT_FORMAT_DBL,
    DATE_SLASH_FORMAT_FULL,
    DATE_DASH_FORMAT_FULL,
    DATE_DOT_FORMAT_FULL
]
DATE_FORMAT = DATE_DOT_FORMAT_DBL  # Default format
