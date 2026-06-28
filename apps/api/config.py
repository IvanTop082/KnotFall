import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

DEMO_NETWORK_PATH = DATA_DIR / "demo_network.json"
DEMO_ALERTS_PATH = DATA_DIR / "demo_alerts.json"
DEMO_IMPROVEMENTS_PATH = DATA_DIR / "demo_improvements.json"

DEFAULT_MAX_DEPTH = 5
DEFAULT_MAX_PATHS_PER_ASSET = 3

BREACHPATH_GRAPH_SOURCE = os.getenv("BREACHPATH_GRAPH_SOURCE", "local").lower()
TURINGDB_HOST = os.getenv("TURINGDB_HOST", "http://localhost:16666")
TURINGDB_GRAPH_NAME = os.getenv("TURINGDB_GRAPH_NAME", "breachpath_demo")
