import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
SAVED_NETWORKS_DIR = DATA_DIR / "saved_networks"

DEMO_NETWORK_PATH = DATA_DIR / "demo_network.json"
DEMO_ALERTS_PATH = DATA_DIR / "demo_alerts.json"
DEMO_IMPROVEMENTS_PATH = DATA_DIR / "demo_improvements.json"

DEFAULT_MAX_DEPTH = 5
DEFAULT_MAX_PATHS_PER_ASSET = 3

BREACHPATH_GRAPH_SOURCE = os.getenv("BREACHPATH_GRAPH_SOURCE", "local").lower()
BREACHPATH_STORAGE_MODE = os.getenv("BREACHPATH_STORAGE_MODE", "turingdb").lower()
TURINGDB_URL = os.getenv("TURINGDB_URL", os.getenv("TURINGDB_HOST", "http://localhost:16666"))
TURINGDB_HOST = TURINGDB_URL
TURINGDB_GRAPH_NAME = os.getenv("TURINGDB_GRAPH_NAME", "breachpath_demo")
TURINGDB_METADATA_PATH = DATA_DIR / "breachpath_turingdb_metadata.json"
