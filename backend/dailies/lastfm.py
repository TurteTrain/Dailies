"""Fallback genre source: Last.fm's artist.getTopTags (free API key, no user login needed).
Docs: https://www.last.fm/api/show/artist.getTopTags"""
import os
import re

import requests

API_URL = "https://ws.audioscrobbler.com/2.0/"

# Tags users add that are not genres. Extend this list as you see junk in your data.
IGNORE = {
    "seen live", "favorites", "favourites", "favorite", "awesome", "love", "all", "good",
    "female vocalists", "male vocalists", "female vocalist", "male vocalist", "singer-songwriter",
    "american", "british", "uk", "usa", "canadian", "australian", "swedish", "german",
    "albums i own", "under 2000 listeners", "spotify",
}
DECADE = re.compile(r"^(\d{2}|\d{4})'?s$")        # "90s", "2000s"


class LastfmError(Exception):
    def __init__(self, code, message):
        super().__init__(f"Last.fm error {code}: {message}")
        self.code = code


def clean_tags(tags, limit=5, min_count=40):
    """Keep the most popular genre-like tags. Counts are relative (the top tag is 100)."""
    out = []
    for t in tags:
        name = str(t.get("name", "")).strip().lower()
        try:
            count = int(t.get("count", 100))
        except (TypeError, ValueError):
            count = 100
        if not name or name in IGNORE or DECADE.match(name) or count < min_count:
            continue
        if name not in out:
            out.append(name)
        if len(out) == limit:
            break
    return out


def top_tags(artist_name, limit=5, min_count=40):
    """Genre-like tags for an artist. Returns None if no API key is configured,
    [] if Last.fm doesn't know the artist, and raises LastfmError / requests errors otherwise."""
    return _get_tags({"method": "artist.gettoptags", "artist": artist_name}, limit, min_count)


def track_top_tags(artist_name, track_name, limit=5, min_count=40):
    """Tags for one song (often moods like "chill" or "sad"). Same return values as top_tags."""
    return _get_tags({"method": "track.gettoptags", "artist": artist_name, "track": track_name},
                     limit, min_count)


def _get_tags(params, limit, min_count):
    key = os.environ.get("LASTFM_API_KEY")
    if not key:
        return None
    r = requests.get(API_URL, timeout=15, params={
        **params, "autocorrect": 1, "api_key": key, "format": "json"})
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        if data["error"] == 6:                    # "artist/track not found"
            return []
        raise LastfmError(data["error"], data.get("message", ""))
    tags = (data.get("toptags") or {}).get("tag") or []
    if isinstance(tags, dict):                    # a single tag can come back as an object
        tags = [tags]
    return clean_tags(tags, limit, min_count)
