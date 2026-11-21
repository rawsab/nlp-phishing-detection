"""Integration test against the trained model in models/."""

import pytest

from phishing_detector.config import MODEL_PATH
from phishing_detector.detector import PhishingDetector


@pytest.mark.skipif(not MODEL_PATH.exists(), reason="no trained model in models/")
def test_pretrained_model_scores_known_examples():
    detector = PhishingDetector.from_pretrained()
    phishing, benign = detector.predict(
        [
            # Taken from the PhishTank and whitelist training data respectively.
            "http://2bit.ooo/",
            "https://www.paypal.com/ad/cgi-bin/webscr?cmd=_batch-payment-overview-outside&nav=0.1.1",
        ]
    )
    assert phishing.is_malicious
    assert not benign.is_malicious
