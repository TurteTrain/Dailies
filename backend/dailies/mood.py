"""Mood of a song, guessed from its name, artists and Last.fm tags by the open-source Laya decision
model (https://huggingface.co/convaiinnovations/laya, Apache-2.0). Laya reads text only; it never
hears the audio, so songs with few tags get weak, low-confidence guesses.

Laya (and torch) live in requirements-ml.txt. Without them installed, available() is False and the
poller skips mood tagging, so the rest of the app works on machines that don't have the model."""
import os

# label -> what the label means (Laya reads these descriptions when choosing)
MOODS = {
    "happy": "upbeat, cheerful, feel-good, positive",
    "sad": "melancholic, heartbreak, lonely, emotional",
    "chill": "relaxed, calm, mellow, laid-back, lo-fi",
    "energetic": "high energy, hype, party, dance, workout",
    "angry": "aggressive, intense, heavy, rage",
    "romantic": "love songs, tender, sensual",
    "focused": "instrumental, study, concentration, ambient",
    "dreamy": "atmospheric, ethereal, nostalgic, spacey",
}
QUESTIONS = {"mood": {"type": "choice", "instructions": "Which mood best describes this song?",
                      "criteria": MOODS}}

# The rewind ignores a track's mood when Laya's confidence is below this.
MIN_CONFIDENCE = 0.4

_router = None


def available():
    try:
        import laya  # noqa: F401
    except ImportError:
        return False
    return True


def build_state(name, artist, tags):
    lines = [f"Song: {name}", f"Artist: {artist}"]
    if tags:
        lines.append("Tags: " + ", ".join(tags))
    return "\n".join(lines)


def _get_router():
    """Load the model once per process (first call downloads ~1.6 GB of weights)."""
    global _router
    if _router is None:
        from laya import Router
        _router = Router(max_loaded=1)       # keep one checkpoint in memory (fits a 4 GB server)
    return _router


def classify(states):
    """One {"mood", "scores", "confidence"} dict per state, in the same order.
    LAYA_MODEL picks the checkpoint. "english" is the default: on test songs it was right more often,
    and when unsure it said so with low confidence, while "multilingual" was confidently wrong.
    Pinning one checkpoint also stops Laya swapping models between songs in different languages."""
    model = os.environ.get("LAYA_MODEL") or "english"
    reqs = [{"state": s, "questions": QUESTIONS, "model": model} for s in states]
    out = []
    for r in _get_router().predict_batch(reqs):
        a = r["answers"]["mood"]
        out.append({"mood": a["choice"],
                    "scores": {k: round(float(v), 4) for k, v in (a.get("probabilities") or {}).items()},
                    "confidence": float(a.get("answer_confidence", a.get("confidence", 0.0)))})
    return out
