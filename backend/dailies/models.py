from django.db import models

class SpotifyUser(models.Model):
    spotify_id = models.CharField(max_length=64, unique=True)
    refresh_token = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class Track(models.Model):
    track_id = models.CharField(max_length=64, primary_key=True)
    name = models.TextField()
    artist = models.TextField()
    duration_ms = models.IntegerField()

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
