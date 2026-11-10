"""Step 1: give MuSe songs one of our 8 moods, from the mood words they were collected under.

MuSe v3 (Akiki & Burghardt 2021, CC-BY-4.0; Kaggle cakiki/muse-the-musical-sentiment-dataset)
gives every song 1+ "seeds": AllMusic mood words like "aggressive" or "mellow" that Last.fm users
tagged it with. We map the clear seeds to our moods (ambiguous ones like "dramatic" are ignored)
and drop songs whose seeds point to different moods. The model never sees the seeds: its input is
title + artist + the artist's Last.fm tags, the same as in production.

Output: data/labeled.jsonl, balanced to at most PER_MOOD songs per mood.

    python ml/mood/label.py
"""
import ast
import collections
import csv
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
PER_MOOD = 5000
SEED = 42

# Keep the keys in sync with backend/dailies/mood.py MOODS.
# We started with 8 moods (happy, sad, chill, energetic, angry, romantic, focused, dreamy) but the
# model could only reach ~30% on held-out artists: from title + artist tags, chill/focused/dreamy/
# romantic all look alike, and so do happy/energetic. So they are merged into 4 moods.
SEED_MAP = {
    "upbeat": "cheerful uplifting fun happy optimistic positive playful joyous carefree bright sweet "  # happy
              "euphoric summery gleeful giddy perky jovial celebratory good-natured amiable whimsical "
              "silly sparkling effervescent springlike sugary ebullient "
              "energetic driving exciting hyper rousing manic explosive kinetic thrilling raucous rowdy "  # energetic
              "rambunctious boisterous athletic lively powerful triumphant urgent freewheeling animated "
              "exuberant ecstatic",
    "sad": "gloomy lonely melancholy sad bittersweet poignant wistful tragic somber bleak yearning "
           "sentimental plaintive elegiac regretful weary distraught funereal brooding desperate grim "
           "negative",
    "calm": "calm peaceful relaxed soothing mellow lazy smooth laid-back gentle soft quiet languid warm "  # chill
            "reassuring consoling pastoral "
            "romantic sensual erotic sexy passionate tender intimate sexual "  # romantic
            "meditative cerebral thoughtful reflective introspective technical complex sparse "  # focused
            "philosophical spiritual sacred monastic austere clinical mechanical circular restrained "
            "understated "
            "dreamy ethereal atmospheric spacey trippy hypnotic nostalgic mystical airy shimmering "  # dreamy
            "druggy narcotic mysterious nocturnal lush translucent flowing",
    "angry": "aggressive angry intense harsh fierce hostile confrontational savage menacing defiant "
             "rebellious volatile visceral feral belligerent outraged threatening malevolent angst-ridden "
             "bitter thuggish brash nihilistic",
}
SEED_TO_MOOD = {w: m for m, words in SEED_MAP.items() for w in words.split()}
assert len(SEED_TO_MOOD) == sum(len(w.split()) for w in SEED_MAP.values()), "a seed is in two moods"


def label(seeds):
    """The mood all mapped seeds agree on, or None (no mapped seed, or they disagree)."""
    moods = {SEED_TO_MOOD[s] for s in seeds if s in SEED_TO_MOOD}
    return moods.pop() if len(moods) == 1 else None


def main():
    with open(DATA / "kaggle" / "muse_v3.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    by_mood = collections.defaultdict(list)
    for r in rows:
        y = label(ast.literal_eval(r["seeds"]))
        if y:
            by_mood[y].append({"id": r["lastfm_url"], "track": r["track"], "artist": r["artist"],
                               "label": y, "genre": r["genre"], "valence": float(r["valence_tags"]),
                               "arousal": float(r["arousal_tags"])})
    rng = random.Random(SEED)
    kept = []
    print(f"{len(rows)} MuSe songs")
    for m in SEED_MAP:
        songs = by_mood[m]
        rng.shuffle(songs)
        kept += songs[:PER_MOOD]
        v = sum(s["valence"] for s in songs) / len(songs)
        a = sum(s["arousal"] for s in songs) / len(songs)
        print(f"  {m:10s} {len(songs):6d} labeled, keep {min(len(songs), PER_MOOD)}  "
              f"(mean valence {v:.2f}, arousal {a:.2f})")
    rng.shuffle(kept)
    with (DATA / "labeled.jsonl").open("w") as f:
        for k in kept:
            f.write(json.dumps(k) + "\n")
    print(f"{len(kept)} songs, {len({k['artist'].lower() for k in kept})} artists -> data/labeled.jsonl")


if __name__ == "__main__":
    main()
