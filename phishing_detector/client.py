"""Command-line client for the prediction API.

Example: ``python -m phishing_detector.client https://example.com/login``
"""

import argparse
import json
import sys

import requests

from phishing_detector.config import API_PORT

DEFAULT_ENDPOINT = f"http://localhost:{API_PORT}/predict"


def classify(url: str, endpoint: str = DEFAULT_ENDPOINT, timeout: float = 30) -> dict:
    response = requests.post(endpoint, json={"url": url}, timeout=timeout)
    response.raise_for_status()
    return response.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Classify a URL using the running API.")
    parser.add_argument("url", help="URL to classify")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="prediction endpoint URL")
    args = parser.parse_args()

    try:
        result = classify(args.url, args.endpoint)
    except requests.HTTPError as e:
        sys.exit(f"Request failed ({e.response.status_code}): {e.response.text.strip()}")
    except requests.RequestException as e:
        sys.exit(f"Could not reach the API at {args.endpoint}: {e}")

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
