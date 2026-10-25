from datetime import date, datetime, timezone as dt_tz

from django.contrib.auth.models import User
from django.test import TestCase

from dailies.models import Artist, Listen, SpotifyUser, Track
from dailies.rewind import day_bounds, get_daily_rewind


def utc(*args):
    return datetime(*args, tzinfo=dt_tz.utc)


class RewindTests(TestCase):
    def setUp(self):
        self.a = SpotifyUser.objects.create(spotify_id="a", refresh_token="x")
        self.b = SpotifyUser.objects.create(spotify_id="b", refresh_token="x")
        self.ar1 = Artist.objects.create(artist_id="ar1", name="Alpha", genres=["indie pop", "dream pop"])
        self.ar2 = Artist.objects.create(artist_id="ar2", name="Beta", genres=["indie pop"])
        self.ar3 = Artist.objects.create(artist_id="ar3", name="Gamma", genres=[])
        self.t1 = self._track("t1", "Song A", [self.ar1])
        self.t2 = self._track("t2", "Song B", [self.ar2, self.ar1])   # collaboration
        self.t3 = self._track("t3", "Song C", [self.ar3])

    def _track(self, tid, name, artists):
        t = Track.objects.create(track_id=tid, name=name, duration_ms=180000,
                                 artist=", ".join(x.name for x in artists))
        t.artists.set(artists)
        return t

    def _listen(self, user, track, *when):
        Listen.objects.create(user=user, track=track, played_at=utc(*when))

    # TC-020: top tracks / artists / genres ordered by plays
    def test_top_lists_ordered_by_plays(self):
        for m in (0, 1, 2): self._listen(self.a, self.t1, 2026, 10, 19, 10, m)   # t1 x3
        for m in (3, 4):    self._listen(self.a, self.t2, 2026, 10, 19, 11, m)   # t2 x2 (Beta + Alpha)
        self._listen(self.a, self.t3, 2026, 10, 19, 12, 0)                        # t3 x1
        r = get_daily_rewind(self.a, date(2026, 10, 19))
        self.assertEqual(r["total_plays"], 6)
        self.assertEqual([(t["name"], t["plays"]) for t in r["top_tracks"]],
                         [("Song A", 3), ("Song B", 2), ("Song C", 1)])
        # Alpha: 3 (t1) + 2 (t2 collab) = 5, Beta: 2, Gamma: 1
        self.assertEqual([(x["name"], x["plays"]) for x in r["top_artists"]],
                         [("Alpha", 5), ("Beta", 2), ("Gamma", 1)])
        # indie pop: Alpha 5 + Beta 2 = 7, dream pop: Alpha 5
        self.assertEqual([(g["genre"], g["plays"]) for g in r["top_genres"]],
                         [("indie pop", 7), ("dream pop", 5)])
        self.assertEqual(r["approx_minutes"], 18)

    # TC-021: midnight boundaries, half-open range [start, next start)
    def test_day_boundaries(self):
        self._listen(self.a, self.t1, 2026, 10, 19, 23, 59, 59)
        self._listen(self.a, self.t2, 2026, 10, 20, 0, 0, 0)
        self._listen(self.a, self.t3, 2026, 10, 20, 23, 59, 59)
        self._listen(self.a, self.t1, 2026, 10, 21, 0, 0, 0)
        r = get_daily_rewind(self.a, date(2026, 10, 20))
        self.assertEqual(r["total_plays"], 2)
        self.assertEqual({t["name"] for t in r["top_tracks"]}, {"Song B", "Song C"})

    def test_timezone_changes_which_day_a_play_belongs_to(self):
        self._listen(self.a, self.t1, 2026, 10, 20, 3, 30)    # 23:30 on Oct 19 in New York (EDT)
        self.assertEqual(get_daily_rewind(self.a, date(2026, 10, 19), "America/New_York")["total_plays"], 1)
        self.assertEqual(get_daily_rewind(self.a, date(2026, 10, 20), "America/New_York")["total_plays"], 0)

    def test_dst_day_is_25_hours(self):
        start, end = day_bounds(date(2026, 11, 1), "America/New_York")   # clocks go back
        # compare as instants (UTC); subtracting same-timezone datetimes would compare wall-clock times
        self.assertEqual((end.astimezone(dt_tz.utc) - start.astimezone(dt_tz.utc)).total_seconds(), 25 * 3600)

    # TC-022: empty day
    def test_empty_day(self):
        r = get_daily_rewind(self.a, date(2026, 1, 1))
        self.assertEqual(r["total_plays"], 0)
        self.assertEqual((r["top_tracks"], r["top_artists"], r["top_genres"]), ([], [], []))

    # TC-023: users are isolated
    def test_only_requesting_users_listens(self):
        for m in (0, 1): self._listen(self.a, self.t1, 2026, 10, 19, 9, m)
        for m in range(5): self._listen(self.b, self.t3, 2026, 10, 19, 9, m)
        ra = get_daily_rewind(self.a, date(2026, 10, 19))
        rb = get_daily_rewind(self.b, date(2026, 10, 19))
        self.assertEqual([t["name"] for t in ra["top_tracks"]], ["Song A"])
        self.assertEqual(ra["total_plays"], 2)
        self.assertEqual([t["name"] for t in rb["top_tracks"]], ["Song C"])
        self.assertEqual(rb["total_plays"], 5)

    def test_tracks_without_artist_links_or_genres_do_not_break(self):
        orphan = Track.objects.create(track_id="t9", name="Orphan", artist="?", duration_ms=1000)
        self._listen(self.a, orphan, 2026, 10, 19, 8, 0)
        r = get_daily_rewind(self.a, date(2026, 10, 19))
        self.assertEqual(r["total_plays"], 1)
        self.assertEqual((r["top_artists"], r["top_genres"]), ([], []))

    def test_limit(self):
        for i, t in enumerate((self.t1, self.t2, self.t3)):
            self._listen(self.a, t, 2026, 10, 19, 8, i)
        self.assertEqual(len(get_daily_rewind(self.a, date(2026, 10, 19), limit=2)["top_tracks"]), 2)


class RewindApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", password="Pass-word-123!")
        self.sp = SpotifyUser.objects.create(account=self.user, spotify_id="sp", refresh_token="x")

    def test_requires_login(self):
        self.assertEqual(self.client.get("/api/rewind").status_code, 403)

    # TC-024: invalid input
    def test_bad_date_and_timezone(self):
        self.client.login(username="u", password="Pass-word-123!")
        for q in ("date=2026-02-30", "date=not-a-date", "tz=Mars/Base"):
            r = self.client.get(f"/api/rewind?{q}")
            self.assertEqual(r.status_code, 400, q)
            self.assertIn("error", r.json())

    def test_ok_and_not_connected(self):
        self.client.login(username="u", password="Pass-word-123!")
        r = self.client.get("/api/rewind?date=2026-10-19")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["total_plays"], 0)
        self.sp.delete()
        self.assertEqual(self.client.get("/api/rewind").json(), {"connected": False})
