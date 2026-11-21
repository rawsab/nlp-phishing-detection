"""Character-level URL tokenizer.

Mirrors the behaviour of the legacy ``keras.preprocessing.text.Tokenizer``
(``char_level=True``) followed by ``pad_sequences``, which the pretrained model
was trained with. That API was removed in Keras 3, so it is reimplemented here
and the fitted vocabulary is saved alongside the model.
"""

import json
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

import numpy as np

from phishing_detector.config import MAX_SEQUENCE_LENGTH


class CharTokenizer:
    """Maps each character of a URL to an integer id (0 is reserved for padding)."""

    def __init__(self, char_index: dict[str, int] | None = None):
        self.char_index = char_index or {}

    @property
    def vocab_size(self) -> int:
        """Number of embedding rows required, including the padding id."""
        return len(self.char_index) + 1

    def fit(self, texts: Iterable[str]) -> "CharTokenizer":
        """Build the vocabulary, assigning lower ids to more frequent characters."""
        counts = Counter()
        for text in texts:
            counts.update(text.lower())
        # Counter.most_common keeps first-seen order for ties, like Keras did.
        self.char_index = {char: i for i, (char, _) in enumerate(counts.most_common(), start=1)}
        return self

    def encode(self, texts: Iterable[str], max_length: int = MAX_SEQUENCE_LENGTH) -> np.ndarray:
        """Encode texts into a ``(n, max_length)`` int32 array.

        Unknown characters are dropped. Sequences are left-padded with zeros, and
        longer sequences keep their last ``max_length`` characters.
        """
        texts = list(texts)
        encoded = np.zeros((len(texts), max_length), dtype=np.int32)
        for row, text in enumerate(texts):
            ids = [self.char_index[c] for c in text.lower() if c in self.char_index]
            ids = ids[-max_length:]
            if ids:
                encoded[row, -len(ids) :] = ids
        return encoded

    def save(self, path: Path) -> None:
        path.write_text(json.dumps({"char_index": self.char_index}, ensure_ascii=False, indent=2))

    @classmethod
    def load(cls, path: Path) -> "CharTokenizer":
        return cls(json.loads(path.read_text())["char_index"])
