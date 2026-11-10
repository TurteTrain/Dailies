"""Step 2: get each labeled artist's Last.fm tags, cleaned exactly like the production poller does
(dailies.lastfm.clean_tags), so training inputs look like what the model will see in production.

Per-song tags are skipped: Last.fm has none for most songs now (even "'Till I Collapse").
Resumable: artists already in the output are skipped, so you can stop and rerun.

    LASTFM_API_KEY=... python ml/mood/fetch_tags.py
"""
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
from dailies.lastfm import API_URL, clean_tags  # noqa: E402

DATA = HERE / "data"
OUT = DATA / "artist_tags.jsonl"
RATE = 4.5                                     # requests/second, under Last.fm's ~5/s

_lock = threading.Lock()
_next = [0.0]


def _wait_turn():
    with _lock:
        now = time.monotonic()
        t = max(now, _next[0])
        _next[0] = t + 1 / RATE
    time.sleep(max(0.0, t - now))


def artist_tags(name):
    for attempt in range(4):
        _wait_turn()
        try:
            data = requests.get(API_URL, timeout=15, params={
                "method": "artist.gettoptags", "artist": name, "autocorrect": 1,
                "api_key": os.environ["LASTFM_API_KEY"], "format": "json"}).json()
        except (requests.RequestException, ValueError):
            time.sleep(2 ** attempt)
            continue
        if data.get("error") == 6:             # unknown artist
            return []
        if "error" in data:                    # rate limit / server trouble: back off, retry
            time.sleep(2 ** attempt)
            continue
        tags = (data.get("toptags") or {}).get("tag") or []
        return clean_tags([tags] if isinstance(tags, dict) else tags)
    return None


def main():
    artists = sorted({json.loads(line)["artist"] for line in (DATA / "labeled.jsonl").open()})
    done = {json.loads(line)["artist"] for line in OUT.open()} if OUT.exists() else set()
    todo = [a for a in artists if a not in done]
    print(f"{len(artists)} artists, {len(todo)} to fetch", flush=True)
    with OUT.open("a") as f, ThreadPoolExecutor(4) as pool:
        for i, (a, tags) in enumerate(zip(todo, pool.map(artist_tags, todo))):
            if tags is not None:               # None = gave up; a rerun retries it
                f.write(json.dumps({"artist": a, "tags": tags}) + "\n")
            if i % 500 == 0:
                f.flush()
                print(f"{i}/{len(todo)}", flush=True)


if __name__ == "__main__":
    main()
