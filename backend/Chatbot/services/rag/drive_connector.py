import os
import io
from google.oauth2.service_account import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import PyPDF2
import docx
from bs4 import BeautifulSoup

from Chatbot.core.config import settings

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

class DriveConnector:
    def __init__(self, credentials_path: str = "credentials.json"):
        self.credentials_path = credentials_path
        self.service = self._authenticate()

    def _authenticate(self):
        """Authenticate with Google Drive API."""
        creds = None
        # In a real scenario, handle OAuth2 tokens or service account properly.
        # Here we mock it if the file doesn't exist so the backend can still run.
        if not os.path.exists(self.credentials_path):
            print(f"WARNING: {self.credentials_path} not found. Drive connection will operate in mock mode.")
            return None

        from google.oauth2.credentials import Credentials as OAuthCreds
        if os.path.exists('token.json'):
            creds = OAuthCreds.from_authorized_user_file('token.json', SCOPES)
            
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        try:
            service = build('drive', 'v3', credentials=creds)
            return service
        except Exception as e:
            print(f"Failed to build Drive service: {e}")
            return None

    def list_files_in_folder(self, folder_id: str, max_results: int = 10):
        if not self.service:
            print("Mock: listing files for folder", folder_id)
            return [{"id": "mock_id_1", "name": "Mock Policy.pdf", "mimeType": "application/pdf"}]

        query = f"'{folder_id}' in parents and trashed=false"
        results = self.service.files().list(
            q=query, pageSize=max_results, fields="nextPageToken, files(id, name, mimeType, webViewLink)"
        ).execute()
        return results.get('files', [])

    def download_file(self, file_id: str, mime_type: str) -> bytes:
        if not self.service:
            return b"Mock file content for testing text extraction from a dummy PDF/Docx."

        if mime_type.startswith('application/vnd.google-apps'):
            # It's a Google Workspace document, need to export it
            export_mime = 'application/pdf'
            if 'document' in mime_type:
                export_mime = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            
            request = self.service.files().export_media(fileId=file_id, mimeType=export_mime)
        else:
            # Regular file (like an uploaded PDF or DOCX)
            request = self.service.files().get_media(fileId=file_id)
            
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()

def extract_text(file_content: bytes, mime_type: str) -> str:
    """Extracts text from PDF or DOCX bytes."""
    text = ""
    try:
        if 'pdf' in mime_type:
            reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            for page in reader.pages:
                text += page.extract_text() + "\n"
        elif 'word' in mime_type or 'document' in mime_type:
            doc = docx.Document(io.BytesIO(file_content))
            for para in doc.paragraphs:
                text += para.text + "\n"
        elif 'html' in mime_type:
            soup = BeautifulSoup(file_content, 'html.parser')
            text = soup.get_text(separator=' ', strip=True)
        else:
            # Fallback for plain text or mock
            text = file_content.decode('utf-8', errors='ignore')
    except Exception as e:
        print(f"Error extracting text: {e}")
    return text.strip()
