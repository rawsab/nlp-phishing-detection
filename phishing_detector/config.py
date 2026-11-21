"""Project-wide paths and hyperparameters."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "data"
MALICIOUS_URLS_PATH = DATA_DIR / "phishtank_malicious_urls.csv"
BENIGN_URLS_PATH = DATA_DIR / "benign_urls.txt"

MODELS_DIR = PROJECT_ROOT / "models"
MODEL_PATH = MODELS_DIR / "malicious_url_detector.keras"
TOKENIZER_PATH = MODELS_DIR / "tokenizer.json"
# Per-epoch metrics and the split settings of the run that produced MODEL_PATH.
TRAINING_HISTORY_PATH = MODELS_DIR / "training_history.json"

REPORTS_DIR = PROJECT_ROOT / "reports"

# URLs are encoded character by character and padded/truncated to this length.
MAX_SEQUENCE_LENGTH = 128
EMBEDDING_DIM = 128

# Default train / validation / test split. The remainder after validation and
# test is used for training.
VAL_FRACTION = 0.15
TEST_FRACTION = 0.05
SEED = 42

# Probability at or above which a URL is classified as malicious.
MALICIOUS_THRESHOLD = 0.5

API_HOST = "0.0.0.0"
API_PORT = 45000
