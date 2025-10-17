import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
import json
from pathlib import Path

# OAuth 2.0 scopes for GA4 access
SCOPES = [
    'https://www.googleapis.com/auth/analytics.readonly',
    'https://www.googleapis.com/auth/analytics',
    'https://www.googleapis.com/auth/analytics.edit',
    'https://www.googleapis.com/auth/webmasters.readonly'
]

# File to store user credentials
CREDENTIALS_FILE = Path('user_credentials.json')
CLIENT_CONFIG_FILE = Path('client_secret.json')

class GA4Auth:
    def __init__(self):
        self.credentials = None
        self.load_credentials()

    def load_credentials(self):
        """Load saved user credentials if they exist"""
        if CREDENTIALS_FILE.exists():
            try:
                with open(CREDENTIALS_FILE, 'r') as f:
                    cred_data = json.load(f)
                    self.credentials = Credentials.from_authorized_user_info(cred_data, SCOPES)

                    # Check if credentials are expired
                    if self.credentials and self.credentials.expired and self.credentials.refresh_token:
                        from google.auth.transport.requests import Request
                        self.credentials.refresh(Request())
                        self.save_credentials()
            except Exception as e:
                st.error(f"Error loading credentials: {e}")
                self.credentials = None

    def save_credentials(self):
        """Save user credentials to file"""
        if self.credentials:
            cred_data = {
                'token': self.credentials.token,
                'refresh_token': self.credentials.refresh_token,
                'token_uri': self.credentials.token_uri,
                'client_id': self.credentials.client_id,
                'client_secret': self.credentials.client_secret,
                'scopes': self.credentials.scopes
            }
            with open(CREDENTIALS_FILE, 'w') as f:
                json.dump(cred_data, f)

    def is_authenticated(self):
        """Check if user is authenticated"""
        return self.credentials is not None and self.credentials.valid

    def get_auth_url(self):
        """Generate OAuth authorization URL"""
        try:
            # Try to load from Streamlit secrets first (for cloud deployment)
            if hasattr(st, 'secrets') and 'google_oauth' in st.secrets:
                client_config = {
                    'web': {
                        'client_id': st.secrets['google_oauth']['client_id'],
                        'client_secret': st.secrets['google_oauth']['client_secret'],
                        'auth_uri': st.secrets['google_oauth'].get('auth_uri', 'https://accounts.google.com/o/oauth2/auth'),
                        'token_uri': st.secrets['google_oauth'].get('token_uri', 'https://oauth2.googleapis.com/token'),
                        'redirect_uris': [st.secrets['google_oauth'].get('redirect_uri', 'http://localhost:8501')]
                    }
                }
                redirect_uri = st.secrets['google_oauth'].get('redirect_uri', 'http://localhost:8501')
            # Fall back to local file for development
            elif CLIENT_CONFIG_FILE.exists():
                with open(CLIENT_CONFIG_FILE, 'r') as f:
                    client_config = json.load(f)

                # Handle both "web" and "installed" type OAuth clients
                if 'installed' in client_config:
                    client_config['web'] = client_config['installed']
                    del client_config['installed']

                redirect_uri = 'http://localhost:8501'
            else:
                return None

            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )

            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'
            )

            return auth_url
        except Exception as e:
            st.error(f"Error generating auth URL: {e}")
            return None

    def authenticate_with_code(self, auth_code):
        """Complete OAuth flow with authorization code"""
        try:
            # Try to load from Streamlit secrets first (for cloud deployment)
            if hasattr(st, 'secrets') and 'google_oauth' in st.secrets:
                client_config = {
                    'web': {
                        'client_id': st.secrets['google_oauth']['client_id'],
                        'client_secret': st.secrets['google_oauth']['client_secret'],
                        'auth_uri': st.secrets['google_oauth'].get('auth_uri', 'https://accounts.google.com/o/oauth2/auth'),
                        'token_uri': st.secrets['google_oauth'].get('token_uri', 'https://oauth2.googleapis.com/token'),
                        'redirect_uris': [st.secrets['google_oauth'].get('redirect_uri', 'http://localhost:8501')]
                    }
                }
                redirect_uri = st.secrets['google_oauth'].get('redirect_uri', 'http://localhost:8501')
            # Fall back to local file for development
            elif CLIENT_CONFIG_FILE.exists():
                with open(CLIENT_CONFIG_FILE, 'r') as f:
                    client_config = json.load(f)

                # Handle both "web" and "installed" type OAuth clients
                if 'installed' in client_config:
                    client_config['web'] = client_config['installed']
                    del client_config['installed']

                redirect_uri = 'http://localhost:8501'
            else:
                st.error("OAuth configuration not found")
                return False

            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )

            flow.fetch_token(code=auth_code)
            self.credentials = flow.credentials
            self.save_credentials()
            return True
        except Exception as e:
            st.error(f"Authentication failed: {e}")
            return False

    def logout(self):
        """Remove saved credentials"""
        if CREDENTIALS_FILE.exists():
            CREDENTIALS_FILE.unlink()
        self.credentials = None

    def get_credentials(self):
        """Get current credentials"""
        return self.credentials

    def get_ga4_properties(self):
        """Fetch GA4 properties accessible to the authenticated user"""
        if not self.is_authenticated():
            return []

        try:
            # Use Admin API to list properties
            admin_service = build('analyticsadmin', 'v1beta', credentials=self.credentials)

            # List account summaries (includes properties)
            account_summaries = admin_service.accountSummaries().list().execute()

            properties = []
            for account in account_summaries.get('accountSummaries', []):
                for property_summary in account.get('propertySummaries', []):
                    # Only include GA4 properties (not UA)
                    if property_summary.get('propertyType') == 'PROPERTY_TYPE_ORDINARY':
                        properties.append({
                            'property_id': property_summary.get('property').split('/')[-1],
                            'display_name': property_summary.get('displayName'),
                            'parent_account': account.get('displayName')
                        })

            return properties
        except Exception as e:
            st.error(f"Error fetching properties: {e}")
            return []
