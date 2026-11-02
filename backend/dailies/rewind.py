from collections import Counter
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Count, Sum

from .models import Artist, Listen
from .mood import MIN_CONFIDENCE


def day_bounds(day: date, tz_name: str = "UTC"):
    """[start, end) of a calendar day in the given timezone, as aware datetimes.
    Computed from the next day's midnight, so DST days (23 or 25 hours) are handled correctly."""
    tz = ZoneInfo(tz_name)                     # raises ZoneInfoNotFoundError for bad names
    start = datetime.combine(day, time.min, tzinfo=tz)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=tz)
    return start, end


def get_daily_rewind(spotify_user, day: date, tz_name: str = "UTC", limit: int = 5) -> dict:
    start, end = day_bounds(day, tz_name)
    listens = Listen.objects.filter(user=spotify_user, played_at__gte=start, played_at__lt=end)

    result = {"date": day.isoformat(), "timezone": tz_name, "total_plays": listens.count(),
              "approx_minutes": 0, "top_tracks": [], "top_artists": [], "top_genres": [],
              "top_moods": [], "mood_of_the_day": None}
    if result["total_plays"] == 0:
        return result

    ms = listens.aggregate(total=Sum("track__duration_ms"))["total"] or 0
    result["approx_minutes"] = round(ms / 60000)      # full track lengths, not time actually played

    # Top tracks: group listens by track
    result["top_tracks"] = [
        {"track_id": r["track__track_id"], "name": r["track__name"],
         "artist": r["track__artist"], "plays": r["plays"]}
        for r in (listens.values("track__track_id", "track__name", "track__artist")
                  .annotate(plays=Count("id"))
                  .order_by("-plays", "track__name")[:limit])
    ]

    # Top artists: a listen counts once for EACH artist on the track
    artist_rows = list(
        listens.filter(track__artists__isnull=False)
        .values("track__artists__artist_id", "track__artists__name")
        .annotate(plays=Count("id"))
        .order_by("-plays", "track__artists__name")
    )
    result["top_artists"] = [
        {"artist_id": r["track__artists__artist_id"], "name": r["track__artists__name"],
         "plays": r["plays"]} for r in artist_rows[:limit]
    ]

    # Top genres: each artist's genres, weighted by that artist's plays that day (all artists, not just top N)
    genres_by_artist = dict(
        Artist.objects.filter(pk__in=[r["track__artists__artist_id"] for r in artist_rows])
        .values_list("pk", "genres"))
    genre_plays = Counter()
    for r in artist_rows:
        for genre in (genres_by_artist.get(r["track__artists__artist_id"]) or []):
            genre_plays[genre] += r["plays"]
    result["top_genres"] = [
        {"genre": g, "plays": n}
        for g, n in sorted(genre_plays.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    ]

    # Moods: each play counts toward its track's mood; low-confidence guesses are left out
    mood_rows = (listens.filter(track__mood_confidence__gte=MIN_CONFIDENCE).exclude(track__mood="")
                 .values("track__mood").annotate(plays=Count("id")).order_by("-plays", "track__mood"))
    total = sum(r["plays"] for r in mood_rows)
    result["top_moods"] = [{"mood": r["track__mood"], "plays": r["plays"],
                            "share": round(r["plays"] / total, 3)} for r in mood_rows]
    if result["top_moods"]:
        result["mood_of_the_day"] = result["top_moods"][0]["mood"]
    return result
