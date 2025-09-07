import json
from googleapiclient.discovery import build
from .helpers import *


def get_drive_service(creds):
    """Builds and returns the Google Drive service."""
    return build('drive', 'v3', credentials=creds)


def get_drive_id():
    """Gets the folder ID from the drive-id.json file."""
    with open(ID_FILE, 'r') as file:
        data = json.load(file)
        return data['drive_id']


def copy_file(service, source_file_id, new_name, destination_folder_id):
    """
    Copies a file to a specified folder with a new name.
    If a file with the same name already exists in the destination, it is
    overwritten.
    """
    existing_file_id = get_file_id(service, new_name, parent_id=destination_folder_id)

    if existing_file_id:
        print(f"File '{new_name}' already exists. Overwriting.")
        service.files().delete(fileId=existing_file_id).execute()

    file_metadata = {
        'name': new_name,
        'parents': [destination_folder_id]
    }

    copied_file = service.files().copy(
        fileId=source_file_id, body=file_metadata
    ).execute()

    return copied_file


def get_file_id(service, file_name, parent_id=None):
    """Retrieves the file ID of a file given its name and optional parent folder."""
    query = f"name='{file_name}' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(
        q=query, spaces='drive', fields='files(id, name)', pageSize=1
    ).execute()
    items = results.get('files', [])

    if len(items) == 0:
        return None

    return items[0]['id']