import numpy as np

from phishing_detector.tokenizer import CharTokenizer


def test_fit_orders_characters_by_frequency():
    tokenizer = CharTokenizer().fit(["aab", "a"])
    assert tokenizer.char_index == {"a": 1, "b": 2}
    assert tokenizer.vocab_size == 3


def test_fit_and_encode_are_case_insensitive():
    tokenizer = CharTokenizer().fit(["ABc"])
    np.testing.assert_array_equal(tokenizer.encode(["abc"]), tokenizer.encode(["ABC"]))


def test_encode_left_pads_and_drops_unknown_characters():
    tokenizer = CharTokenizer({"a": 1, "b": 2})
    encoded = tokenizer.encode(["ab?", ""], max_length=4)
    np.testing.assert_array_equal(encoded, [[0, 0, 1, 2], [0, 0, 0, 0]])
    assert encoded.dtype == np.int32


def test_encode_keeps_the_end_of_long_sequences():
    tokenizer = CharTokenizer({"a": 1, "b": 2})
    np.testing.assert_array_equal(tokenizer.encode(["aaab"], max_length=2), [[1, 2]])


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "tokenizer.json"
    CharTokenizer({"a": 1, "/": 2}).save(path)
    assert CharTokenizer.load(path).char_index == {"a": 1, "/": 2}
