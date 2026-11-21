import numpy as np

from phishing_detector.data import split_indices


def test_split_indices_is_a_disjoint_partition():
    train, val, test = split_indices(100, val_fraction=0.2, test_fraction=0.1, seed=0)
    assert (len(train), len(val), len(test)) == (70, 20, 10)
    np.testing.assert_array_equal(np.sort(np.concatenate([train, val, test])), np.arange(100))


def test_split_indices_is_reproducible():
    first = split_indices(50, 0.2, 0.2, seed=7)
    second = split_indices(50, 0.2, 0.2, seed=7)
    for a, b in zip(first, second, strict=True):
        np.testing.assert_array_equal(a, b)
