import builtins
from unittest import mock

import numpy as np
from django.test import SimpleTestCase

from dailies import mood


class FakeEncoding:
    def __init__(self, n):
        self.ids = [1] * n
        self.attention_mask = [1] * n
        self.type_ids = [0] * n


def fake_model(logits):
    tok = mock.Mock()
    tok.encode_batch.side_effect = lambda states: [FakeEncoding(3) for _ in states]
    sess = mock.Mock()
    rows = iter(logits)                       # mood.classify runs one song per call
    sess.run.side_effect = lambda _out, feed: [np.array([next(rows)] * len(feed["input_ids"]), dtype=np.float32)]
    return tok, sess, ["chill", "sad", "angry"]


class MoodTests(SimpleTestCase):
    def test_build_state(self):
        self.assertEqual(mood.build_state("Song A", "Alpha, Beta", ["chill", "lo-fi"]),
                         "Song: Song A\nArtist: Alpha, Beta\nTags: chill, lo-fi")
        self.assertEqual(mood.build_state("Song A", "Alpha", []), "Song: Song A\nArtist: Alpha")

    def test_classify_returns_top_mood_and_probabilities_in_order(self):
        model = fake_model([[2.0, 0.0, 0.0], [0.0, 0.0, 3.0]])
        with mock.patch("dailies.mood._load", return_value=model):
            out = mood.classify(["s1", "s2"])
        self.assertEqual([o["mood"] for o in out], ["chill", "angry"])
        self.assertAlmostEqual(sum(out[0]["scores"].values()), 1.0, places=3)
        self.assertEqual(out[0]["confidence"], out[0]["scores"]["chill"])
        self.assertAlmostEqual(out[0]["confidence"], 0.787, places=3)
        self.assertEqual([c.args[0] for c in model[0].encode_batch.call_args_list], [["s1"], ["s2"]])
        feed = model[1].run.call_args.args[1]
        self.assertEqual(set(feed), {"input_ids", "attention_mask", "token_type_ids"})
        self.assertEqual(feed["input_ids"].dtype, np.int64)

    def test_shipped_model_labels_match_moods(self):
        if not mood.available():
            self.skipTest("ML requirements not installed")
        _, _, labels = mood._load()
        self.assertEqual(set(labels), set(mood.MOODS))

    def test_available_is_false_without_onnxruntime(self):
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "onnxruntime":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=fake_import):
            self.assertFalse(mood.available())
