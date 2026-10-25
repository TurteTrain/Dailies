import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from dailies.models import Artist, Listen, SpotifyUser, Track

# (track name, artist name, genres)
SAMPLE = [("Midnight Drive", "Neon Atlas", ["synthwave", "electropop"]),
          ("Gator Country", "The Swamp Kings", ["southern rock"]),
          ("Late Library", "Quiet Hours", ["lo-fi", "ambient"]),
          ("Paynes Prairie", "Sunday Static", ["indie rock"]),
          ("Cold Brew", "Morning Shift", ["lo-fi", "indie pop"]),
          ("Campus Lights", "Orange & Blue", ["pop"]),
          ("Bus Route 8", "The Commuters", ["indie rock", "indie pop"]),
          ("Finals Week", "Redline", ["punk", "indie rock"]),
          ("Sunset Lap", "Coastal Drive", ["synthwave"]),
          ("Echo Hall", "Reverb Club", ["ambient", "electropop"])]


class Command(BaseCommand):
    help = "Create sample listens (with artists and genres) for an existing Spotify-linked user"

    def add_arguments(self, parser):
        parser.add_argument("spotify_id")
        parser.add_argument("--count", type=int, default=120)

    def handle(self, *args, **opts):
        try:
            user = SpotifyUser.objects.get(spotify_id=opts["spotify_id"])
        except SpotifyUser.DoesNotExist:
            raise CommandError("No SpotifyUser with that spotify_id. Connect Spotify first.")
        tracks = []
        for i, (name, artist_name, genres) in enumerate(SAMPLE):
            artist, _ = Artist.objects.get_or_create(
                artist_id=f"seed_artist_{i}",
                defaults={"name": artist_name, "genres": genres, "genres_fetched_at": timezone.now()})
            t, _ = Track.objects.get_or_create(
                track_id=f"seed_{i}",
                defaults={"name": name, "artist": artist_name, "duration_ms": 180000 + i * 5000})
            t.artists.add(artist)
            tracks.append(t)
        now = timezone.now()
        Listen.objects.bulk_create(
            [Listen(user=user, track=random.choice(tracks),
                    played_at=now - timedelta(minutes=7 * i + random.randint(0, 5)))
             for i in range(opts["count"])], ignore_conflicts=True)
        self.stdout.write(f"Listen rows for {user.spotify_id}: {Listen.objects.filter(user=user).count()}")
