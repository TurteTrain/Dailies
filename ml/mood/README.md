# Mood model (PBI 4.2, Sprint 2 fine-tuning)

Training code for the model in `backend/dailies/mood_model/`. It reads a song's **title, artists and
Last.fm tags** and picks one of 4 moods: **upbeat, sad, calm, angry**.

## Results (held-out test set: 2,859 songs by artists never seen in training)

| | Accuracy | Random guess |
|---|---|---|
| All test songs (title + artist + tags) | **41.8%** | 25% |
| Title + artist only (Last.fm doesn't know the artist) | 35.2% | 25% |
| Songs the model is confident on (>= 0.5, 42% of songs) | **50.9%** | 25% |
| Right mood in its top 2 | 68.5% | 50% |

Per mood: upbeat 46%, sad 41%, calm 39%, angry 40%. The app only counts songs with confidence
>= 0.5 (`MIN_CONFIDENCE` in `dailies/mood.py`) toward the mood of the day.

## What we learned (why not 70%, why 4 moods)

1. **Laya didn't fit the server.** The zero-shot Laya model from PR #8 needs ~1.6 GB for its weights,
   and the EC2 box has 2 GB in total, so it was never installed and no song was ever tagged. This
   model is a 23 MB int8 ONNX file using ~100 MB of RAM, with no torch on the server.
2. **Last.fm has almost no per-song tags anymore** (even "'Till I Collapse" has none). So in practice
   the model sees the title, the artist and the *artist's* genre tags.
3. **Mood from metadata has a low ceiling.** Songs by the same artist get nearly the same input, but
   the labels give them different moods: for artists with 3+ test songs, even a model that knew each
   artist's most common mood would be right only ~61% of the time with 8 moods.
4. **8 moods reached only 30%** (random: 12.5%). The model couldn't tell chill/focused/dreamy/romantic
   apart, or happy from energetic, so we merged them into 4 moods.

Getting much higher would need a different signal (audio or lyrics), not more training.

## Data

[MuSe](https://zenodo.org/record/4281165) (Akiki & Burghardt 2021, CC-BY-4.0), v3 from Kaggle
(`cakiki/muse-the-musical-sentiment-dataset`). Each song has "seed" mood words (AllMusic moods that
Last.fm users tagged it with). `label.py` maps the clear seeds to our 4 moods, drops songs whose
seeds disagree, and keeps 5,000 per mood. Sanity check: upbeat songs have the highest MuSe valence,
sad and angry the lowest, angry the highest arousal. The model never sees the seeds.

Split **by artist** 70/15/15 (seed 42), so test scores are on unseen artists.

## Model

`sentence-transformers/all-MiniLM-L6-v2` (22M params, Apache-2.0), fully fine-tuned with a 4-way head:
3 epochs, lr 3e-5, AdamW, class-balanced loss, tags hidden on 15% of training examples. Input text is
built by `dailies.mood.build_state`, the same function the poller uses. Exported to ONNX and
quantized to int8 (same accuracy as the full model). The server runs one song at a time, because
int8 dynamic quantization would otherwise make a song's result depend on its batch.

## Reproduce (~1 hour, mostly Last.fm downloads)

```bash
pip install torch transformers onnx onnxruntime kaggle            # training machine only
kaggle datasets download -d cakiki/muse-the-musical-sentiment-dataset --unzip -p ml/mood/data/kaggle
python ml/mood/label.py                                            # -> data/labeled.jsonl
LASTFM_API_KEY=... python ml/mood/fetch_tags.py                    # artist tags, ~50 min, resumable
python ml/mood/train.py --epochs 3 --lr 3e-5                       # -> runs/<time>/ (~5 min on an M3)
python ml/mood/export.py ml/mood/runs/<time>                       # -> backend/dailies/mood_model/
```

`export.py` checks that the int8 model matches the full model and that the server's code path
(`dailies.mood.classify`) gives identical answers. `baseline_laya.py` scores the old zero-shot Laya
on the same test songs (heavy: needs ~4 GB free memory).
