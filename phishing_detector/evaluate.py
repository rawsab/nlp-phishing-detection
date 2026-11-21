"""Evaluate the trained model on its held-out test set.

Run with ``python -m phishing_detector.evaluate`` after training. Recreates the
test split recorded in the training history, then writes ``metrics.json`` and
the following figures to ``reports/``:

- ``training_curves.png``: training vs. validation loss and accuracy per epoch
- ``roc_curve.png``: ROC curve with AUC
- ``confusion_matrix.png``: confusion matrix at the decision threshold
"""

import argparse
import json
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.ticker import PercentFormatter
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)

from phishing_detector.config import (
    MALICIOUS_THRESHOLD,
    MODEL_PATH,
    REPORTS_DIR,
    TOKENIZER_PATH,
    TRAINING_HISTORY_PATH,
)
from phishing_detector.data import load_dataset, split_indices

CLASS_NAMES = ["Benign", "Malicious"]

# Chart colours (light surface).
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES_TRAIN = "#2a78d6"
SERIES_VALIDATION = "#eb6834"
SEQUENTIAL_BLUES = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

matplotlib.rcParams.update(
    {
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 10,
        "text.color": INK_PRIMARY,
        "axes.edgecolor": AXIS,
        "axes.labelcolor": INK_SECONDARY,
        "axes.titlecolor": INK_PRIMARY,
        "axes.titlesize": 12,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.titlepad": 10,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRIDLINE,
        "grid.linewidth": 0.8,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelcolor": INK_SECONDARY,
        "ytick.labelcolor": INK_SECONDARY,
        "legend.frameon": False,
        "lines.linewidth": 2,
    }
)


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> dict:
    """Classification metrics for binary labels and predicted probabilities."""
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "threshold": threshold,
        "samples": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "specificity": float(tn / (tn + fp)) if tn + fp else 0.0,
        "f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def plot_training_curves(run: dict, path: Path) -> None:
    history = run["history"]
    epochs = np.arange(1, len(history["loss"]) + 1)
    fig = Figure(figsize=(10, 4), layout="constrained")
    axes = fig.subplots(1, 2)

    for ax, metric, title in [(axes[0], "loss", "Loss"), (axes[1], "accuracy", "Accuracy")]:
        ax.plot(epochs, history[metric], color=SERIES_TRAIN, marker="o", ms=5, label="Training")
        ax.plot(
            epochs,
            history[f"val_{metric}"],
            color=SERIES_VALIDATION,
            marker="o",
            ms=5,
            label="Validation",
        )
        ax.axvline(run["best_epoch"], color=INK_MUTED, linestyle="--", linewidth=1, zorder=0)
        ax.set_title(title)
        ax.set_xlabel("Epoch")
        ax.set_xticks(epochs)
        ax.grid(axis="x", visible=False)

    axes[0].set_ylabel("Binary cross-entropy")
    axes[1].yaxis.set_major_formatter(PercentFormatter(xmax=1, decimals=0))
    axes[1].legend(loc="lower right")
    axes[0].annotate(
        f"best epoch ({run['best_epoch']})",
        xy=(run["best_epoch"], 1),
        xycoords=("data", "axes fraction"),
        xytext=(4, -4),
        textcoords="offset points",
        va="top",
        color=INK_MUTED,
        fontsize=9,
    )
    fig.savefig(path, dpi=150)


def plot_roc_curve(y_true: np.ndarray, y_prob: np.ndarray, metrics: dict, path: Path) -> None:
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    fig = Figure(figsize=(5.5, 5), layout="constrained")
    ax = fig.subplots()

    ax.plot([0, 1], [0, 1], color=INK_MUTED, linestyle="--", linewidth=1, label="Chance")
    ax.plot(fpr, tpr, color=SERIES_TRAIN, label=f"BiLSTM (AUC = {metrics['roc_auc']:.3f})")

    # Operating point at the decision threshold.
    point_fpr = 1 - metrics["specificity"]
    ax.plot(point_fpr, metrics["recall"], "o", ms=7, color=SERIES_TRAIN, mec=SURFACE, mew=2)
    ax.annotate(
        f"threshold {metrics['threshold']}",
        xy=(point_fpr, metrics["recall"]),
        xytext=(10, -14),
        textcoords="offset points",
        color=INK_SECONDARY,
        fontsize=9,
    )

    ax.set_title("ROC curve (test set)")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_xlim(-0.01, 1)
    ax.set_ylim(0, 1.01)
    ax.set_aspect("equal")
    ax.legend(loc="lower right")
    fig.savefig(path, dpi=150)


