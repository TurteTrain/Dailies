"""Step 4: export the trained model to a small int8 ONNX file the server can run without torch.

Writes backend/dailies/mood_model/{model.onnx, tokenizer.json, labels.json} and checks the
quantized model still agrees with the full one on the test split.

    python ml/mood/export.py runs/<time>
"""
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModelForSequenceClassification, AutoTokenizer

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from train import LABELS, text  # noqa: E402

OUT = HERE.parents[1] / "backend" / "dailies" / "mood_model"


def main():
    run = Path(sys.argv[1])
    tok = AutoTokenizer.from_pretrained(run / "hf")
    model = AutoModelForSequenceClassification.from_pretrained(run / "hf").eval()
    OUT.mkdir(exist_ok=True)

    sample = tok(["Song: x\nArtist: y\nTags: z"], return_tensors="pt")
    fp32 = run / "model_fp32.onnx"
    torch.onnx.export(
        model, (sample["input_ids"], sample["attention_mask"], sample["token_type_ids"]), str(fp32),
        input_names=["input_ids", "attention_mask", "token_type_ids"], output_names=["logits"],
        dynamic_axes={n: {0: "batch", 1: "seq"} for n in ["input_ids", "attention_mask", "token_type_ids"]}
        | {"logits": {0: "batch"}}, opset_version=17, dynamo=False)
    quantize_dynamic(str(fp32), str(OUT / "model.onnx"), weight_type=QuantType.QInt8)
    shutil.copy(run / "hf" / "tokenizer.json", OUT / "tokenizer.json")
    (OUT / "labels.json").write_text(json.dumps(LABELS))

    # Parity check: int8 vs. the full torch model on the test songs.
    rows = [json.loads(line) for line in (run / "test_split.jsonl").open()]
    texts = [text(r) for r in rows] + [text(r, True) for r in rows]
    sess = ort.InferenceSession(str(OUT / "model.onnx"), providers=["CPUExecutionProvider"])
    agree, q_correct, t_correct = 0, 0, 0
    y = [LABELS.index(r["label"]) for r in rows] * 2
    for i in range(0, len(texts), 64):
        enc = tok(texts[i:i + 64], padding=True, truncation=True, max_length=128, return_tensors="np")
        q = sess.run(None, {k: enc[k].astype(np.int64) for k in ["input_ids", "attention_mask", "token_type_ids"]})[0]
        with torch.no_grad():
            t = model(**{k: torch.from_numpy(enc[k]) for k in enc}).logits.numpy()
        agree += int((q.argmax(1) == t.argmax(1)).sum())
        q_correct += int((q.argmax(1) == np.array(y[i:i + 64])).sum())
        t_correct += int((t.argmax(1) == np.array(y[i:i + 64])).sum())
    n = len(texts)
    print(f"int8 agrees with full model on {agree / n:.1%} of {n} inputs; "
          f"acc full {t_correct / n:.1%} vs int8 {q_correct / n:.1%}")
    print(f"model.onnx: {(OUT / 'model.onnx').stat().st_size / 1e6:.1f} MB")

    # The server runs backend/dailies/mood.py (tokenizers + onnxruntime, no transformers).
    # Check it gives the same answers as the int8 model fed by the transformers tokenizer above.
    sys.path.insert(0, str(HERE.parents[1] / "backend"))
    from dailies import mood
    prod = [r["mood"] for r in mood.classify(texts)]
    ref = []
    for t in texts:                            # one at a time, like production (mood.BATCH = 1)
        enc = tok([t], truncation=True, max_length=128, return_tensors="np")
        q = sess.run(None, {k: enc[k].astype(np.int64) for k in ["input_ids", "attention_mask", "token_type_ids"]})[0]
        ref.append(LABELS[int(q.argmax(1)[0])])
    same = sum(a == b for a, b in zip(prod, ref)) / n
    print(f"production mood.classify matches int8 reference on {same:.1%} of inputs")
    assert same > 0.99, "production tokenizer path disagrees with training tokenizer"


if __name__ == "__main__":
    main()
