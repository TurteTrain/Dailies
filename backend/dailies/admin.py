from django.contrib import admin
from .models import SpotifyUser, Track, Listen

@admin.register(SpotifyUser)
class SpotifyUserAdmin(admin.ModelAdmin):
    list_display = ("spotify_id", "created_at")
    exclude = ("refresh_token",)   # keep the token out of the UI

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ("name", "artist", "duration_ms")
    search_fields = ("name", "artist")

@admin.register(Listen)
class ListenAdmin(admin.ModelAdmin):
    list_display = ("played_at", "user", "track")
    list_filter = ("user",)
    ordering = ("-played_at",)
