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
from urllib.error import URLError
from urllib.request import urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_DIR = PROJECT_ROOT / "data" / "saved_networks"


@dataclass
class SaveResult:
    network_id: str
    name: str | None
    commit_id: str
    version: int
    status: str
    storage_backend: str
    message: str | None = None
    created_at: str | None = None
    node_count: int | None = None
    edge_count: int | None = None
    warning: str | None = None


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _safe_network_id(network_id: str) -> str:
    safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", network_id.strip())
    return safe_id or "network"


def graph_hash(graph: dict[str, Any]) -> str:
    payload = json.dumps(graph, sort_keys=True, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _graph_counts(graph: dict[str, Any]) -> tuple[int, int]:
    return len(graph.get("nodes", [])), len(graph.get("edges", []))


def _commit_id(network_id: str, version: int, graph: dict[str, Any], message: str) -> str:
    payload = json.dumps(
        {
            "network_id": network_id,
            "version": version,
            "graph_hash": graph_hash(graph),
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
        name: str | None,
        graph: dict[str, Any],
        message: str,
    ) -> SaveResult:
        raise NotImplementedError

    def get_network(self, network_id: str) -> dict[str, Any]:
        raise NotImplementedError

    def list_networks(self) -> list[dict[str, Any]]:
        raise NotImplementedError

    def delete_network(self, network_id: str) -> None:
        raise NotImplementedError

    def get_history(self, network_id: str) -> list[dict[str, Any]]:
        raise NotImplementedError

    def get_version(self, network_id: str, version: int) -> dict[str, Any]:
        raise NotImplementedError

    def restore_version(self, network_id: str, version: int) -> SaveResult:
        raise NotImplementedError

    def compare_versions(
        self,
        network_id: str,
        from_version: int,
        to_version: int,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def record_analysis(
        self,
        network_id: str,
        version: int,
        analysis: dict[str, Any],
    ) -> None:
        raise NotImplementedError

    def storage_status(self) -> dict[str, Any]:
        raise NotImplementedError


class LocalNetworkRepository(NetworkRepository):
    def __init__(self, store_dir: Path = DEFAULT_STORE_DIR):
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)

    def save_network(
        self,
        network_id: str,
        name: str | None,
        graph: dict[str, Any],
        message: str,
    ) -> SaveResult:
        safe_id = _safe_network_id(network_id)
        saved = self._read_network_file(safe_id)
        version = int(saved.get("version", 0)) + 1 if saved else 1
        node_count, edge_count = _graph_counts(graph)
        created_at = _now_iso()
        commit_id = _commit_id(safe_id, version, graph, message)
        resolved_name = name or (saved or {}).get("name") or safe_id

        commit = {
            "commit_id": commit_id,
            "version": version,
            "message": message,
            "created_at": created_at,
            "node_count": node_count,
            "edge_count": edge_count,
            "graph_hash": graph_hash(graph),
            "graph": graph,
            "analyses": [],
        }

        history = [*saved.get("history", [])] if saved else []
        history.append(commit)

        payload = {
            "network_id": safe_id,
            "name": resolved_name,
            "graph": graph,
            "graph_hash": commit["graph_hash"],
            "version": version,
            "commit_id": commit_id,
            "updated_at": created_at,
            "history": history,
            "storage_backend": "local_history_fallback",
        }

        self._write_network_file(safe_id, payload)

        return SaveResult(
            network_id=safe_id,
            name=resolved_name,
            commit_id=commit_id,
            version=version,
            message=message,
            created_at=created_at,
            node_count=node_count,
            edge_count=edge_count,
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

    def delete_network(self, network_id: str) -> None:
        safe_id = _safe_network_id(network_id)
        path = self._network_path(safe_id)
        if not path.exists():
            raise FileNotFoundError(f"Saved network not found: {safe_id}")
        path.unlink()

    def get_history(self, network_id: str) -> list[dict[str, Any]]:
        saved = self.get_network(network_id)
        return [_version_summary(commit) for commit in saved.get("history", [])]

    def get_version(self, network_id: str, version: int) -> dict[str, Any]:
        saved = self.get_network(network_id)
        commit = _find_version(saved, version)
        if not commit:
            raise FileNotFoundError(f"Version {version} not found for network {network_id}")

        graph = commit.get("graph")
        if not graph and version == saved.get("version"):
            graph = saved.get("graph", {})
        if not graph:
            raise FileNotFoundError(
                f"Version {version} exists but has no graph snapshot. Save a new version first."
            )

        return {
            "network_id": saved["network_id"],
            "name": saved["name"],
            "graph": graph,
            "version": commit["version"],
            "commit_id": commit["commit_id"],
            "message": commit.get("message", ""),
            "created_at": commit.get("created_at", saved.get("updated_at", "")),
            "node_count": commit.get("node_count", _graph_counts(graph)[0]),
            "edge_count": commit.get("edge_count", _graph_counts(graph)[1]),
            "analysed": bool(commit.get("analyses")),
            "analysis_count": len(commit.get("analyses", [])),
            "storage_backend": saved.get("storage_backend", "local_history_fallback"),
        }

    def restore_version(self, network_id: str, version: int) -> SaveResult:
        version_snapshot = self.get_version(network_id, version)
        return self.save_network(
            network_id=network_id,
            name=version_snapshot["name"],
            graph=version_snapshot["graph"],
            message=f"Restored from version {version}",
        )

    def compare_versions(
        self,
        network_id: str,
        from_version: int,
        to_version: int,
    ) -> dict[str, Any]:
        from_snapshot = self.get_version(network_id, from_version)
        to_snapshot = self.get_version(network_id, to_version)
        return compare_graphs(
            network_id=_safe_network_id(network_id),
            from_version=from_version,
            to_version=to_version,
            from_graph=from_snapshot["graph"],
            to_graph=to_snapshot["graph"],
        )

    def record_analysis(
        self,
        network_id: str,
        version: int,
        analysis: dict[str, Any],
    ) -> None:
        safe_id = _safe_network_id(network_id)
        saved = self.get_network(safe_id)
        commit = _find_version(saved, version)
        if not commit:
            raise FileNotFoundError(f"Version {version} not found for network {safe_id}")

        analyses = commit.setdefault("analyses", [])
        analyses.append(analysis)
        self._write_network_file(safe_id, saved)

    def storage_status(self) -> dict[str, Any]:
        return {
            "status": "local_fallback",
            "storage_backend": "local_history_fallback",
            "turingdb_host": "",
            "message": "Local JSON history is active. TuringDB was not used for this repository.",
        }

    def mark_latest_backend(self, network_id: str, storage_backend: str) -> None:
        safe_id = _safe_network_id(network_id)
        saved = self.get_network(safe_id)
        saved["storage_backend"] = storage_backend
        self._write_network_file(safe_id, saved)

    def _network_path(self, network_id: str) -> Path:
        return self.store_dir / f"{network_id}.json"

    def _read_network_file(self, network_id: str) -> dict[str, Any] | None:
        path = self._network_path(network_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_network_file(self, network_id: str, payload: dict[str, Any]) -> None:
        self._network_path(network_id).write_text(
            json.dumps(payload, indent=2),
            encoding="utf-8",
        )


class TuringDBNetworkRepository(NetworkRepository):
    """Best-effort TuringDB writer with local history as source of truth."""

    def __init__(self, host: str, local_repository: LocalNetworkRepository):
        self.host = host
        self.local_repository = local_repository

    def save_network(
        self,
        network_id: str,
        name: str | None,
        graph: dict[str, Any],
        message: str,
    ) -> SaveResult:
        result = self.local_repository.save_network(network_id, name, graph, message)
        warning = self._try_write_to_turingdb(result.network_id, graph)

        if warning:
            result.warning = warning
            return result

        result.storage_backend = "turingdb_with_local_history"
        self.local_repository.mark_latest_backend(result.network_id, result.storage_backend)
        return result

    def get_network(self, network_id: str) -> dict[str, Any]:
        return self.local_repository.get_network(network_id)

    def list_networks(self) -> list[dict[str, Any]]:
        return self.local_repository.list_networks()

    def delete_network(self, network_id: str) -> None:
        self.local_repository.delete_network(network_id)

    def get_history(self, network_id: str) -> list[dict[str, Any]]:
        return self.local_repository.get_history(network_id)

    def get_version(self, network_id: str, version: int) -> dict[str, Any]:
        return self.local_repository.get_version(network_id, version)

    def restore_version(self, network_id: str, version: int) -> SaveResult:
        result = self.local_repository.restore_version(network_id, version)
        warning = self._try_write_to_turingdb(result.network_id, self.get_network(network_id)["graph"])

        if warning:
            result.warning = warning
            return result

        result.storage_backend = "turingdb_with_local_history"
        self.local_repository.mark_latest_backend(result.network_id, result.storage_backend)
        return result

    def compare_versions(
        self,
        network_id: str,
        from_version: int,
        to_version: int,
    ) -> dict[str, Any]:
        return self.local_repository.compare_versions(network_id, from_version, to_version)

    def record_analysis(
        self,
        network_id: str,
        version: int,
        analysis: dict[str, Any],
    ) -> None:
        self.local_repository.record_analysis(network_id, version, analysis)

    def storage_status(self) -> dict[str, Any]:
        try:
            from turingdb import TuringDB  # noqa: F401
        except Exception as error:
            return {
                "status": "local_fallback",
                "storage_backend": "local_history_fallback",
                "turingdb_host": self.host,
                "message": f"TuringDB SDK is not available: {error}",
            }

        try:
            with urlopen(self.host, timeout=2) as response:
                response.read(100)
        except (OSError, URLError) as error:
            return {
                "status": "local_fallback",
                "storage_backend": "local_history_fallback",
                "turingdb_host": self.host,
                "message": f"TuringDB HTTP API did not respond: {error}",
            }

        return {
            "status": "connected",
            "storage_backend": "turingdb_with_local_history",
            "turingdb_host": self.host,
            "message": "TuringDB HTTP API responded. Local JSON history remains the audit fallback.",
        }

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


def compare_graphs(
    network_id: str,
    from_version: int,
    to_version: int,
    from_graph: dict[str, Any],
    to_graph: dict[str, Any],
) -> dict[str, Any]:
    from_nodes = {_node_id(node): node for node in from_graph.get("nodes", []) if _node_id(node)}
    to_nodes = {_node_id(node): node for node in to_graph.get("nodes", []) if _node_id(node)}
    from_edges = {_edge_key(edge): edge for edge in from_graph.get("edges", []) if _edge_key(edge)}
    to_edges = {_edge_key(edge): edge for edge in to_graph.get("edges", []) if _edge_key(edge)}

    added_nodes = [to_nodes[node_id] for node_id in sorted(to_nodes.keys() - from_nodes.keys())]
    removed_nodes = [
        from_nodes[node_id] for node_id in sorted(from_nodes.keys() - to_nodes.keys())
    ]
    changed_nodes = [
        {
            "id": node_id,
            "label": to_nodes[node_id].get("label", from_nodes[node_id].get("label", node_id)),
            "before_criticality": from_nodes[node_id].get("criticality"),
            "after_criticality": to_nodes[node_id].get("criticality"),
        }
        for node_id in sorted(from_nodes.keys() & to_nodes.keys())
        if from_nodes[node_id].get("criticality") != to_nodes[node_id].get("criticality")
    ]

    added_edges = [to_edges[edge_key] for edge_key in sorted(to_edges.keys() - from_edges.keys())]
    removed_edges = [
        from_edges[edge_key] for edge_key in sorted(from_edges.keys() - to_edges.keys())
    ]
    changed_edges = [
        {
            "id": to_edges[edge_key].get("id", from_edges[edge_key].get("id", edge_key)),
            "source": to_edges[edge_key].get("source"),
            "target": to_edges[edge_key].get("target"),
            "before_relationship": _edge_relationship(from_edges[edge_key]),
            "after_relationship": _edge_relationship(to_edges[edge_key]),
        }
        for edge_key in sorted(from_edges.keys() & to_edges.keys())
        if _edge_relationship(from_edges[edge_key]) != _edge_relationship(to_edges[edge_key])
    ]

    return {
        "network_id": network_id,
        "from_version": from_version,
        "to_version": to_version,
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "changed_nodes": changed_nodes,
        "added_edges": added_edges,
        "removed_edges": removed_edges,
        "changed_edges": changed_edges,
        "summary": {
            "added_nodes": len(added_nodes),
            "removed_nodes": len(removed_nodes),
            "changed_nodes": len(changed_nodes),
            "added_edges": len(added_edges),
            "removed_edges": len(removed_edges),
            "changed_edges": len(changed_edges),
        },
    }


def _version_summary(commit: dict[str, Any]) -> dict[str, Any]:
    analyses = commit.get("analyses", [])
    return {
        "commit_id": commit.get("commit_id", ""),
        "version": int(commit.get("version", 0)),
        "message": commit.get("message", ""),
        "created_at": commit.get("created_at", ""),
        "node_count": int(commit.get("node_count", 0)),
        "edge_count": int(commit.get("edge_count", 0)),
        "analysed": bool(analyses),
        "analysis_count": len(analyses),
    }


def _find_version(saved: dict[str, Any], version: int) -> dict[str, Any] | None:
    for commit in saved.get("history", []):
        if int(commit.get("version", 0)) == version:
            return commit
    return None


def _node_id(node: dict[str, Any]) -> str:
    return str(node.get("id") or "").strip()


def _edge_relationship(edge: dict[str, Any]) -> str:
    return str(edge.get("relationship") or edge.get("edge_type") or "").strip()


def _edge_key(edge: dict[str, Any]) -> str:
    edge_id = str(edge.get("id") or "").strip()
    if edge_id:
        return edge_id
    source = str(edge.get("source") or "").strip()
    target = str(edge.get("target") or "").strip()
    relationship = _edge_relationship(edge)
    if not source or not target:
        return ""
    return f"{source}->{relationship}->{target}"


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
