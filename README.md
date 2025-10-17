# GA4 Traffic Comparison Dashboard

A professional Streamlit dashboard to compare Organic Traffic with AI Mode Traffic using Google Analytics 4 data.

## Features

- **Simple OAuth Sign-in**: Users just click "Sign in with Google" - no setup required
- **Automatic GA4 Property Detection**: Dashboard fetches all GA4 properties the user has access to
- **Traffic Comparison**: Side-by-side comparison of Organic vs AI Mode traffic
- **Professional Charts**: Clean line charts showing trends over time
- **Data Export**: Download traffic data as CSV

## For End Users

### How to Use

1. Open the dashboard
2. Click **"Sign in with Google"**
3. Authorize access to your Google Analytics
4. Select your GA4 property
5. View your traffic comparison

That's it! No configuration needed.

## For Administrators

### One-Time Setup

You need to provide the OAuth credentials for the app. Users will NOT need to do any setup.

1. **Create OAuth Credentials in Google Cloud Console**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create/select a project
   - Enable **Google Analytics Admin API** and **Google Analytics Data API**
   - Go to "Credentials" → "Create Credentials" → "OAuth client ID"
   - Application type: **Web application**
   - Authorized redirect URIs: `http://localhost:8501` (or your deployment URL)
   - Download the credentials

2. **Place credentials file**:
   - Save the downloaded file as `client_secret.json`
   - Put it in the project directory: `C:\Users\hp\code\streamlit\`

3. **Deploy**:
   ```bash
   pip install -r requirements.txt
   streamlit run app.py
   ```

Users can now sign in with their Google accounts and access their GA4 data directly.

## How It Works

### Authentication Flow
1. User clicks "Sign in with Google"
2. Google OAuth consent screen opens
3. User authorizes access to GA4
4. Credentials stored in `user_credentials.json` (per user)
5. Dashboard loads user's GA4 properties automatically

### AI Traffic Detection

The dashboard filters traffic by source. Customize in `ga4_client.py`:

```python
def _create_traffic_filter(self, traffic_source):
    if traffic_source == "ai_mode":
        return FilterExpression(
            filter=Filter(
                field_name="sessionSource",
                string_filter=Filter.StringFilter(
                    value="ai",  # Adjust this
                    match_type=Filter.StringFilter.MatchType.CONTAINS
                ),
            )
        )
```

Adjust based on your tracking:
- UTM source (utm_source=chatgpt, perplexity, etc.)
- Custom channel groups
- Referral sources

## File Structure

```
streamlit/
├── app.py                    # Main dashboard
├── auth.py                   # OAuth handler
├── ga4_client.py            # GA4 API client
├── client_secret.json       # OAuth config (admin provides)
├── user_credentials.json    # User tokens (auto-generated)
├── requirements.txt
└── .streamlit/config.toml
```

## Security

- `client_secret.json` - Admin provides this once
- `user_credentials.json` - Auto-generated per user, add to `.gitignore`
- Users can revoke access via Google Account settings or "Sign Out" button

## Deployment

For production deployment:

1. Update redirect URI in Google Cloud Console to your production URL
2. Update `auth.py` line 20-21 to use your production URL
3. Deploy with your `client_secret.json`

## License

MIT License
