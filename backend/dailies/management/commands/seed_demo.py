import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from dailies.models import Artist, Listen, SpotifyUser, Track

# (track name, artist name, genres, mood). Moods are preset so the demo works without the model.
SAMPLE = [("Midnight Drive", "Neon Atlas", ["synthwave", "electropop"], "dreamy"),
          ("Gator Country", "The Swamp Kings", ["southern rock"], "energetic"),
          ("Late Library", "Quiet Hours", ["lo-fi", "ambient"], "focused"),
          ("Paynes Prairie", "Sunday Static", ["indie rock"], "chill"),
          ("Cold Brew", "Morning Shift", ["lo-fi", "indie pop"], "chill"),
          ("Campus Lights", "Orange & Blue", ["pop"], "happy"),
          ("Bus Route 8", "The Commuters", ["indie rock", "indie pop"], "happy"),
          ("Finals Week", "Redline", ["punk", "indie rock"], "angry"),
          ("Sunset Lap", "Coastal Drive", ["synthwave"], "dreamy"),
          ("Echo Hall", "Reverb Club", ["ambient", "electropop"], "sad")]


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
        for i, (name, artist_name, genres, mood) in enumerate(SAMPLE):
            artist, _ = Artist.objects.get_or_create(
                artist_id=f"seed_artist_{i}",
                defaults={"name": artist_name, "genres": genres, "genres_fetched_at": timezone.now()})
            t, _ = Track.objects.get_or_create(
                track_id=f"seed_{i}",
                defaults={"name": name, "artist": artist_name, "duration_ms": 180000 + i * 5000,
                          "mood": mood, "mood_scores": {mood: 0.9}, "mood_confidence": 0.9,
                          "mood_tagged_at": timezone.now()})
            t.artists.add(artist)
            tracks.append(t)
        now = timezone.now()
        Listen.objects.bulk_create(
            [Listen(user=user, track=random.choice(tracks),
                    played_at=now - timedelta(minutes=7 * i + random.randint(0, 5)))
             for i in range(opts["count"])], ignore_conflicts=True)
        self.stdout.write(f"Listen rows for {user.spotify_id}: {Listen.objects.filter(user=user).count()}")
