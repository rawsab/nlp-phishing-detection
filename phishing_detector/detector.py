"""Inference wrapper combining the tokenizer and the trained model."""

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from phishing_detector.config import MALICIOUS_THRESHOLD, MODEL_PATH, TOKENIZER_PATH
from phishing_detector.tokenizer import CharTokenizer


def is_base_url(url: str) -> bool:
    """True if the URL has no path or query, e.g. ``https://example.com/``."""
    parsed = urlparse(url if "://" in url else f"http://{url}")
    return parsed.path in ("", "/") and not parsed.query


@dataclass(frozen=True)
class Prediction:
    url: str
    malicious_probability: float
    is_malicious: bool
    is_base_url: bool


class PhishingDetector:
    def __init__(self, model, tokenizer: CharTokenizer, threshold: float = MALICIOUS_THRESHOLD):
        self.model = model
        self.tokenizer = tokenizer
        self.threshold = threshold

    @classmethod
    def from_pretrained(
        cls, model_path: Path = MODEL_PATH, tokenizer_path: Path = TOKENIZER_PATH
    ) -> "PhishingDetector":
        import keras

        model = keras.models.load_model(model_path)
        return cls(model, CharTokenizer.load(tokenizer_path))

    def predict(self, urls: list[str]) -> list[Prediction]:
        probabilities = self.model.predict(self.tokenizer.encode(urls), verbose=0).ravel()
        return [
            Prediction(
                url=url,
                malicious_probability=float(p),
                is_malicious=bool(p >= self.threshold),
                is_base_url=is_base_url(url),
            )
            for url, p in zip(urls, probabilities, strict=True)
        ]
