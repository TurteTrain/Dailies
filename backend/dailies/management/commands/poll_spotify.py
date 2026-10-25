import os
from datetime import datetime

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from dailies import lastfm, spotify
from dailies.models import Artist, Listen, SpotifyUser, Track

# Spotify has no batch artist endpoint for dev-mode apps, so genres cost one request per artist.
# Each artist is looked up once and cached in the database; cap the lookups per user per run.
ARTIST_LOOKUPS_PER_RUN = 25


class Command(BaseCommand):
    help = "Fetch recent plays (and artist genres) for every connected Spotify user"

    def handle(self, *args, **options):
        for user in SpotifyUser.objects.all():
            try:
                tokens = spotify.refresh_access_token(user.refresh_token)
                if tokens.get("refresh_token"):
                    user.refresh_token = tokens["refresh_token"]
                    user.save(update_fields=["refresh_token"])
                access_token = tokens["access_token"]
                items = spotify.get_recently_played(access_token)
            except requests.HTTPError as e:
                self.stderr.write(f"{user.spotify_id}: {e}")
                continue

            tracks, artists, links, listens = {}, {}, set(), []
            for it in items:
                t = it["track"]
                if not t.get("id"):          # local files have no Spotify id
                    continue
                tracks[t["id"]] = Track(
                    track_id=t["id"], name=t["name"],
                    artist=", ".join(a["name"] for a in t["artists"]),
                    duration_ms=t["duration_ms"])
                for a in t["artists"]:
                    if a.get("id"):
                        artists[a["id"]] = Artist(artist_id=a["id"], name=a["name"])
                        links.add((t["id"], a["id"]))
                listens.append(Listen(
                    user=user, track_id=t["id"],
                    played_at=datetime.fromisoformat(it["played_at"].replace("Z", "+00:00"))))

            Track.objects.bulk_create(tracks.values(), ignore_conflicts=True)
            Artist.objects.bulk_create(artists.values(), ignore_conflicts=True)
            Through = Track.artists.through
            Through.objects.bulk_create(
                [Through(track_id=t, artist_id=a) for t, a in links], ignore_conflicts=True)
            Listen.objects.bulk_create(listens, ignore_conflicts=True)
            self.stdout.write(f"{user.spotify_id}: fetched {len(listens)} plays")

            self.fetch_genres(access_token)

    def fetch_genres(self, access_token):
        """Look up genres once per artist and cache them.

        Spotify no longer returns a "genres" field to development-mode apps, so when LASTFM_API_KEY
        is set we use Last.fm tags and skip the (useless) Spotify call. Without a key we fall back
        to Spotify's genres field, which stays empty if Spotify doesn't send it."""
        use_lastfm = bool(os.environ.get("LASTFM_API_KEY"))
        pending = list(Artist.objects.filter(genres_fetched_at__isnull=True)[:ARTIST_LOOKUPS_PER_RUN])
        for artist in pending:
            if use_lastfm:
                try:
                    genres = lastfm.top_tags(artist.name) or []
                except (requests.RequestException, lastfm.LastfmError) as e:
                    self.stderr.write(f"last.fm {artist.name}: {e}")
                    continue                   # temporary failure: leave unfetched, retry next run
            else:
                try:
                    data = spotify.get_artist(access_token, artist.artist_id)
                except requests.HTTPError as e:
                    self.stderr.write(f"artist {artist.artist_id}: {e}")
                    if e.response is not None and e.response.status_code == 429:
                        break                  # rate limited: stop and retry next run
                    continue
                genres = data.get("genres") or []   # field may be missing or empty

            artist.genres = genres
            artist.genres_fetched_at = timezone.now()
            artist.save(update_fields=["genres", "genres_fetched_at"])
