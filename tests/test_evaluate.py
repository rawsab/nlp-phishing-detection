import numpy as np
import pytest

from phishing_detector.evaluate import (
    compute_metrics,
    plot_confusion_matrix,
    plot_roc_curve,
    plot_training_curves,
)

Y_TRUE = np.array([0, 0, 0, 1, 1, 1])
Y_PROB = np.array([0.1, 0.6, 0.2, 0.9, 0.4, 0.8])


def test_compute_metrics():
    metrics = compute_metrics(Y_TRUE, Y_PROB, threshold=0.5)
    assert metrics["confusion_matrix"] == {"tn": 2, "fp": 1, "fn": 1, "tp": 2}
    assert metrics["accuracy"] == pytest.approx(4 / 6)
    assert metrics["precision"] == pytest.approx(2 / 3)
    assert metrics["recall"] == pytest.approx(2 / 3)
    assert metrics["specificity"] == pytest.approx(2 / 3)
    assert metrics["f1"] == pytest.approx(2 / 3)
    assert metrics["roc_auc"] == pytest.approx(8 / 9)


def test_plots_are_written(tmp_path):
    run = {
        "best_epoch": 2,
        "history": {
            "loss": [0.6, 0.4, 0.35],
            "val_loss": [0.55, 0.45, 0.5],
            "accuracy": [0.7, 0.8, 0.85],
            "val_accuracy": [0.72, 0.79, 0.78],
        },
    }
    metrics = compute_metrics(Y_TRUE, Y_PROB, threshold=0.5)
    plot_training_curves(run, tmp_path / "curves.png")
    plot_roc_curve(Y_TRUE, Y_PROB, metrics, tmp_path / "roc.png")
    plot_confusion_matrix(metrics, tmp_path / "cm.png")
    assert all((tmp_path / name).stat().st_size > 0 for name in ["curves.png", "roc.png", "cm.png"])
