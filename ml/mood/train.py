"""Step 3: fine-tune a small text model to predict a song's mood, then export it for the server.

Model: sentence-transformers/all-MiniLM-L6-v2 (22M params, Apache-2.0) + an 8-way classifier head.
Input text is built by backend/dailies/mood.py build_state, the same function production uses.

Honesty rules:
  - Split by ARTIST (70/15/15), so the test set has no artist the model trained on.
  - Labels come from MuSe's seed mood words (label.py), which the model never sees. Its input is
    title + artist + the artist's Last.fm tags, as in production.
  - Two test scores: "normal" (with artist tags) and "no tags" (title + artist only, which is what
    the model gets when Last.fm doesn't know the artist). Training hides the tags TAG_DROPOUT of the
    time so the model handles both.

    python ml/mood/train.py                  # trains, evaluates, writes runs/<time>/
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "backend"))
sys.path.insert(0, str(HERE))
from dailies.mood import MOODS, build_state  # noqa: E402

BASE = "sentence-transformers/all-MiniLM-L6-v2"
LABELS = list(MOODS)
TAG_DROPOUT = 0.15
SEED = 42


def text(row, notags=False):
    return build_state(row["track"], row["artist"], [] if notags else row["artist_tags"])


def load_rows():
    tags = {}
    for line in (HERE / "data" / "artist_tags.jsonl").open():
        a = json.loads(line)
        tags[a["artist"]] = a["tags"]
    rows = []
    for line in (HERE / "data" / "labeled.jsonl").open():
        r = json.loads(line)
        if r["artist"] in tags:               # skip the few artists whose fetch failed
            rows.append(r | {"artist_tags": tags[r["artist"]]})
    return rows


def split_by_artist(rows):
    artists = sorted({r["artist"].lower() for r in rows})
    random.Random(SEED).shuffle(artists)
    n = len(artists)
    test_a = set(artists[: int(0.15 * n)])
    val_a = set(artists[int(0.15 * n): int(0.30 * n)])
    out = {"train": [], "val": [], "test": []}
    for r in rows:
        a = r["artist"].lower()
        out["test" if a in test_a else "val" if a in val_a else "train"].append(r)
    return out


@torch.no_grad()
def predict(model, tok, texts, device, bs=64):
    model.eval()
    probs = []
    for i in range(0, len(texts), bs):
        enc = tok(texts[i:i + bs], padding=True, truncation=True, max_length=128, return_tensors="pt").to(device)
        probs.append(torch.softmax(model(**enc).logits.float(), -1).cpu().numpy())
    return np.concatenate(probs) if probs else np.zeros((0, len(LABELS)))


def report(name, rows, probs):
    y = np.array([LABELS.index(r["label"]) for r in rows])
    pred = probs.argmax(1)
    acc = float((pred == y).mean())
    per = {m: float((pred[y == i] == i).mean()) if (y == i).any() else None for i, m in enumerate(LABELS)}
    conf = probs.max(1)
    hi = conf >= 0.4
    print(f"{name:14s} acc {acc:.1%}  (n={len(rows)})  | conf>=0.4: {hi.mean():.0%} of songs, "
          f"acc {float((pred[hi] == y[hi]).mean()) if hi.any() else 0:.1%}")
    print("    per mood: " + "  ".join(f"{m} {v:.0%}" for m, v in per.items() if v is not None))
    cm = np.zeros((len(LABELS), len(LABELS)), int)
    for a, b in zip(y, pred):
        cm[a, b] += 1
    return {"accuracy": acc, "per_mood": per, "n": len(rows), "confusion": cm.tolist(),
            "share_conf_ge_0.4": float(hi.mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--lr", type=float, default=5e-5)
    ap.add_argument("--bs", type=int, default=32)
    args = ap.parse_args()

    random.seed(SEED); np.random.seed(SEED); torch.manual_seed(SEED)
    device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
    rows = load_rows()
    sp = split_by_artist(rows)
    print({k: len(v) for k, v in sp.items()}, "device", device)

    tok = AutoTokenizer.from_pretrained(BASE)
    model = AutoModelForSequenceClassification.from_pretrained(
        BASE, num_labels=len(LABELS), id2label=dict(enumerate(LABELS)),
        label2id={m: i for i, m in enumerate(LABELS)}).to(device)

    counts = np.bincount([LABELS.index(r["label"]) for r in sp["train"]], minlength=len(LABELS))
    weights = torch.tensor(len(sp["train"]) / (len(LABELS) * np.maximum(counts, 1)), dtype=torch.float32)
    loss_fn = torch.nn.CrossEntropyLoss(weight=weights.to(device))
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.01)
    steps = args.epochs * ((len(sp["train"]) + args.bs - 1) // args.bs)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=steps, pct_start=0.1)

    def collate(batch):
        texts = [text(r, notags=random.random() < TAG_DROPOUT) for r in batch]
        enc = tok(texts, padding=True, truncation=True, max_length=128, return_tensors="pt")
        enc["labels"] = torch.tensor([LABELS.index(r["label"]) for r in batch])
        return enc

    run = HERE / "runs" / time.strftime("%Y%m%d-%H%M%S")
    run.mkdir(parents=True)
    best, best_state = -1, None
    for ep in range(args.epochs):
        model.train()
        total = 0.0
        for b in DataLoader(sp["train"], batch_size=args.bs, shuffle=True, collate_fn=collate):
            b = {k: v.to(device) for k, v in b.items()}
            y = b.pop("labels")
            loss = loss_fn(model(**b).logits, y)
            opt.zero_grad(); loss.backward(); opt.step(); sched.step()
            total += loss.item() * len(y)
        val_rows = sp["val"]
        vp = predict(model, tok, [text(r) for r in val_rows], device)
        vs = predict(model, tok, [text(r, True) for r in val_rows], device)
        y = np.array([LABELS.index(r["label"]) for r in val_rows])
        va, vsa = float((vp.argmax(1) == y).mean()), float((vs.argmax(1) == y).mean())
        print(f"epoch {ep + 1}: train loss {total / len(sp['train']):.3f}  val acc {va:.1%}  no tags {vsa:.1%}", flush=True)
        if 2 * va + vsa > best:                 # pick the epoch that does best, mostly with tags
            best = 2 * va + vsa
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    results = {"base": BASE, "args": vars(args), "split": {k: len(v) for k, v in sp.items()},
               "train_counts": dict(zip(LABELS, counts.tolist()))}
    print("\n== held-out test (artists never seen in training) ==")
    results["test_normal"] = report("test normal", sp["test"], predict(model, tok, [text(r) for r in sp["test"]], device))
    results["test_notags"] = report("test no tags", sp["test"],
                                    predict(model, tok, [text(r, True) for r in sp["test"]], device))
    with (run / "test_split.jsonl").open("w") as f:
        for r in sp["test"]:
            f.write(json.dumps(r) + "\n")

    model.to("cpu").save_pretrained(run / "hf")
    tok.save_pretrained(run / "hf")
    (run / "results.json").write_text(json.dumps(results, indent=2))
    print("saved", run)


if __name__ == "__main__":
    main()
