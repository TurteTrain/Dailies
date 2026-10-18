from datetime import datetime
import requests
from django.core.management.base import BaseCommand
from dailies import spotify
from dailies.models import SpotifyUser, Track, Listen

class Command(BaseCommand):
    help = "Fetch recent plays for every connected Spotify user"

    def handle(self, *args, **options):
        for user in SpotifyUser.objects.all():
            try:
                tokens = spotify.refresh_access_token(user.refresh_token)
                if tokens.get("refresh_token"):          # Spotify sometimes rotates it
                    user.refresh_token = tokens["refresh_token"]
                    user.save(update_fields=["refresh_token"])
                items = spotify.get_recently_played(tokens["access_token"])
            except requests.HTTPError as e:
                self.stderr.write(f"{user.spotify_id}: {e}")
                continue                                  # one bad user shouldn't stop the rest

            tracks, listens = {}, []
            for it in items:
                t = it["track"]
                tracks[t["id"]] = Track(
                    track_id=t["id"], name=t["name"],
                    artist=", ".join(a["name"] for a in t["artists"]),
                    duration_ms=t["duration_ms"])
                listens.append(Listen(
                    user=user, track_id=t["id"],
                    played_at=datetime.fromisoformat(it["played_at"].replace("Z", "+00:00"))))

            Track.objects.bulk_create(tracks.values(), ignore_conflicts=True)
            Listen.objects.bulk_create(listens, ignore_conflicts=True)
            self.stdout.write(f"{user.spotify_id}: fetched {len(listens)} plays")
