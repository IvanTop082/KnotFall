#!/usr/bin/env python3
"""Proof script for BreachPath TuringDB HTTP persistence."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.api.repositories.network_repository import TuringDBHttpNetworkRepository
from apps.api.turingdb_integration.http_client import TuringDBHttpClient


TURINGDB_URL = os.getenv("TURINGDB_URL", "http://localhost:16666")
TEST_NETWORK_ID = f"http_persistence_proof_{int(time.time())}"


def step(title: str) -> None:
    print(f"\n== {title} ==")


def fail(message: str, code: int = 1) -> None:
    print(f"\nFAIL: {message}")
    sys.exit(code)


def graph_with_nodes(count: int) -> dict:
    nodes = []
    edges = []
    for index in range(count):
        node_id = f"proof-node-{index + 1}"
        nodes.append(
            {
                "id": node_id,
                "label": f"Proof Node {index + 1}",
                "node_type": "workstation",
                "template_type": "workstation",
                "criticality": "medium",
                "zone": "internal",
                "is_internet_exposed": False,
                "has_admin_privileges": False,
                "notes": f"proof node {index + 1}",
            }
        )
        if index > 0:
            edges.append(
                {
                    "id": f"proof-edge-{index}",
                    "source": f"proof-node-{index}",
                    "target": node_id,
                    "edge_type": "can_access",
                    "label": "can access",
                    "risk_weight": 50,
                    "direction": "directional",
                    "risk_can_spread_both_ways": False,
                    "notes": "",
                }
            )

    return {
        "metadata": {"name": "HTTP persistence proof", "source": "proof-script"},
        "nodes": nodes,
        "edges": edges,
    }


def main() -> None:
    print("BreachPath TuringDB HTTP persistence proof")
    print(f"TuringDB URL: {TURINGDB_URL}")

    step("1. Check TuringDB HTTP server reachability")
    try:
        request = urllib.request.Request(
            f"{TURINGDB_URL}/list_avail_graphs",
            data=b"{}",
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            body = response.read().decode("utf-8")
        print(f"POST /list_avail_graphs -> {response.status}")
        print(body[:300])
    except urllib.error.HTTPError as error:
        fail(f"TuringDB HTTP probe failed with HTTP {error.code}: {error.read().decode()}")
    except Exception as error:
        fail(f"TuringDB is not reachable at {TURINGDB_URL}: {error}")

    step("2. Check documented usable TuringDB endpoint")
    client = TuringDBHttpClient(TURINGDB_URL)
    graphs = client.list_available_graphs()
    print(f"Available graphs: {graphs[:10]}{'...' if len(graphs) > 10 else ''}")

    step("3-5. Save proof network v1 and v2 with different node counts")
    metadata_path = PROJECT_ROOT / "data" / "breachpath_turingdb_metadata_proof.json"
    if metadata_path.exists():
        metadata_path.unlink()

    from apps.api.repositories.network_repository import TuringDBMetadataStore

    repository = TuringDBHttpNetworkRepository(
        url=TURINGDB_URL,
        metadata_store=TuringDBMetadataStore(metadata_path),
    )
    status = repository.storage_status()
    print(json.dumps(status, indent=2))
    if not status.get("connected"):
        fail(status.get("message", "Storage is not connected"))

    v1 = repository.save_network(
        network_id=TEST_NETWORK_ID,
        name="HTTP Proof Network",
        graph=graph_with_nodes(2),
        message="proof v1",
    )
    print(f"Saved v1: {v1.version} nodes={v1.node_count}")

    time.sleep(0.5)
    v2 = repository.save_network(
        network_id=TEST_NETWORK_ID,
        name="HTTP Proof Network",
        graph=graph_with_nodes(4),
        message="proof v2",
    )
    print(f"Saved v2: {v2.version} nodes={v2.node_count}")

    step("6. List versions")
    history = repository.get_history(TEST_NETWORK_ID)
    print(json.dumps(history, indent=2))
    if len(history) < 2:
        fail("Expected at least two saved versions in metadata history")

    step("7-8. Load v1 and v2")
    loaded_v1 = repository.get_version(TEST_NETWORK_ID, 1)
    loaded_v2 = repository.get_version(TEST_NETWORK_ID, 2)
    print(f"Loaded v1 nodes={len(loaded_v1['graph']['nodes'])}")
    print(f"Loaded v2 nodes={len(loaded_v2['graph']['nodes'])}")

    step("9. Verify versions differ")
    if len(loaded_v1["graph"]["nodes"]) == len(loaded_v2["graph"]["nodes"]):
        fail("v1 and v2 loaded the same node count; snapshot versioning did not work")
    if len(loaded_v1["graph"]["nodes"]) != 2 or len(loaded_v2["graph"]["nodes"]) != 4:
        fail("Loaded graph node counts do not match saved snapshots")

    print("\nPASS: TuringDB HTTP persistence works for save/list/load/version snapshots.")
    print("Graph snapshots are stored in TuringDB graphs named like:")
    print("  breachpath_http_persistence_proof_v1")
    print("  breachpath_http_persistence_proof_v2")
    print(f"Version metadata is stored locally at: {metadata_path}")


if __name__ == "__main__":
    main()
