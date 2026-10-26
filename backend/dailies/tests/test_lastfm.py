import os
from unittest import mock

import requests
from django.test import SimpleTestCase

from dailies import lastfm


def reply(payload, status=200):
    r = mock.Mock(); r.status_code = status; r.json.return_value = payload
    r.raise_for_status.side_effect = None if status < 400 else requests.HTTPError(str(status))
    return r


TAGS = {"toptags": {"tag": [
    {"name": "Alternative Rock", "count": 100}, {"name": "seen live", "count": 90},
    {"name": "rock", "count": 80}, {"name": "american", "count": 70}, {"name": "2000s", "count": 60},
    {"name": "indie", "count": 55}, {"name": "garage rock", "count": 20},      # below min_count
]}}


@mock.patch.dict(os.environ, {"LASTFM_API_KEY": "k"})
class LastfmTests(SimpleTestCase):
    def test_returns_cleaned_genres(self):
        with mock.patch("requests.get", return_value=reply(TAGS)) as g:
            self.assertEqual(lastfm.top_tags("Cage The Elephant"), ["alternative rock", "rock", "indie"])
        params = g.call_args.kwargs["params"]
        self.assertEqual((params["method"], params["artist"], params["format"]),
                         ("artist.gettoptags", "Cage The Elephant", "json"))

    def test_track_tags_query_the_song(self):
        with mock.patch("requests.get", return_value=reply(TAGS)) as g:
            self.assertEqual(lastfm.track_top_tags("Alpha", "Song A"), ["alternative rock", "rock", "indie"])
        params = g.call_args.kwargs["params"]
        self.assertEqual((params["method"], params["artist"], params["track"]),
                         ("track.gettoptags", "Alpha", "Song A"))

    def test_none_when_no_api_key(self):
        with mock.patch.dict(os.environ, {"LASTFM_API_KEY": ""}), mock.patch("requests.get") as g:
            self.assertIsNone(lastfm.top_tags("X"))
            g.assert_not_called()

    def test_artist_not_found_returns_empty_list(self):
        with mock.patch("requests.get", return_value=reply({"error": 6, "message": "not found"})):
            self.assertEqual(lastfm.top_tags("Nobody"), [])

    def test_other_api_errors_raise(self):
        with mock.patch("requests.get", return_value=reply({"error": 10, "message": "Invalid API key"})):
            with self.assertRaises(lastfm.LastfmError):
                lastfm.top_tags("X")

    def test_http_error_raises(self):
        with mock.patch("requests.get", return_value=reply({}, status=500)):
            with self.assertRaises(requests.HTTPError):
                lastfm.top_tags("X")

    def test_single_tag_object_and_missing_tags(self):
        with mock.patch("requests.get", return_value=reply({"toptags": {"tag": {"name": "punk", "count": 100}}})):
            self.assertEqual(lastfm.top_tags("X"), ["punk"])
        with mock.patch("requests.get", return_value=reply({"toptags": {}})):
            self.assertEqual(lastfm.top_tags("X"), [])

    def test_limit(self):
        many = {"toptags": {"tag": [{"name": f"genre{i}", "count": 100} for i in range(10)]}}
        with mock.patch("requests.get", return_value=reply(many)):
            self.assertEqual(len(lastfm.top_tags("X", limit=3)), 3)
