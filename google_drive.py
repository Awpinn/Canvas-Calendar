# from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
# from google.auth.transport.requests import Request
# from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.discovery import build
import io, os
from parse_apis import *

# Define the scopes required
SCOPES = ['https://www.googleapis.com/auth/drive']

# Define the path to your credentials file (generated when you set up API credentials)
CLIENT_SECRETS_FILE = 'service-secret.json'
if runningOnPi:
    CLIENT_SECRETS_FILE = '/home/noah/Documents/Calendar/service-secret.json'

FOLDER_ID = '1-I9OyEPb1CO2aa8wN2db910vD5jfghIf'

# Define the local path where you want to download the files
LOCAL_PATH = 'backgrounds/'
if runningOnPi:
    LOCAL_PATH = "/home/noah/Documents/backgrounds/"

def clear_folder(folder_path):
    files = os.listdir(folder_path)
    for file_name in files:
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            os.remove(file_path)
            
creds = service_account.Credentials.from_service_account_file(
    CLIENT_SECRETS_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

# Function to retrieve images from the given folder
def get_images_from_folder(folder_id):
    images = []
    page_token = None
    while True:
        response = drive_service.files().list(q=f"'{folder_id}' in parents and mimeType contains 'image/'", spaces='drive', fields='nextPageToken, files(id, name, modifiedTime)', pageToken=page_token).execute()
        for file in response.get('files', []): 
            images.append({'id': file['id'], 'name': file['name'], 'modifiedTime': file['modifiedTime']})
        page_token = response.get('nextPageToken', None)
        if page_token is None:
            break
    return images

# Function to download an image from Google Drive
def download_image(image_id, image_name, local_folder=LOCAL_PATH):
    request = drive_service.files().get_media(fileId=image_id)
    fh = io.FileIO(image_name, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()

def synchronize_images():
    folder_id = FOLDER_ID
    local_folder = LOCAL_PATH
    # List images in Google Drive folder
    drive_images = get_images_from_folder(folder_id)
    files_to_keep = set()
    
    for drive_image in drive_images:
        drive_image_name = drive_image['name']
        files_to_keep.add(drive_image_name)
        drive_image_modified_time = drive_image['modifiedTime']
        drive_image_modified_datetime = datetime.strptime(drive_image_modified_time, '%Y-%m-%dT%H:%M:%S.%fZ')

        local_image_path = os.path.join(local_folder, drive_image_name)
        
        # Check if the local image exists
        if os.path.exists(local_image_path):
            local_image_modified_time = os.path.getmtime(local_image_path)
            local_image_modified_datetime = datetime.utcfromtimestamp(local_image_modified_time)

            # Compare the timestamps
            if drive_image_modified_datetime > local_image_modified_datetime:
                print(f"Local image {drive_image_name} is older. Updating from Google Drive.")
                os.remove(local_image_path)
                download_image(drive_image['id'], local_image_path)
            else:
                print(f"Local image {drive_image_name} is up-to-date.")
        else:
            # Download if the local image does not exist
            print(f"Local image {drive_image_name} does not exist. Downloading from Google Drive.")
            download_image(drive_image['id'], local_image_path)
            
    for file_name in os.listdir(local_folder):
        if file_name not in files_to_keep:
            file_path = os.path.join(local_folder, file_name)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                else:
                    print(f"Skipped (not a file): {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
            
synchronize_images()