"""Train the BiLSTM URL classifier.

Run with ``python -m phishing_detector.train``. Writes the best checkpoint, the
fitted tokenizer and the per-epoch training history to ``models/``, replacing
the pretrained model.
"""

import argparse
import json
import time
from pathlib import Path

import keras
import numpy as np

from phishing_detector.config import (
    MODEL_PATH,
    SEED,
    TEST_FRACTION,
    TOKENIZER_PATH,
    TRAINING_HISTORY_PATH,
    VAL_FRACTION,
)
from phishing_detector.data import load_dataset, split_indices
from phishing_detector.model import build_model
from phishing_detector.tokenizer import CharTokenizer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--val-fraction", type=float, default=VAL_FRACTION)
    parser.add_argument("--test-fraction", type=float, default=TEST_FRACTION)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH)
    parser.add_argument("--tokenizer-path", type=Path, default=TOKENIZER_PATH)
    parser.add_argument("--history-path", type=Path, default=TRAINING_HISTORY_PATH)
    args = parser.parse_args()

    keras.utils.set_random_seed(args.seed)

    urls, labels = load_dataset()
    print(f"Loaded {len(urls)} URLs ({sum(labels)} malicious, {len(labels) - sum(labels)} benign)")

    tokenizer = CharTokenizer().fit(urls)
    x = tokenizer.encode(urls)
    y = np.array(labels, dtype=np.float32)
    print(f"Vocabulary: {len(tokenizer.char_index)} characters, input shape: {x.shape}")

    train_idx, val_idx, test_idx = split_indices(
        len(urls), args.val_fraction, args.test_fraction, args.seed
    )
    print(f"Split: {len(train_idx)} train / {len(val_idx)} validation / {len(test_idx)} test")

    model = build_model(tokenizer.vocab_size)
    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=[
            "accuracy",
            keras.metrics.Precision(name="precision"),
            keras.metrics.Recall(name="recall"),
            keras.metrics.AUC(name="auc"),
        ],
    )
    model.summary()

    args.model_path.parent.mkdir(parents=True, exist_ok=True)
    tokenizer.save(args.tokenizer_path)

    start = time.perf_counter()
    history = model.fit(
        x[train_idx],
        y[train_idx],
        validation_data=(x[val_idx], y[val_idx]),
        epochs=args.epochs,
        batch_size=args.batch_size,
        callbacks=[
            keras.callbacks.EarlyStopping(
                monitor="val_loss", patience=2, restore_best_weights=True
            ),
            keras.callbacks.ModelCheckpoint(
                args.model_path, monitor="val_loss", save_best_only=True
            ),
        ],
    )
    training_seconds = time.perf_counter() - start

    print("\nTest set evaluation:")
    results = model.evaluate(x[test_idx], y[test_idx], batch_size=args.batch_size, return_dict=True)
    for name, value in results.items():
        print(f"  {name:<10} {value:.4f}")

    epochs = {name: [float(v) for v in values] for name, values in history.history.items()}
    run = {
        "seed": args.seed,
        "val_fraction": args.val_fraction,
        "test_fraction": args.test_fraction,
        "batch_size": args.batch_size,
        "max_epochs": args.epochs,
        "best_epoch": int(np.argmin(epochs["val_loss"])) + 1,
        "training_seconds": round(training_seconds, 1),
        "history": epochs,
        "test": {name: float(value) for name, value in results.items()},
    }
    args.history_path.write_text(json.dumps(run, indent=2))
    print(f"\nSaved model to {args.model_path} and history to {args.history_path}")


if __name__ == "__main__":
    main()
