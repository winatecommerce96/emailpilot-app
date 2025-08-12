"""
Google service for handling Google API integrations
"""

import logging
from typing import Optional, Dict, Any
import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

class GoogleService:
    def __init__(self):
        self.docs_api_url = "https://docs.googleapis.com/v1/documents"
        self.drive_api_url = "https://www.googleapis.com/drive/v3/files"

    async def get_document_content(self, doc_id: str, access_token: str) -> Optional[str]:
        """
        Extract text content from Google Docs document
        """
        try:
            # Build credentials from access token
            creds = Credentials(token=access_token)
            
            # Build the service
            service = build('docs', 'v1', credentials=creds)
            
            # Get the document
            document = service.documents().get(documentId=doc_id).execute()
            
            # Extract text content
            text_content = self._extract_text_from_document(document.get('body', {}).get('content', []))
            
            logger.info(f"Extracted {len(text_content)} characters from document {doc_id}")
            
            return text_content
            
        except Exception as e:
            logger.error(f"Error fetching Google Doc content: {e}")
            return None

    def _extract_text_from_document(self, content: list) -> str:
        """
        Recursively extract text from Google Docs content structure
        """
        text = ""
        
        for element in content:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                for paragraph_element in paragraph.get('elements', []):
                    if 'textRun' in paragraph_element:
                        text += paragraph_element['textRun'].get('content', '')
                        
            elif 'table' in element:
                table = element['table']
                for row in table.get('tableRows', []):
                    for cell in row.get('tableCells', []):
                        cell_content = cell.get('content', [])
                        text += self._extract_text_from_document(cell_content)
                        
            elif 'sectionBreak' in element:
                text += "\n"
        
        return text

    async def verify_document_access(self, doc_id: str, access_token: str) -> bool:
        """
        Verify that the document exists and is accessible
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                f"{self.docs_api_url}/{doc_id}",
                headers=headers,
                params={'fields': 'documentId,title'}
            )
            
            if response.status_code == 200:
                doc_info = response.json()
                logger.info(f"Document accessible: {doc_info.get('title', 'Untitled')}")
                return True
            else:
                logger.error(f"Document access failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error verifying document access: {e}")
            return False

    async def get_document_metadata(self, doc_id: str, access_token: str) -> Optional[Dict[str, Any]]:
        """
        Get document metadata (title, last modified, etc.)
        """
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                f"{self.docs_api_url}/{doc_id}",
                headers=headers,
                params={'fields': 'documentId,title,revisionId'}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get document metadata: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting document metadata: {e}")
            return None