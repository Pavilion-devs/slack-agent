#!/usr/bin/env python3
"""
Google Calendar Authentication Setup Script
Run this to set up or refresh Google Calendar authentication tokens.
"""

import os
import json
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Google Calendar API scopes
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events'
]

# File paths
CREDENTIALS_FILE = 'credentials.json'  # Download from Google Cloud Console
TOKEN_FILE = 'calendar_token.json'


def setup_calendar_auth():
    """Set up Google Calendar authentication."""
    print("🔐 Setting up Google Calendar Authentication...")
    
    creds = None
    token_path = Path(TOKEN_FILE)
    
    # Load existing token if available
    if token_path.exists():
        print("📄 Found existing token file, attempting to load...")
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            print("✅ Token loaded successfully")
        except Exception as e:
            print(f"❌ Error loading token: {e}")
            print("🔄 Will need to re-authenticate...")
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Token expired, attempting to refresh...")
            try:
                creds.refresh(Request())
                print("✅ Token refreshed successfully!")
            except Exception as e:
                print(f"❌ Token refresh failed: {e}")
                print("🔄 Need to re-authenticate...")
                creds = None
        
        if not creds:
            print("🌐 Starting OAuth flow...")
            
            # Check if credentials.json exists
            if not Path(CREDENTIALS_FILE).exists():
                print(f"❌ Missing {CREDENTIALS_FILE}")
                print("\n📋 To fix this:")
                print("1. Go to https://console.cloud.google.com/")
                print("2. Create a new project or select existing")
                print("3. Enable Google Calendar API")
                print("4. Create OAuth2 credentials (Desktop application)")
                print("5. Download credentials.json to this directory")
                print("6. Run this script again")
                return False
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=8080)
                print("✅ Authentication successful!")
            except Exception as e:
                print(f"❌ Authentication failed: {e}")
                return False
        
        # Save the credentials for the next run
        try:
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            print(f"💾 Token saved to {TOKEN_FILE}")
        except Exception as e:
            print(f"❌ Error saving token: {e}")
            return False
    
    # Test the calendar connection
    try:
        print("🧪 Testing calendar connection...")
        service = build('calendar', 'v3', credentials=creds)
        
        # Get calendar list to test connection
        calendars_result = service.calendarList().list().execute()
        calendars = calendars_result.get('items', [])
        
        print(f"✅ Successfully connected to Google Calendar!")
        print(f"📅 Found {len(calendars)} calendars:")
        
        for calendar in calendars[:3]:  # Show first 3
            name = calendar.get('summary', 'Unnamed')
            primary = " (Primary)" if calendar.get('primary') else ""
            print(f"   • {name}{primary}")
        
        return True
        
    except Exception as e:
        print(f"❌ Calendar connection test failed: {e}")
        return False


def check_calendar_status():
    """Check current calendar authentication status."""
    print("🔍 Checking Google Calendar Authentication Status...")
    
    if not Path(TOKEN_FILE).exists():
        print("❌ No token file found")
        return False
    
    try:
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        
        if not creds.valid:
            if creds.expired:
                expiry = creds.expiry.strftime('%Y-%m-%d %H:%M:%S UTC') if creds.expiry else "Unknown"
                print(f"⏰ Token expired: {expiry}")
                if creds.refresh_token:
                    print("🔄 Refresh token available, can attempt refresh")
                else:
                    print("❌ No refresh token, need to re-authenticate")
            else:
                print("❌ Token invalid for unknown reason")
            return False
        
        print("✅ Token is valid")
        
        # Test actual API call
        service = build('calendar', 'v3', credentials=creds)
        service.calendarList().list(maxResults=1).execute()
        print("✅ Calendar API connection successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking token: {e}")
        return False


def create_sample_credentials():
    """Create a sample credentials.json template."""
    print("📝 Creating sample credentials.json template...")
    
    sample_creds = {
        "installed": {
            "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
            "project_id": "your-project-id",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": "YOUR_CLIENT_SECRET",
            "redirect_uris": ["http://localhost"]
        }
    }
    
    with open('credentials_template.json', 'w') as f:
        json.dump(sample_creds, f, indent=2)
    
    print("✅ Created credentials_template.json")
    print("📋 Replace YOUR_CLIENT_ID and YOUR_CLIENT_SECRET with actual values")
    print("📋 Then rename to credentials.json")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "check":
            check_calendar_status()
        elif command == "template":
            create_sample_credentials()
        elif command == "setup":
            setup_calendar_auth()
        else:
            print("Usage: python setup_calendar_auth.py [check|setup|template]")
    else:
        # Default: check status and setup if needed
        if not check_calendar_status():
            print("\n🚀 Running setup...")
            setup_calendar_auth()
        else:
            print("✅ Google Calendar authentication is working!")