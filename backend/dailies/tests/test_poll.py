import io
import os
from unittest import mock

import requests
from django.core.management import call_command
from django.test import TestCase

from dailies.models import Artist, Listen, SpotifyUser, Track


def item(tid, name, artists, played_at):
    return {"played_at": played_at,
            "track": {"id": tid, "name": name, "duration_ms": 200000,
                      "artists": [{"id": a[0], "name": a[1]} for a in artists]}}


ITEMS = [
    item("t1", "Song A", [("ar1", "Alpha")], "2026-10-19T10:00:00.000Z"),
    item("t2", "Song B", [("ar2", "Beta"), ("ar1", "Alpha")], "2026-10-19T10:05:00.000Z"),
    item("t1", "Song A", [("ar1", "Alpha")], "2026-10-19T10:10:00.000Z"),
]


def http_error(status):
    resp = requests.Response(); resp.status_code = status
    return requests.HTTPError(f"{status}", response=resp)


class PollHelpers:
    def setUp(self):
        SpotifyUser.objects.create(spotify_id="u1", refresh_token="RT")

    def run_poll(self, items=ITEMS, artist_side_effect=None, mood_available=False):
        genres = {"ar1": ["indie pop"], "ar2": []}
        with mock.patch("dailies.mood.available", return_value=mood_available), \
             mock.patch("dailies.spotify.refresh_access_token", return_value={"access_token": "AT"}), \
             mock.patch("dailies.spotify.get_recently_played", return_value=items), \
             mock.patch("dailies.spotify.get_artist",
                        side_effect=artist_side_effect or (lambda tok, aid: {"id": aid, "genres": genres.get(aid)})) as ga:
            out, err = io.StringIO(), io.StringIO()
            call_command("poll_spotify", stdout=out, stderr=err)
        return ga, out.getvalue(), err.getvalue()


class PollTests(PollHelpers, TestCase):
    def test_saves_listens_tracks_artist_links_and_genres(self):
        ga, out, _ = self.run_poll()
        self.assertIn("fetched 3 plays", out)
        self.assertEqual(Listen.objects.count(), 3)
        self.assertEqual(Track.objects.count(), 2)
        self.assertEqual(Artist.objects.count(), 2)
        self.assertEqual(set(Track.objects.get(pk="t2").artists.values_list("pk", flat=True)), {"ar1", "ar2"})
        self.assertEqual(Artist.objects.get(pk="ar1").genres, ["indie pop"])
        self.assertIsNotNone(Artist.objects.get(pk="ar2").genres_fetched_at)   # empty list still counts as fetched
        self.assertEqual(ga.call_count, 2)

    def test_second_run_adds_nothing_and_does_not_refetch_artists(self):
        self.run_poll()
        ga, _, _ = self.run_poll()
        self.assertEqual((Listen.objects.count(), Track.objects.count(), Artist.objects.count()), (3, 2, 2))
        self.assertEqual(ga.call_count, 0)

    def test_missing_genres_field_is_stored_as_empty_list(self):
        self.run_poll(artist_side_effect=lambda tok, aid: {"id": aid})     # e.g. Spotify drops the field
        self.assertEqual(Artist.objects.get(pk="ar1").genres, [])
        self.assertIsNotNone(Artist.objects.get(pk="ar1").genres_fetched_at)

    def test_artist_lookup_failure_does_not_lose_listens(self):
        _, _, err = self.run_poll(artist_side_effect=http_error(500))
        self.assertEqual(Listen.objects.count(), 3)
        self.assertIsNone(Artist.objects.get(pk="ar1").genres_fetched_at)   # retried next run
        self.assertIn("artist", err)

    def test_rate_limit_stops_further_lookups(self):
        ga, _, _ = self.run_poll(artist_side_effect=http_error(429))
        self.assertEqual(ga.call_count, 1)

    def test_local_file_without_id_is_skipped(self):
        local = {"played_at": "2026-10-19T09:00:00.000Z",
                 "track": {"id": None, "name": "My mp3", "duration_ms": 1000, "artists": []}}
        self.run_poll(items=ITEMS + [local])
        self.assertEqual(Listen.objects.count(), 3)


