"""The "before" number: zero-shot Laya (what PR #8 shipped) on the same held-out test songs.
The Laya code below is copied from the PR #8 version of backend/dailies/mood.py.

    pip install laya==0.4.15
    python ml/mood/baseline_laya.py runs/<time>
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
sys.path.insert(0, str(HERE))
from dailies.mood import MOODS  # noqa: E402
from train import LABELS, report, text  # noqa: E402

QUESTIONS = {"mood": {"type": "choice", "instructions": "Which mood best describes this song?",
                      "criteria": MOODS}}


def laya_probs(router, states):
    reqs = [{"state": s, "questions": QUESTIONS, "model": "english"} for s in states]
    out = []
    for r in router.predict_batch(reqs):
        p = r["answers"]["mood"].get("probabilities") or {}
        out.append([float(p.get(m, 0.0)) for m in LABELS])
    return np.array(out)


def main():
    from laya import Router
    run = Path(sys.argv[1])
    rows = [json.loads(line) for line in (run / "test_split.jsonl").open()]
    router = Router(max_loaded=1)
    out = {}
    for notags in (False, True):
        name = "laya " + ("no tags" if notags else "normal")
        out[name.replace(" ", "_")] = report(name, rows, laya_probs(router, [text(r, notags) for r in rows]))
    (run / "baseline_laya.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
