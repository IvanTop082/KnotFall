"""Saved network persistence for BreachPath."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
import re
from pathlib import Path
from typing import Any

from ..config import (
    BREACHPATH_STORAGE_MODE,
    SAVED_NETWORKS_DIR,
    TURINGDB_METADATA_PATH,
    TURINGDB_URL,
)
from ..turingdb_integration.http_client import (
    TuringDBHttpClient,
    TuringDBHttpError,
    sdk_available,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STORE_DIR = SAVED_NETWORKS_DIR


class StorageUnavailableError(RuntimeError):
    """Raised when turingdb mode is configured but persistence is unavailable."""


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


def _version_graph_name(network_id: str, version: int) -> str:
    return f"breachpath_{_safe_network_id(network_id)}_v{version}"


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

    def ensure_available(self) -> None:
        status = self.storage_status()
        if not status.get("connected"):
            raise StorageUnavailableError(status.get("message", "Storage is unavailable."))


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
            "mode": "local_fallback",
            "connected": True,
            "repository": "LocalNetworkRepository",
            "turingdb_url": TURINGDB_URL,
            "sdk_available": sdk_available(),
            "http_server_reachable": False,
            "graph_writes_supported": True,
            "graph_storage": "local_json",
            "metadata_storage": "local_json",
            "storage_backend": "local_history_fallback",
            "message": "Local JSON history is active.",
        }

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


class TuringDBMetadataStore:
    def __init__(self, metadata_path: Path = TURINGDB_METADATA_PATH):
        self.metadata_path = metadata_path
        self.metadata_path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict[str, Any]:
        if not self.metadata_path.exists():
            return {"networks": {}}
        return json.loads(self.metadata_path.read_text(encoding="utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        self.metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def get_network(self, network_id: str) -> dict[str, Any] | None:
        return self._read()["networks"].get(_safe_network_id(network_id))

    def list_networks(self) -> list[dict[str, Any]]:
        return list(self._read()["networks"].values())

    def upsert_network(self, payload: dict[str, Any]) -> None:
        data = self._read()
        data["networks"][payload["network_id"]] = payload
        self._write(data)

    def delete_network(self, network_id: str) -> None:
        data = self._read()
        safe_id = _safe_network_id(network_id)
        if safe_id not in data["networks"]:
            raise FileNotFoundError(f"Saved network not found: {safe_id}")
        del data["networks"][safe_id]
        self._write(data)


class TuringDBHttpNetworkRepository(NetworkRepository):
    """Persist BreachPath graph snapshots in TuringDB via Docker HTTP; metadata locally."""

    repository_name = "TuringDBHttpNetworkRepository"

    def __init__(self, url: str, metadata_store: TuringDBMetadataStore | None = None):
        self.url = url.rstrip("/")
        self.client = TuringDBHttpClient(self.url)
        self.metadata_store = metadata_store or TuringDBMetadataStore()

    def save_network(
        self,
        network_id: str,
        name: str | None,
        graph: dict[str, Any],
        message: str,
    ) -> SaveResult:
        self.ensure_available()
        safe_id = _safe_network_id(network_id)
        saved = self.metadata_store.get_network(safe_id)
        version = int(saved.get("version", 0)) + 1 if saved else 1
        node_count, edge_count = _graph_counts(graph)
        created_at = _now_iso()
        commit_id = _commit_id(safe_id, version, graph, message)
        resolved_name = name or (saved or {}).get("name") or safe_id
        turingdb_graph = _version_graph_name(safe_id, version)

        self.client.write_graph_snapshot(
            turingdb_graph,
            graph.get("nodes", []),
            graph.get("edges", []),
        )

        commit = {
            "commit_id": commit_id,
            "version": version,
            "message": message,
            "created_at": created_at,
            "node_count": node_count,
            "edge_count": edge_count,
            "graph_hash": graph_hash(graph),
            "turingdb_graph": turingdb_graph,
            "analyses": [],
        }
        history = [*saved.get("history", [])] if saved else []
        history.append(commit)

        self.metadata_store.upsert_network(
            {
                "network_id": safe_id,
                "name": resolved_name,
                "version": version,
                "updated_at": created_at,
                "latest_turingdb_graph": turingdb_graph,
                "history": history,
                "storage_backend": "turingdb_http",
            }
        )

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
            storage_backend="turingdb_http",
        )

    def get_network(self, network_id: str) -> dict[str, Any]:
        self.ensure_available()
        saved = self.metadata_store.get_network(network_id)
        if not saved:
            raise FileNotFoundError(f"Saved network not found: {_safe_network_id(network_id)}")

        latest_version = int(saved["version"])
        version_snapshot = self.get_version(network_id, latest_version)
        return {
            "network_id": saved["network_id"],
            "name": saved["name"],
            "graph": version_snapshot["graph"],
            "graph_hash": version_snapshot.get("graph_hash") or graph_hash(version_snapshot["graph"]),
            "version": latest_version,
            "commit_id": version_snapshot["commit_id"],
            "updated_at": saved["updated_at"],
            "history": saved.get("history", []),
            "storage_backend": "turingdb_http",
        }

    def list_networks(self) -> list[dict[str, Any]]:
        self.ensure_available()
        summaries = []
        for saved in self.metadata_store.list_networks():
            latest_commit = _find_version(saved, int(saved.get("version", 0)))
            summaries.append(
                {
                    "network_id": saved["network_id"],
                    "name": saved["name"],
                    "version": saved["version"],
                    "updated_at": saved["updated_at"],
                    "node_count": latest_commit.get("node_count", 0) if latest_commit else 0,
                    "edge_count": latest_commit.get("edge_count", 0) if latest_commit else 0,
                    "storage_backend": "turingdb_http",
                }
            )
        return summaries

    def delete_network(self, network_id: str) -> None:
        self.ensure_available()
        self.metadata_store.delete_network(network_id)

    def get_history(self, network_id: str) -> list[dict[str, Any]]:
        saved = self.metadata_store.get_network(network_id)
        if not saved:
            raise FileNotFoundError(f"Saved network not found: {_safe_network_id(network_id)}")
        return [_version_summary(commit) for commit in saved.get("history", [])]

    def get_version(self, network_id: str, version: int) -> dict[str, Any]:
        self.ensure_available()
        saved = self.metadata_store.get_network(network_id)
        if not saved:
            raise FileNotFoundError(f"Saved network not found: {_safe_network_id(network_id)}")

        commit = _find_version(saved, version)
        if not commit:
            raise FileNotFoundError(f"Version {version} not found for network {network_id}")

        turingdb_graph = commit.get("turingdb_graph") or _version_graph_name(network_id, version)
        graph = self.client.read_graph_snapshot(turingdb_graph)

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
            "graph_hash": commit.get("graph_hash", graph_hash(graph)),
            "analysed": bool(commit.get("analyses")),
            "analysis_count": len(commit.get("analyses", [])),
            "storage_backend": "turingdb_http",
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
        self.ensure_available()
        saved = self.metadata_store.get_network(network_id)
        if not saved:
            raise FileNotFoundError(f"Saved network not found: {_safe_network_id(network_id)}")

        commit = _find_version(saved, version)
        if not commit:
            raise FileNotFoundError(f"Version {version} not found for network {network_id}")

        commit.setdefault("analyses", []).append(analysis)
        self.metadata_store.upsert_network(saved)

    def storage_status(self) -> dict[str, Any]:
        reachable, reach_message = self.client.is_reachable()
        sdk = sdk_available()
        graph_writes_supported = reachable

        if not reachable:
            return {
                "mode": "turingdb",
                "connected": False,
                "repository": self.repository_name,
                "turingdb_url": self.url,
                "sdk_available": sdk,
                "http_server_reachable": False,
                "graph_writes_supported": False,
                "graph_storage": "turingdb",
                "metadata_storage": "local_json",
                "storage_backend": "turingdb_http",
                "message": reach_message
                or "TuringDB Docker server is not reachable. Start Docker first.",
            }

        try:
            self.client.list_available_graphs()
            api_known = True
            api_message = (
                "Connected to TuringDB through Docker HTTP API. "
                + ("Python SDK not required." if not sdk else "Python SDK is also available.")
            )
        except TuringDBHttpError as error:
            api_known = False
            api_message = f"TuringDB server reachable but API probe failed: {error}"

        return {
            "mode": "turingdb",
            "connected": api_known and graph_writes_supported,
            "repository": self.repository_name,
            "turingdb_url": self.url,
            "sdk_available": sdk,
            "http_server_reachable": True,
            "graph_writes_supported": graph_writes_supported,
            "graph_storage": "turingdb",
            "metadata_storage": "local_json",
            "storage_backend": "turingdb_http",
            "message": (
                api_message
                if api_known
                else api_message
                + " Graphs stored in TuringDB; metadata stored locally because TuringDB metadata API was not found."
            ),
        }


def get_network_repository() -> NetworkRepository:
    mode = BREACHPATH_STORAGE_MODE
    if mode == "local_fallback":
        return LocalNetworkRepository()
    if mode == "turingdb":
        return TuringDBHttpNetworkRepository(url=TURINGDB_URL)
    raise ValueError(
        f"Invalid BREACHPATH_STORAGE_MODE={mode!r}. Use 'turingdb' or 'local_fallback'."
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