class GenreSourceTests(PollHelpers, TestCase):
    """With LASTFM_API_KEY set, genres come from Last.fm and Spotify's artist endpoint is not called."""

    def run_with_lastfm(self, lastfm_return=None, lastfm_side_effect=None):
        with mock.patch.dict(os.environ, {"LASTFM_API_KEY": "k"}), \
             mock.patch("dailies.lastfm.top_tags", return_value=lastfm_return,
                        side_effect=lastfm_side_effect) as lf:
            ga, out, err = self.run_poll()
        return ga, lf, err

    def test_lastfm_genres_are_stored_and_spotify_artist_endpoint_skipped(self):
        ga, lf, _ = self.run_with_lastfm(lastfm_return=["alternative rock", "indie"])
        self.assertEqual(ga.call_count, 0)
        self.assertEqual(lf.call_count, 2)
        self.assertEqual(Artist.objects.get(pk="ar1").genres, ["alternative rock", "indie"])
        self.assertIsNotNone(Artist.objects.get(pk="ar1").genres_fetched_at)

    def test_lastfm_is_queried_by_artist_name(self):
        _, lf, _ = self.run_with_lastfm(lastfm_return=["rock"])
        self.assertEqual({c.args[0] for c in lf.call_args_list}, {"Alpha", "Beta"})

    def test_lastfm_failure_leaves_artist_unfetched_for_retry(self):
        _, _, err = self.run_with_lastfm(lastfm_side_effect=requests.ConnectionError("down"))
        self.assertIsNone(Artist.objects.get(pk="ar1").genres_fetched_at)
        self.assertEqual(Listen.objects.count(), 3)           # listens are unaffected
        self.assertIn("last.fm", err)

    def test_artist_unknown_to_lastfm_is_cached_as_empty(self):
        self.run_with_lastfm(lastfm_return=[])
        self.assertEqual(Artist.objects.get(pk="ar1").genres, [])
        self.assertIsNotNone(Artist.objects.get(pk="ar1").genres_fetched_at)

    def test_without_api_key_spotify_is_used(self):
        with mock.patch.dict(os.environ, {"LASTFM_API_KEY": ""}):
            ga, _, _ = self.run_poll()
        self.assertEqual(ga.call_count, 2)
        self.assertEqual(Artist.objects.get(pk="ar1").genres, ["indie pop"])


def fake_classify(states):
    return [{"mood": "chill", "scores": {"chill": 0.8, "sad": 0.2}, "confidence": 0.8} for _ in states]


class MoodTaggingTests(PollHelpers, TestCase):
    """The mood step runs after genres, tags each track once, and never blocks saving listens."""

    def run_with_mood(self, track_tags=None, track_tags_side_effect=None):
        with mock.patch.dict(os.environ, {"LASTFM_API_KEY": "k"}), \
             mock.patch("dailies.lastfm.top_tags", return_value=["indie pop"]), \
             mock.patch("dailies.lastfm.track_top_tags", return_value=track_tags,
                        side_effect=track_tags_side_effect) as tt, \
             mock.patch("dailies.mood.classify", side_effect=fake_classify) as cl:
            _, out, err = self.run_poll(mood_available=True)
        return tt, cl, out, err

    def test_tracks_are_tagged_with_song_and_artist_tags(self):
        tt, cl, out, _ = self.run_with_mood(track_tags=["sad", "indie pop"])
        self.assertIn("mood: tagged 2 tracks", out)
        t1 = Track.objects.get(pk="t1")
        self.assertEqual((t1.mood, t1.mood_confidence), ("chill", 0.8))
        self.assertEqual(t1.mood_scores, {"chill": 0.8, "sad": 0.2})
        self.assertIsNotNone(t1.mood_tagged_at)
        states = cl.call_args.args[0]
        self.assertIn("Tags: sad, indie pop", states[0])               # song tags first, deduped
        self.assertEqual({c.args for c in tt.call_args_list}, {("Alpha", "Song A"), ("Beta", "Song B")})

    def test_second_run_does_not_retag(self):
        self.run_with_mood(track_tags=[])
        _, cl, _, _ = self.run_with_mood(track_tags=[])
        self.assertEqual(cl.call_count, 0)

    def test_track_waits_until_its_artists_have_tags(self):
        with mock.patch.dict(os.environ, {"LASTFM_API_KEY": "k"}), \
             mock.patch("dailies.lastfm.top_tags", side_effect=requests.ConnectionError("down")), \
             mock.patch("dailies.lastfm.track_top_tags", return_value=[]), \
             mock.patch("dailies.mood.classify", side_effect=fake_classify) as cl:
            self.run_poll(mood_available=True)
        self.assertEqual(cl.call_count, 0)
        self.assertIsNone(Track.objects.get(pk="t1").mood_tagged_at)

    def test_lastfm_failure_leaves_track_for_retry(self):
        _, cl, _, err = self.run_with_mood(track_tags_side_effect=requests.ConnectionError("down"))
        self.assertEqual(cl.call_count, 0)
        self.assertIsNone(Track.objects.get(pk="t1").mood_tagged_at)
        self.assertEqual(Listen.objects.count(), 3)
        self.assertIn("last.fm Song A", err)

    def test_skipped_when_laya_not_installed(self):
        with mock.patch("dailies.mood.classify") as cl:
            _, out, _ = self.run_poll(mood_available=False)
        self.assertEqual(cl.call_count, 0)
        self.assertIn("laya not installed", out)
        self.assertEqual(Listen.objects.count(), 3)
