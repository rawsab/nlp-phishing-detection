import numpy as np
import pytest

from phishing_detector.api import BASE_URL_WARNING, create_app
from phishing_detector.detector import PhishingDetector, is_base_url
from phishing_detector.tokenizer import CharTokenizer


class StubModel:
    """Returns a fixed probability for every input."""

    def __init__(self, probability: float):
        self.probability = probability

    def predict(self, x, verbose=0):
        return np.full((len(x), 1), self.probability)


def make_client(probability: float):
    detector = PhishingDetector(StubModel(probability), CharTokenizer().fit(["http://example.com"]))
    return create_app(detector).test_client()


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://example.com", True),
        ("https://example.com/", True),
        ("example.com", True),
        ("https://example.com/login", False),
        ("https://example.com/?next=x", False),
    ],
)
def test_is_base_url(url, expected):
    assert is_base_url(url) is expected


def test_health():
    assert make_client(0.5).get("/health").get_json() == {"status": "ok"}


def test_predict_malicious():
    body = make_client(0.91).post("/predict", json={"url": "http://evil.example/login"}).get_json()
    assert body["is_malicious"] is True
    assert body["malicious_probability"] == pytest.approx(0.91)
    assert body["warning"] is None


def test_predict_benign_base_url_includes_warning():
    body = make_client(0.1).post("/predict", json={"url": "https://example.com"}).get_json()
    assert body["is_malicious"] is False
    assert body["warning"] == BASE_URL_WARNING


@pytest.mark.parametrize("payload", [None, {}, {"url": ""}, {"url": 42}, ["https://example.com"]])
def test_predict_rejects_invalid_payloads(payload):
    response = make_client(0.5).post("/predict", json=payload)
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_predict_rejects_overly_long_urls():
    response = make_client(0.5).post("/predict", json={"url": "http://a.com/" + "a" * 5000})
    assert response.status_code == 400
