"""
Google/Gemini Service Module for Calendar Application

This module provides integration with:
- Google Docs API for document reading
- Google Sheets API for data export
- Gemini AI API for content processing and chat
- OAuth2 authentication for Google APIs
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode

import aiohttp
import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


class GoogleServiceError(Exception):
    """Custom exception for Google service errors"""
    pass


class GoogleService:
    """Service for handling Google APIs and Gemini AI integration"""
    
    # API Configuration
    GOOGLE_API_KEY = "AIzaSyAMeP8IjAfqmHAh7MeN5lpu2OpHhfRTTEg"
    GOOGLE_CLIENT_ID = "1058910766003-pqu4avth8ltclpbtpk81k0ln21dl8jue.apps.googleusercontent.com"
    GEMINI_API_KEY = "AIzaSyDZxn9-FekvRhcvRfneulDrebD0RFxUpvs"
    
    # OAuth2 Configuration
    SCOPES = [
        'https://www.googleapis.com/auth/documents.readonly',
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    
    REDIRECT_URI = 'http://localhost:8080/auth/callback'
    
    def __init__(self):
        self.credentials: Optional[Credentials] = None
        self.docs_service = None
        self.sheets_service = None
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()
    
    # OAuth2 Authentication Methods
    
    def get_auth_url(self) -> str:
        """Generate OAuth2 authorization URL"""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.GOOGLE_CLIENT_ID,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.REDIRECT_URI]
                    }
                },
                scopes=self.SCOPES
            )
            flow.redirect_uri = self.REDIRECT_URI
            
            auth_url, _ = flow.authorization_url(prompt='consent')
            return auth_url
            
        except Exception as e:
            logger.error(f"Error generating auth URL: {e}")
            raise GoogleServiceError(f"Failed to generate auth URL: {e}")
    
    async def handle_oauth_callback(self, code: str) -> Dict[str, Any]:
        """Handle OAuth2 callback and exchange code for tokens"""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.GOOGLE_CLIENT_ID,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.REDIRECT_URI]
                    }
                },
                scopes=self.SCOPES
            )
            flow.redirect_uri = self.REDIRECT_URI
            
            # Exchange code for credentials
            flow.fetch_token(code=code)
            self.credentials = flow.credentials
            
            # Initialize Google API services
            await self._initialize_services()
            
            return {
                "success": True,
                "access_token": self.credentials.token,
                "refresh_token": self.credentials.refresh_token,
                "expires_at": self.credentials.expiry.isoformat() if self.credentials.expiry else None
            }
            
        except Exception as e:
            logger.error(f"OAuth callback error: {e}")
            raise GoogleServiceError(f"OAuth authentication failed: {e}")
    
    def set_credentials(self, token_data: Dict[str, Any]) -> None:
        """Set credentials from stored token data"""
        try:
            self.credentials = Credentials(
                token=token_data.get('access_token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.GOOGLE_CLIENT_ID,
                scopes=self.SCOPES
            )
            
            # Refresh token if expired
            if self.credentials.expired and self.credentials.refresh_token:
                self.credentials.refresh(Request())
                
        except Exception as e:
            logger.error(f"Error setting credentials: {e}")
            raise GoogleServiceError(f"Failed to set credentials: {e}")
    
    async def _initialize_services(self) -> None:
        """Initialize Google API services with credentials"""
        try:
            if not self.credentials:
                raise GoogleServiceError("No credentials available")
                
            # Initialize Google Docs service
            self.docs_service = build('docs', 'v1', credentials=self.credentials)
            
            # Initialize Google Sheets service
            self.sheets_service = build('sheets', 'v4', credentials=self.credentials)
            
            logger.info("Google API services initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Google services: {e}")
            raise GoogleServiceError(f"Failed to initialize Google services: {e}")
    
    # Google Docs API Methods
    
    async def read_google_doc(self, doc_id: str) -> Dict[str, Any]:
        """
        Read and parse Google Docs content
        
        Args:
            doc_id: Google Docs document ID
            
        Returns:
            Dict containing document title, content, and metadata
        """
        try:
            if not self.docs_service:
                await self._initialize_services()
            
            # Get document
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            
            # Extract content
            content = self._extract_doc_content(document)
            
            return {
                "success": True,
                "title": document.get('title', 'Untitled'),
                "content": content,
                "doc_id": doc_id,
                "revision_id": document.get('revisionId'),
                "created_time": document.get('createdTime'),
                "modified_time": document.get('modifiedTime')
            }
            
        except HttpError as e:
            logger.error(f"Google Docs API error: {e}")
            raise GoogleServiceError(f"Failed to read Google Doc: {e}")
        except Exception as e:
            logger.error(f"Unexpected error reading Google Doc: {e}")
            raise GoogleServiceError(f"Failed to read Google Doc: {e}")
    
    def _extract_doc_content(self, document: Dict[str, Any]) -> str:
        """Extract plain text content from Google Docs document structure"""
        content = []
        
        try:
            body = document.get('body', {})
            elements = body.get('content', [])
            
            for element in elements:
                if 'paragraph' in element:
                    paragraph = element['paragraph']
                    paragraph_text = self._extract_paragraph_text(paragraph)
                    if paragraph_text.strip():
                        content.append(paragraph_text)
                elif 'table' in element:
                    table_text = self._extract_table_text(element['table'])
                    if table_text.strip():
                        content.append(table_text)
            
            return '\n\n'.join(content)
            
        except Exception as e:
            logger.error(f"Error extracting document content: {e}")
            return ""
    
    def _extract_paragraph_text(self, paragraph: Dict[str, Any]) -> str:
        """Extract text from paragraph element"""
        text_parts = []
        
        elements = paragraph.get('elements', [])
        for element in elements:
            if 'textRun' in element:
                text_run = element['textRun']
                content = text_run.get('content', '')
                text_parts.append(content)
        
        return ''.join(text_parts)
    
    def _extract_table_text(self, table: Dict[str, Any]) -> str:
        """Extract text from table element"""
        table_text = []
        
        rows = table.get('tableRows', [])
        for row in rows:
            row_cells = []
            cells = row.get('tableCells', [])
            
            for cell in cells:
                cell_content = []
                content_elements = cell.get('content', [])
                
                for element in content_elements:
                    if 'paragraph' in element:
                        cell_text = self._extract_paragraph_text(element['paragraph'])
                        if cell_text.strip():
                            cell_content.append(cell_text.strip())
                
                row_cells.append(' '.join(cell_content))
            
            if any(cell.strip() for cell in row_cells):
                table_text.append('\t'.join(row_cells))
        
        return '\n'.join(table_text)
    
    # Google Sheets API Methods
    
    async def create_calendar_sheet(self, sheet_name: str, calendar_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create a new Google Sheet with calendar data
        
        Args:
            sheet_name: Name for the new spreadsheet
            calendar_data: List of calendar events/campaigns
            
        Returns:
            Dict containing sheet ID, URL, and success status
        """
        try:
            if not self.sheets_service:
                await self._initialize_services()
            
            # Create new spreadsheet
            spreadsheet = {
                'properties': {
                    'title': sheet_name
                }
            }
            
            result = self.sheets_service.spreadsheets().create(
                body=spreadsheet
            ).execute()
            
            spreadsheet_id = result['spreadsheetId']
            
            # Populate with calendar data
            await self._populate_calendar_sheet(spreadsheet_id, calendar_data)
            
            return {
                "success": True,
                "spreadsheet_id": spreadsheet_id,
                "url": f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}",
                "title": sheet_name
            }
            
        except HttpError as e:
            logger.error(f"Google Sheets API error: {e}")
            raise GoogleServiceError(f"Failed to create calendar sheet: {e}")
        except Exception as e:
            logger.error(f"Unexpected error creating calendar sheet: {e}")
            raise GoogleServiceError(f"Failed to create calendar sheet: {e}")
    
    async def _populate_calendar_sheet(self, spreadsheet_id: str, calendar_data: List[Dict[str, Any]]) -> None:
        """Populate spreadsheet with calendar data"""
        try:
            # Prepare headers
            headers = [
                'Date', 'Campaign Name', 'Type', 'Target Audience', 
                'Status', 'Goals', 'Content Summary', 'Notes'
            ]
            
            # Prepare data rows
            rows = [headers]
            
            for event in calendar_data:
                row = [
                    event.get('date', ''),
                    event.get('title', ''),
                    event.get('type', ''),
                    event.get('audience', ''),
                    event.get('status', ''),
                    event.get('goals', ''),
                    event.get('content', ''),
                    event.get('notes', '')
                ]
                rows.append(row)
            
            # Update spreadsheet
            body = {
                'values': rows
            }
            
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range='Sheet1!A1',
                valueInputOption='RAW',
                body=body
            ).execute()
            
            # Format headers
            await self._format_sheet_headers(spreadsheet_id)
            
        except Exception as e:
            logger.error(f"Error populating calendar sheet: {e}")
            raise GoogleServiceError(f"Failed to populate calendar sheet: {e}")
    
    async def _format_sheet_headers(self, spreadsheet_id: str) -> None:
        """Format spreadsheet headers with bold text and background color"""
        try:
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,
                        'startRowIndex': 0,
                        'endRowIndex': 1
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.9,
                                'green': 0.9,
                                'blue': 0.9
                            },
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            }]
            
            body = {'requests': requests}
            
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=body
            ).execute()
            
        except Exception as e:
            logger.warning(f"Failed to format sheet headers: {e}")
    
    # Gemini AI API Methods
    
    async def chat_with_gemini(self, message: str, context: Optional[str] = None) -> Dict[str, Any]:
        """
        Send chat message to Gemini AI
        
        Args:
            message: User message
            context: Optional context for the conversation
            
        Returns:
            Dict containing AI response and metadata
        """
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.GEMINI_API_KEY}"
            
            # Prepare prompt with context
            full_prompt = message
            if context:
                full_prompt = f"Context: {context}\n\nUser: {message}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": full_prompt
                    }]
                }],
                "generationConfig": {
                    "temperature": 0.7,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 2048,
                }
            }
            
            async with self.http_client as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code != 200:
                    error_text = await response.aread()
                    logger.error(f"Gemini API error: {response.status_code} - {error_text}")
                    raise GoogleServiceError(f"Gemini API error: {response.status_code}")
                
                result = response.json()
                
                # Extract response text
                candidates = result.get('candidates', [])
                if not candidates:
                    raise GoogleServiceError("No response from Gemini AI")
                
                content = candidates[0].get('content', {})
                parts = content.get('parts', [])
                
                if not parts:
                    raise GoogleServiceError("Empty response from Gemini AI")
                
                ai_response = parts[0].get('text', '')
                
                return {
                    "success": True,
                    "response": ai_response,
                    "model": "gemini-pro",
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Gemini chat error: {e}")
            raise GoogleServiceError(f"Failed to chat with Gemini: {e}")
    
    async def extract_campaigns_from_content(self, content: str, doc_title: str = "") -> Dict[str, Any]:
        """
        Use Gemini AI to extract campaign information from document content
        
        Args:
            content: Document content to analyze
            doc_title: Title of the document
            
        Returns:
            Dict containing extracted campaigns and metadata
        """
        try:
            prompt = f"""
            Please analyze the following document content and extract all email marketing campaigns, events, or promotional activities mentioned. 

            Document Title: {doc_title}

            Content:
            {content}

            For each campaign/event found, extract the following information in JSON format:
            - title: Campaign name or title
            - date: Date mentioned (if any)
            - type: Type of campaign (email, social, event, promotion, etc.)
            - audience: Target audience (if mentioned)
            - goals: Campaign goals or objectives
            - content: Brief description of content/message
            - status: Current status (if mentioned)
            - notes: Any additional relevant notes

            Return the results as a JSON array of campaign objects. If no campaigns are found, return an empty array.
            """
            
            result = await self.chat_with_gemini(prompt)
            
            if not result["success"]:
                raise GoogleServiceError("Failed to get AI response")
            
            # Try to parse JSON from AI response
            ai_response = result["response"]
            campaigns = self._extract_json_from_ai_response(ai_response)
            
            return {
                "success": True,
                "campaigns": campaigns,
                "source_title": doc_title,
                "extraction_timestamp": datetime.now().isoformat(),
                "ai_response": ai_response
            }
            
        except Exception as e:
            logger.error(f"Campaign extraction error: {e}")
            raise GoogleServiceError(f"Failed to extract campaigns: {e}")
    
    def _extract_json_from_ai_response(self, response: str) -> List[Dict[str, Any]]:
        """Extract JSON array from AI response text"""
        try:
            # Look for JSON array in the response
            import re
            
            # Try to find JSON array pattern
            json_pattern = r'\[.*\]'
            matches = re.findall(json_pattern, response, re.DOTALL)
            
            if matches:
                # Try to parse the first match
                json_text = matches[0]
                campaigns = json.loads(json_text)
                
                if isinstance(campaigns, list):
                    return campaigns
            
            # If no valid JSON found, try to parse the entire response
            try:
                campaigns = json.loads(response)
                if isinstance(campaigns, list):
                    return campaigns
            except:
                pass
            
            # If all parsing fails, return empty list
            logger.warning("Could not extract JSON from AI response")
            return []
            
        except Exception as e:
            logger.error(f"JSON extraction error: {e}")
            return []
    
    # Utility Methods
    
    def extract_doc_id_from_url(self, url: str) -> Optional[str]:
        """Extract Google Docs document ID from URL"""
        try:
            import re
            
            # Pattern for Google Docs URLs
            pattern = r'/document/d/([a-zA-Z0-9-_]+)'
            match = re.search(pattern, url)
            
            if match:
                return match.group(1)
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting doc ID from URL: {e}")
            return None
    
    async def validate_doc_access(self, doc_id: str) -> bool:
        """Validate that we can access a Google Doc"""
        try:
            result = await self.read_google_doc(doc_id)
            return result.get("success", False)
            
        except Exception as e:
            logger.error(f"Doc access validation failed: {e}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if user is authenticated with Google APIs"""
        return (
            self.credentials is not None and 
            not self.credentials.expired
        )


# Singleton instance
google_service = GoogleService()


# Async context manager for clean usage
class GoogleServiceManager:
    """Context manager for Google Service"""
    
    def __init__(self):
        self.service = google_service
    
    async def __aenter__(self):
        return self.service
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup if needed
        pass


# Convenience functions for common operations
async def read_document(doc_id: str, credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function to read a Google Doc"""
    async with GoogleServiceManager() as service:
        if credentials:
            service.set_credentials(credentials)
        return await service.read_google_doc(doc_id)


async def create_calendar_export(sheet_name: str, calendar_data: List[Dict[str, Any]], 
                                credentials: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Convenience function to export calendar data to Google Sheets"""
    async with GoogleServiceManager() as service:
        if credentials:
            service.set_credentials(credentials)
        return await service.create_calendar_sheet(sheet_name, calendar_data)


async def ai_chat(message: str, context: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function for Gemini AI chat"""
    async with GoogleServiceManager() as service:
        return await service.chat_with_gemini(message, context)


async def extract_campaigns(content: str, title: str = "") -> Dict[str, Any]:
    """Convenience function to extract campaigns using AI"""
    async with GoogleServiceManager() as service:
        return await service.extract_campaigns_from_content(content, title)