def plot_confusion_matrix(metrics: dict, path: Path) -> None:
    cm = metrics["confusion_matrix"]
    counts = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
    row_share = counts / counts.sum(axis=1, keepdims=True)

    fig = Figure(figsize=(5, 4.5), layout="constrained")
    ax = fig.subplots()
    cmap = LinearSegmentedColormap.from_list("blues", SEQUENTIAL_BLUES)
    ax.imshow(row_share, cmap=cmap, vmin=0, vmax=1)

    for i in range(2):
        for j in range(2):
            ink = "#ffffff" if row_share[i, j] > 0.5 else INK_PRIMARY
            ax.text(
                j,
                i - 0.08,
                f"{counts[i, j]:,}",
                ha="center",
                va="center",
                color=ink,
                fontsize=15,
                fontweight="semibold",
            )
            ax.text(
                j,
                i + 0.14,
                f"{row_share[i, j]:.1%} of actual",
                ha="center",
                va="center",
                color=ink,
                fontsize=9,
            )

    ax.set_title(f"Confusion matrix (test set, threshold {metrics['threshold']})")
    ax.set_xticks([0, 1], CLASS_NAMES)
    ax.set_yticks([0, 1], CLASS_NAMES)
    ax.set_xlabel("Predicted")
    ax.set_ylabel("Actual")
    ax.grid(False)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.savefig(path, dpi=150)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-path", type=Path, default=MODEL_PATH)
    parser.add_argument("--tokenizer-path", type=Path, default=TOKENIZER_PATH)
    parser.add_argument("--history-path", type=Path, default=TRAINING_HISTORY_PATH)
    parser.add_argument("--output-dir", type=Path, default=REPORTS_DIR)
    parser.add_argument("--threshold", type=float, default=MALICIOUS_THRESHOLD)
    args = parser.parse_args()

    if not args.history_path.exists():
        parser.error(
            f"{args.history_path} not found. Train a model first with "
            "`python -m phishing_detector.train` so the test split is known."
        )
    run = json.loads(args.history_path.read_text())

    # Imported here so that `--help` and the error above don't wait for TensorFlow.
    from phishing_detector.detector import PhishingDetector

    urls, labels = load_dataset()
    _, _, test_idx = split_indices(
        len(urls), run["val_fraction"], run["test_fraction"], run["seed"]
    )
    test_urls = [urls[i] for i in test_idx]
    y_true = np.array([labels[i] for i in test_idx])

    detector = PhishingDetector.from_pretrained(args.model_path, args.tokenizer_path)
    y_prob = detector.model.predict(detector.tokenizer.encode(test_urls), batch_size=1024).ravel()

    metrics = compute_metrics(y_true, y_prob, args.threshold)
    final = {name: values[run["best_epoch"] - 1] for name, values in run["history"].items()}
    report = {
        "test": metrics,
        "best_epoch": run["best_epoch"],
        "epochs_trained": len(run["history"]["loss"]),
        "train_loss": final["loss"],
        "train_accuracy": final["accuracy"],
        "val_loss": final["val_loss"],
        "val_accuracy": final["val_accuracy"],
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "metrics.json").write_text(json.dumps(report, indent=2))
    plot_training_curves(run, args.output_dir / "training_curves.png")
    plot_roc_curve(y_true, y_prob, metrics, args.output_dir / "roc_curve.png")
    plot_confusion_matrix(metrics, args.output_dir / "confusion_matrix.png")

    print(f"\nBest epoch {run['best_epoch']} of {report['epochs_trained']}")
    print(f"  train      loss {final['loss']:.4f}   accuracy {final['accuracy']:.4f}")
    print(f"  validation loss {final['val_loss']:.4f}   accuracy {final['val_accuracy']:.4f}")
    print(f"\nTest set ({metrics['samples']} URLs, threshold {args.threshold})")
    for name in ["accuracy", "precision", "recall", "specificity", "f1", "roc_auc"]:
        print(f"  {name:<12} {metrics[name]:.4f}")
    cm = metrics["confusion_matrix"]
    print(f"  confusion    TN {cm['tn']}  FP {cm['fp']}  FN {cm['fn']}  TP {cm['tp']}")
    print(f"\nWrote metrics and figures to {args.output_dir}")


if __name__ == "__main__":
    main()
