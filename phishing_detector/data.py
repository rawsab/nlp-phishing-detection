"""Load the labelled URL dataset used for training."""

import csv
from pathlib import Path

import numpy as np

from phishing_detector.config import BENIGN_URLS_PATH, MALICIOUS_URLS_PATH

MALICIOUS = 1
BENIGN = 0


def load_dataset(
    malicious_path: Path = MALICIOUS_URLS_PATH,
    benign_path: Path = BENIGN_URLS_PATH,
) -> tuple[list[str], list[int]]:
    """Return de-duplicated URLs and their labels (1 = malicious, 0 = benign).

    Malicious URLs come from a PhishTank export (CSV with a ``url`` column) and
    benign URLs from a plain-text whitelist with one URL per line. A URL that
    appears in both sources is labelled benign.
    """
    labels: dict[str, int] = {}

    with open(malicious_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            labels[row["url"]] = MALICIOUS

    with open(benign_path, encoding="utf-8") as f:
        for line in f:
            url = line.strip()
            if url:
                labels[url] = BENIGN

    return list(labels), list(labels.values())


def split_indices(
    n: int, val_fraction: float, test_fraction: float, seed: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Shuffle ``range(n)`` and split it into train / validation / test indices.

    The split depends only on its arguments, so evaluation can recreate the exact
    test set a model was trained without.
    """
    indices = np.random.default_rng(seed).permutation(n)
    n_test = int(n * test_fraction)
    n_val = int(n * val_fraction)
    return indices[n_test + n_val :], indices[n_test : n_test + n_val], indices[:n_test]


if __name__ == "__main__":
    urls, targets = load_dataset()
    print(f"Loaded {len(urls)} unique URLs")
    print(f"  malicious: {targets.count(MALICIOUS)}")
    print(f"  benign:    {targets.count(BENIGN)}")
