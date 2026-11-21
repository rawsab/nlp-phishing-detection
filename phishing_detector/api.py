"""Flask REST API that classifies URLs as malicious or benign.

Run with ``python -m phishing_detector.api`` and send requests to ``POST /predict``.
"""

import argparse
import logging

from flask import Flask, jsonify, request

from phishing_detector.config import API_HOST, API_PORT
from phishing_detector.detector import PhishingDetector

MAX_URL_LENGTH = 2048
BASE_URL_WARNING = (
    "Base URLs (no path or query) are underrepresented in the training data, "
    "so this prediction is less reliable."
)

logger = logging.getLogger(__name__)


def create_app(detector: PhishingDetector) -> Flask:
    app = Flask(__name__)
    app.json.sort_keys = False

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/predict")
    def predict():
        payload = request.get_json(silent=True)
        url = payload.get("url") if isinstance(payload, dict) else None

        if not isinstance(url, str) or not url.strip():
            return jsonify(error='Request body must be JSON of the form {"url": "<url>"}.'), 400
        url = url.strip()
        if len(url) > MAX_URL_LENGTH:
            return jsonify(error=f"URL must be at most {MAX_URL_LENGTH} characters."), 400

        prediction = detector.predict([url])[0]
        logger.info("%s -> %.4f", url, prediction.malicious_probability)

        return jsonify(
            url=prediction.url,
            malicious_probability=round(prediction.malicious_probability, 4),
            is_malicious=prediction.is_malicious,
            verdict=(
                "The URL is likely to be malicious."
                if prediction.is_malicious
                else "The URL is not likely to be malicious."
            ),
            warning=BASE_URL_WARNING if prediction.is_base_url else None,
        )

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the phishing URL detector over HTTP.")
    parser.add_argument("--host", default=API_HOST)
    parser.add_argument("--port", type=int, default=API_PORT)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Loading model...")
    app = create_app(PhishingDetector.from_pretrained())
    app.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
