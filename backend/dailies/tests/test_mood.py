import builtins
from unittest import mock

from django.test import SimpleTestCase

from dailies import mood


def laya_result(choice, probs, conf):
    return {"answers": {"mood": {"choice": choice, "probabilities": probs,
                                 "confidence": conf, "answer_confidence": conf}}}


class MoodTests(SimpleTestCase):
    def test_build_state(self):
        self.assertEqual(mood.build_state("Song A", "Alpha, Beta", ["chill", "lo-fi"]),
                         "Song: Song A\nArtist: Alpha, Beta\nTags: chill, lo-fi")
        self.assertEqual(mood.build_state("Song A", "Alpha", []), "Song: Song A\nArtist: Alpha")

    def test_classify_parses_laya_answers_in_order(self):
        router = mock.Mock()
        router.predict_batch.return_value = [laya_result("chill", {"chill": 0.71234, "sad": 0.28766}, 0.71),
                                             laya_result("angry", {"angry": 0.9}, 0.9)]
        with mock.patch("dailies.mood._get_router", return_value=router):
            out = mood.classify(["s1", "s2"])
        self.assertEqual(out[0], {"mood": "chill", "scores": {"chill": 0.7123, "sad": 0.2877},
                                  "confidence": 0.71})
        self.assertEqual(out[1]["mood"], "angry")
        reqs = router.predict_batch.call_args.args[0]
        self.assertEqual([r["state"] for r in reqs], ["s1", "s2"])
        self.assertEqual(set(reqs[0]["questions"]["mood"]["criteria"]), set(mood.MOODS))
        self.assertEqual(reqs[0]["model"], "english")

    def test_laya_model_env_forces_checkpoint(self):
        router = mock.Mock()
        router.predict_batch.return_value = [laya_result("happy", {}, 0.5)]
        with mock.patch("dailies.mood._get_router", return_value=router), \
             mock.patch.dict("os.environ", {"LAYA_MODEL": "multilingual"}):
            mood.classify(["s"])
        self.assertEqual(router.predict_batch.call_args.args[0][0]["model"], "multilingual")

    def test_available_is_false_without_laya(self):
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "laya":
                raise ImportError(name)
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=fake_import):
            self.assertFalse(mood.available())
