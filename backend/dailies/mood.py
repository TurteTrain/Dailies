"""Mood of a song, guessed from its name, artists and Last.fm tags by our fine-tuned text model.

The model is all-MiniLM-L6-v2 (Apache-2.0) fine-tuned on songs from the public MuSe dataset
(CC-BY-4.0), labeled from their Last.fm mood tags. Training code and results: ml/mood/README.md.
It ships as a ~23 MB int8 ONNX file in dailies/mood_model/, so the server needs only onnxruntime
and tokenizers (requirements-ml.txt), not torch. It reads text only and never hears the audio,
so songs with few tags get weaker, lower-confidence guesses.

Without the ML requirements installed, available() is False and the poller skips mood tagging,
so the rest of the app works on machines that don't have them."""
import json
from pathlib import Path

# label -> what the label means. The model's own label order is in mood_model/labels.json.
# Only 4 moods: with 8 (happy/energetic and chill/focused/dreamy/romantic split out) the model
# couldn't tell the look-alikes apart from a song's name and tags. See ml/mood/README.md.
MOODS = {
    "upbeat": "happy, energetic, feel-good, party",
    "sad": "melancholic, heartbreak, lonely",
    "calm": "chill, mellow, dreamy, romantic, focused",
    "angry": "aggressive, intense, heavy",
}

# The rewind ignores a track's mood when the model's confidence is below this.
MIN_CONFIDENCE = 0.5          # 4 moods: at 0.5 about 42% of songs qualify, ~51% of those correct

MODEL_DIR = Path(__file__).resolve().parent / "mood_model"
MAX_LEN = 128
# One song per run. The int8 model picks its quantization scale per batch, so batching would
# make a song's mood depend on which other songs it was batched with. ~5 ms per song on CPU.
BATCH = 1

_model = None


def available():
    try:
        import onnxruntime  # noqa: F401
        import tokenizers  # noqa: F401
    except ImportError:
        return False
    return (MODEL_DIR / "model.onnx").exists()


def build_state(name, artist, tags):
    lines = [f"Song: {name}", f"Artist: {artist}"]
    if tags:
        lines.append("Tags: " + ", ".join(tags))
    return "\n".join(lines)


def _load():
    """Load the model once per process (~100 MB of RAM)."""
    global _model
    if _model is None:
        import onnxruntime as ort
        from tokenizers import Tokenizer
        tok = Tokenizer.from_file(str(MODEL_DIR / "tokenizer.json"))
        tok.enable_truncation(MAX_LEN)
        tok.enable_padding()
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1          # small server: leave a core for Django
        sess = ort.InferenceSession(str(MODEL_DIR / "model.onnx"), opts, providers=["CPUExecutionProvider"])
        labels = json.loads((MODEL_DIR / "labels.json").read_text())
        _model = (tok, sess, labels)
    return _model


def _softmax(x):
    import numpy as np
    e = np.exp(x - x.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def classify(states):
    """One {"mood", "scores", "confidence"} dict per state, in the same order.
    confidence is the top mood's probability."""
    import numpy as np
    tok, sess, labels = _load()
    out = []
    for i in range(0, len(states), BATCH):
        enc = tok.encode_batch(states[i:i + BATCH])
        feed = {"input_ids": np.array([e.ids for e in enc], dtype=np.int64),
                "attention_mask": np.array([e.attention_mask for e in enc], dtype=np.int64),
                "token_type_ids": np.array([e.type_ids for e in enc], dtype=np.int64)}
        for p in _softmax(sess.run(None, feed)[0]):
            top = int(p.argmax())
            out.append({"mood": labels[top],
                        "scores": {m: round(float(v), 4) for m, v in zip(labels, p)},
                        "confidence": round(float(p[top]), 4)})
    return out
