from django.db import models
from django.conf import settings

class SpotifyUser(models.Model):
    account = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   on_delete=models.CASCADE, related_name="spotify")
    spotify_id = models.CharField(max_length=64, unique=True)
    refresh_token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Artist(models.Model):
    artist_id = models.CharField(max_length=64, primary_key=True)
    name = models.TextField()
    genres = models.JSONField(default=list, blank=True)
    genres_fetched_at = models.DateTimeField(null=True, blank=True)  # null = not looked up yet
    
class Track(models.Model):
    track_id = models.CharField(max_length=64, primary_key=True)
    name = models.TextField()
    artist = models.TextField()
    duration_ms = models.IntegerField()
    artists = models.ManyToManyField(Artist, related_name="tracks", blank=True)
    # Filled in by the poller's mood step (dailies/mood.py). mood_tagged_at null = not tagged yet.
    mood = models.CharField(max_length=32, blank=True, default="")
    mood_scores = models.JSONField(default=dict, blank=True)     # {label: probability}
    mood_confidence = models.FloatField(null=True, blank=True)
    mood_tagged_at = models.DateTimeField(null=True, blank=True)

class Listen(models.Model):
    user = models.ForeignKey(SpotifyUser, on_delete=models.CASCADE)
    track = models.ForeignKey(Track, on_delete=models.CASCADE)
    played_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "played_at", "track"],
                                    name="unique_listen")
        ]
        indexes = [models.Index(fields=["user", "played_at"])]
