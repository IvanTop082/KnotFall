"""Saved network persistence for BreachPath.

The local JSON history is the reliable demo fallback. TuringDB write support is
kept isolated because the exact SDK write workflow can vary by environment.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_DIR = PROJECT_ROOT / "data" / "saved_networks"


@dataclass
class SaveResult:
    network_id: str
    name: str
    commit_id: str
    version: int
    status: str
    storage_backend: str
    warning: str | None = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _safe_network_id(network_id: str) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", network_id.strip())
    return safe_id or "network"


def _graph_counts(graph: dict[str, Any]) -> tuple[int, int]:
    return len(graph.get("nodes", [])), len(graph.get("edges", []))


def _commit_id(network_id: str, version: int, graph: dict[str, Any], message: str) -> str:
    payload = json.dumps(
        {
            "network_id": network_id,
            "version": version,
            "graph": graph,
            "message": message,
            "created_at": _now_iso(),
        },
        sort_keys=True,
    )
    return sha256(payload.encode("utf-8")).hexdigest()[:12]


class NetworkRepository:
    def save_network(
        self,
        network_id: str,
        name: str,
        graph: dict[str, Any],
        message: str,
    ) -> SaveResult:
        raise NotImplementedError

    def get_network(self, network_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def list_networks(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_history(self, network_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError


class LocalNetworkRepository(NetworkRepository):
    def __init__(self, store_dir: Path = DEFAULT_STORE_DIR):
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def save_network(
        self,
        network_id: str,
        name: str,
        graph: dict[str, Any],
        message: str,
    ) -> SaveResult:
        safe_id = _safe_network_id(network_id)
        saved = self._read_network_file(safe_id)
        version = int(saved.get("version", 0)) + 1 if saved else 1
        node_count, edge_count = _graph_counts(graph)
        created_at = _now_iso()
        commit_id = _commit_id(safe_id, version, graph, message)

        commit = {
            "commit_id": commit_id,
            "version": version,
            "message": message,
            "created_at": created_at,
            "node_count": node_count,
            "edge_count": edge_count,
        }

        history = [*saved.get("history", [])] if saved else []
        history.append(commit)

        payload = {
            "network_id": safe_id,
            "name": name,
            "graph": graph,
            "version": version,
            "commit_id": commit_id,
            "updated_at": created_at,
            "history": history,
            "storage_backend": "local_history_fallback",
        }

        self._network_path(safe_id).write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )

        return SaveResult(
            network_id=safe_id,
            name=name,
            commit_id=commit_id,
            version=version,
            status="saved",
            storage_backend="local_history_fallback",
        )

    def get_network(self, network_id: str) -> dict[str, Any]:
        safe_id = _safe_network_id(network_id)
        saved = self._read_network_file(safe_id)
        if not saved:
            raise FileNotFoundError(f"Saved network not found: {safe_id}")
        return saved

    def list_networks(self) -> list[dict[str, Any]]:
        summaries = []
        for path in sorted(self.store_dir.glob("*.json")):
            saved = json.loads(path.read_text(encoding="utf-8"))
            node_count, edge_count = _graph_counts(saved.get("graph", {}))
            summaries.append(
                {
                    "network_id": saved["network_id"],
                    "name": saved["name"],
                    "version": saved["version"],
                    "updated_at": saved["updated_at"],
                    "node_count": node_count,
                    "edge_count": edge_count,
                    "storage_backend": saved.get("storage_backend", "local_history_fallback"),
                }
            )
        return summaries

    def get_history(self, network_id: str) -> list[dict[str, Any]]:
        return self.get_network(network_id).get("history", [])

    def _network_path(self, network_id: str) -> Path:
        return self.store_dir / f"{network_id}.json"

    def _read_network_file(self, network_id: str) -> dict[str, Any] | None:
        path = self._network_path(network_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


class TuringDBNetworkRepository(NetworkRepository):
    """Best-effort TuringDB writer with local history as source of truth."""

    def __init__(self, host: str, local_repository: LocalNetworkRepository):
        self.host = host
        self.local_repository = local_repository

    def save_network(
        self,
        network_id: str,
        name: str,
        graph: dict[str, Any],
        message: str,
    ) -> SaveResult:
        result = self.local_repository.save_network(network_id, name, graph, message)
        warning = self._try_write_to_turingdb(result.network_id, graph)

        if warning:
            result.warning = warning
            return result

        result.storage_backend = "turingdb_with_local_history"
        return result

    def get_network(self, network_id: str) -> dict[str, Any]:
        return self.local_repository.get_network(network_id)

    def list_networks(self) -> list[dict[str, Any]]:
        return self.local_repository.list_networks()

    def get_history(self, network_id: str) -> list[dict[str, Any]]:
        return self.local_repository.get_history(network_id)

    def _try_write_to_turingdb(self, network_id: str, graph: dict[str, Any]) -> str | None:
        try:
            from turingdb import TuringDB
        except Exception as error:
            return (
                "Saved to local history fallback. TuringDB SDK was not available "
                f"in this Python environment: {error}"
            )

        graph_name = f"breachpath_{network_id}"

        try:
            client = TuringDB(host=self.host)
            try:
                client.create_graph(graph_name)
            except Exception:
                try:
                    client.load_graph(graph_name)
                except Exception:
                    pass

            client.set_graph(graph_name)
            change = client.new_change()
            client.checkout(change=change)

            for node in graph.get("nodes", []):
                client.query(_create_node_query(node))
            client.query("COMMIT")

            for edge in graph.get("edges", []):
                client.query(_create_edge_query(edge))

            client.query("CHANGE SUBMIT")
            client.checkout()
            return None
        except Exception as error:
            return (
                "Saved to local history fallback. TuringDB write is isolated and "
                f"did not complete for graph {graph_name}: {error}"
            )


def get_network_repository(turingdb_host: str) -> NetworkRepository:
    return TuringDBNetworkRepository(
        host=turingdb_host,
        local_repository=LocalNetworkRepository(),
    )


def _escape_cypher_string(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def _cypher_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    return f"'{_escape_cypher_string(value)}'"


def _safe_identifier(value: Any, fallback: str) -> str:
    identifier = re.sub(r"[^A-Za-z0-9_]", "_", str(value or fallback))
    if identifier and identifier[0].isdigit():
        identifier = f"{fallback}_{identifier}"
    return identifier or fallback


def _cypher_properties(data: dict[str, Any]) -> str:
    parts = [f"{key}: {_cypher_value(value)}" for key, value in data.items()]
    return "{ " + ", ".join(parts) + " }"


def _create_node_query(node: dict[str, Any]) -> str:
    node_label = _safe_identifier(node.get("type") or node.get("node_type"), "BreachPathNode")
    return f"CREATE (:BreachPathNode:{node_label} {_cypher_properties(node)})"


def _create_edge_query(edge: dict[str, Any]) -> str:
    relationship = _safe_identifier(
        edge.get("relationship") or edge.get("edge_type"),
        "RELATES_TO",
    ).upper()
    source_id = _escape_cypher_string(edge["source"])
    target_id = _escape_cypher_string(edge["target"])
    return (
        f"MATCH (source {{id: '{source_id}'}}), (target {{id: '{target_id}'}}) "
        f"CREATE (source)-[:{relationship} {_cypher_properties(edge)}]->(target)"
    )
