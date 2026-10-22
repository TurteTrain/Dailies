import base64, os, requests

TOKEN_URL = "https://accounts.spotify.com/api/token"
API = "https://api.spotify.com/v1"

def _basic_auth():
    raw = f"{os.environ['SPOTIFY_CLIENT_ID']}:{os.environ['SPOTIFY_CLIENT_SECRET']}"
    return {"Authorization": "Basic " + base64.b64encode(raw.encode()).decode()}

def exchange_code(code, redirect_uri):
    r = requests.post(TOKEN_URL, headers=_basic_auth(), timeout=15, data={
        "grant_type": "authorization_code", "code": code, "redirect_uri": redirect_uri})
    r.raise_for_status()
    return r.json()

def refresh_access_token(refresh_token):
    r = requests.post(TOKEN_URL, headers=_basic_auth(), timeout=15, data={
        "grant_type": "refresh_token", "refresh_token": refresh_token})
    r.raise_for_status()
    return r.json()   # may include a new refresh_token

def get_me(access_token):
    r = requests.get(f"{API}/me", timeout=15,
                     headers={"Authorization": f"Bearer {access_token}"})
    r.raise_for_status()
    return r.json()

def get_recently_played(access_token):
    r = requests.get(f"{API}/me/player/recently-played", params={"limit": 50},
                     timeout=15, headers={"Authorization": f"Bearer {access_token}"})
    r.raise_for_status()
    return r.json()["items"]
