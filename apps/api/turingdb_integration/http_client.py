"""HTTP client for the TuringDB Docker REST API (no Python SDK required)."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


NODE_SNAPSHOT_PROPERTIES = [
    "label",
    "type",
    "node_type",
    "template_type",
    "criticality",
    "zone",
    "description",
    "is_internet_exposed",
    "has_admin_privileges",
    "notes",
]


EDGE_SNAPSHOT_PROPERTIES = [
    "id",
    "edge_type",
    "relationship",
    "label",
    "risk_weight",
    "direction",
    "risk_can_spread_both_ways",
    "description",
    "notes",
]


class TuringDBHttpError(RuntimeError):
    def __init__(self, message: str, *, error_code: str | None = None):
        super().__init__(message)
        self.error_code = error_code


class TuringDBHttpClient:
    DEFAULT_TIMEOUT = 180

    def __init__(self, base_url: str, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._graph = "default"
        self._change: str | None = None
        self._commit: str | None = None

    def set_graph(self, graph_name: str) -> None:
        self._graph = graph_name

    def get_graph(self) -> str:
        return self._graph

    def checkout_main(self) -> None:
        self._change = None
        self._commit = None

    def set_change(self, change_id: int | str) -> None:
        if isinstance(change_id, int):
            self._change = f"{change_id:x}"
        else:
            self._change = str(change_id)

    def ping(self) -> dict[str, Any]:
        return self._post_json("list_avail_graphs")

    def is_reachable(self) -> tuple[bool, str | None]:
        try:
            self.ping()
            return True, None
        except (OSError, URLError) as error:
            return False, f"TuringDB Docker server is not reachable: {error}"
        except TuringDBHttpError as error:
            return True, str(error)

    def list_available_graphs(self) -> list[str]:
        payload = self._post_json("list_avail_graphs")
        data = payload.get("data", [])
        if isinstance(data, list) and data and isinstance(data[0], list):
            return [str(name) for name in data[0]]
        if isinstance(data, list):
            return [str(name) for name in data]
        return []

    def list_loaded_graphs(self) -> list[str]:
        payload = self._post_json("list_loaded_graphs")
        data = payload.get("data", [])
        if not data:
            return []
        first = data[0]
        if isinstance(first, list) and first and isinstance(first[0], list):
            return [str(name) for name in first[0]]
        return []

    def is_graph_loaded(self, graph_name: str | None = None) -> bool:
        graph = graph_name or self._graph
        payload = self._post_json("is_graph_loaded", params={"graph": graph})
        return bool(payload.get("data"))

    def load_graph(self, graph_name: str) -> None:
        payload = self._post_json("load_graph", params={"graph": graph_name})
        error = payload.get("error")
        if error and error not in {"GRAPH_ALREADY_EXISTS"}:
            raise TuringDBHttpError(
                f"Could not load graph {graph_name}: {error}",
                error_code=str(error),
            )

    def create_graph(self, graph_name: str) -> None:
        self.ensure_graph_loaded("default")
        try:
            self.query(f"CREATE GRAPH {graph_name}", graph="default")
        except TuringDBHttpError as error:
            if "already exists" not in str(error).lower():
                raise

    def ensure_graph_loaded(self, graph_name: str) -> None:
        if self.is_graph_loaded(graph_name):
            return
        try:
            self.load_graph(graph_name)
        except TuringDBHttpError as error:
            if error.error_code not in {"GRAPH_ALREADY_EXISTS", "GRAPH_LOAD_ERROR"}:
                raise

    def new_change(self, graph_name: str | None = None) -> int:
        graph = graph_name or self._graph
        self.checkout_main()
        rows = self.query("CHANGE NEW", graph=graph)
        change_id = int(rows[0]["changeID"])
        self.set_change(change_id)
        return change_id

    def query(
        self,
        query: str,
        *,
        graph: str | None = None,
        change: int | str | None = None,
        commit: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {"graph": graph or self._graph}
        resolved_change = change if change is not None else self._change
        resolved_commit = commit if commit is not None else self._commit
        if resolved_change is not None:
            params["change"] = (
                f"{resolved_change:x}"
                if isinstance(resolved_change, int)
                else str(resolved_change)
            )
        if resolved_commit:
            params["commit"] = resolved_commit

        payload = self._post_text("query", params=params, body=query)
        if payload.get("error"):
            raise TuringDBHttpError(
                f"{payload['error']}: {payload.get('error_details', '')}".strip(": "),
                error_code=str(payload["error"]),
            )
        return self._rows_from_payload(payload)

    def write_graph_snapshot(
        self,
        graph_name: str,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> None:
        self.create_graph(graph_name)
        self.ensure_graph_loaded(graph_name)
        self.set_graph(graph_name)
        self.checkout_main()

        change_id = self.new_change(graph_name)
        valid_node_ids: set[str] = set()

        for node in nodes:
            node_id = str(node.get("id") or "").strip()
            if not node_id:
                continue
            self.query(_create_node_query(node), graph=graph_name, change=change_id)
            valid_node_ids.add(node_id)

        self.query("COMMIT", graph=graph_name, change=change_id)

        for edge in edges:
            source = str(edge.get("source") or "").strip()
            target = str(edge.get("target") or "").strip()
            if source not in valid_node_ids or target not in valid_node_ids:
                continue
            self.query(_create_edge_query(edge), graph=graph_name, change=change_id)

        self.query("COMMIT", graph=graph_name, change=change_id)
        self.query("CHANGE SUBMIT", graph=graph_name, change=change_id)
        self.checkout_main()

    def read_graph_snapshot(self, graph_name: str) -> dict[str, Any]:
        self.ensure_graph_loaded(graph_name)
        self.set_graph(graph_name)
        self.checkout_main()

        node_rows = self.query(
            """
            MATCH (n)
            WHERE n.id IS NOT NULL
            RETURN n.id AS id
            """,
            graph=graph_name,
        )
        nodes_by_id = {
            str(row["id"]): {"id": str(row["id"])}
            for row in node_rows
            if row.get("id")
        }
        for property_name in NODE_SNAPSHOT_PROPERTIES:
            for row in self._optional_node_property_rows(graph_name, property_name):
                node_id = str(row.get("id") or "")
                if node_id in nodes_by_id:
                    nodes_by_id[node_id][property_name] = row.get("value")

        edge_rows = self.query(
            """
            MATCH (src)-[edge]->(dst)
            WHERE src.id IS NOT NULL AND dst.id IS NOT NULL
            RETURN src.id AS source, dst.id AS target
            """,
            graph=graph_name,
        )
        edges = [
            {
                "source": str(row.get("source") or ""),
                "target": str(row.get("target") or ""),
            }
            for row in edge_rows
            if row.get("source") and row.get("target")
        ]
        for property_name in EDGE_SNAPSHOT_PROPERTIES:
            property_rows = self._optional_edge_property_rows(graph_name, property_name)
            for index, row in enumerate(property_rows):
                if index >= len(edges):
                    continue
                if (
                    edges[index]["source"] == str(row.get("source") or "")
                    and edges[index]["target"] == str(row.get("target") or "")
                ):
                    edges[index][property_name] = row.get("value")

        nodes = [_normalize_node(row) for row in nodes_by_id.values()]
        normalised_edges = [_normalize_edge(row) for row in edges]

        return {
            "metadata": {
                "name": graph_name,
                "source": "turingdb",
            },
            "nodes": nodes,
            "edges": normalised_edges,
        }

    def _optional_node_property_rows(
        self,
        graph_name: str,
        property_name: str,
    ) -> list[dict[str, Any]]:
        return self._optional_property_rows(
            f"""
            MATCH (n)
            WHERE n.id IS NOT NULL
            RETURN n.id AS id, n.{property_name} AS value
            """,
            graph_name,
        )

    def _optional_edge_property_rows(
        self,
        graph_name: str,
        property_name: str,
    ) -> list[dict[str, Any]]:
        return self._optional_property_rows(
            f"""
            MATCH (src)-[edge]->(dst)
            WHERE src.id IS NOT NULL AND dst.id IS NOT NULL
            RETURN src.id AS source, dst.id AS target, edge.{property_name} AS value
            """,
            graph_name,
        )

    def _optional_property_rows(self, query: str, graph_name: str) -> list[dict[str, Any]]:
        try:
            return self.query(query, graph=graph_name)
        except TuringDBHttpError as error:
            message = str(error).lower()
            if "property type" in message and "not found" in message:
                return []
            raise

    def _post_json(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        encoded = json.dumps(body or {}).encode("utf-8")
        return self._request(path, params=params, body=encoded, content_type="application/json")

    def _post_text(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        body: str = "",
    ) -> dict[str, Any]:
        return self._request(
            path,
            params=params,
            body=body.encode("utf-8"),
            content_type="text/plain",
        )

    def _request(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        body: bytes = b"{}",
        content_type: str = "application/json",
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        if params:
            url = f"{url}?{urlencode(params)}"

        request = Request(url, data=body, method="POST")
        request.add_header("Accept", "application/json")
        request.add_header("Content-Type", content_type)

        try:
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise TuringDBHttpError(
                f"HTTP {error.code} from TuringDB at {url}: {detail or error.reason}"
            ) from error
        except (OSError, URLError) as error:
            raise TuringDBHttpError(
                f"TuringDB Docker server is not reachable at {self.base_url}: {error}"
            ) from error

        try:
            payload = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as error:
            raise TuringDBHttpError(
                f"Invalid JSON from TuringDB at {url}: {error}"
            ) from error

        if not isinstance(payload, dict):
            raise TuringDBHttpError(f"Unexpected response type from TuringDB at {url}")

        return payload

    @staticmethod
    def _rows_from_payload(payload: dict[str, Any]) -> list[dict[str, Any]]:
        header = payload.get("header") or {}
        column_names = header.get("column_names") or []
        data = payload.get("data") or []
        if not column_names or not data:
            return []

        rows: list[dict[str, Any]] = []
        for chunk in data:
            if not isinstance(chunk, list):
                continue
            column_values = {
                name: values
                for name, values in zip(column_names, chunk, strict=False)
                if isinstance(values, list)
            }
            if not column_values:
                continue
            row_count = max(len(values) for values in column_values.values())
            for index in range(row_count):
                row = {
                    name: values[index] if index < len(values) else None
                    for name, values in column_values.items()
                }
                rows.append(row)
        return rows


def _escape_cypher_string(value: Any) -> str:
    return str(value).replace("\\", "\\\\").replace("'", "\\'")


def _cypher_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if value is None:
        return "null"
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
    node_label = _safe_identifier(
        node.get("type") or node.get("node_type") or node.get("template_type"),
        "BreachPathNode",
    )
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


def _normalize_node(row: dict[str, Any]) -> dict[str, Any]:
    node_type = row.get("node_type") or row.get("type") or row.get("template_type") or "unknown"
    description = row.get("description") or row.get("notes") or ""
    return {
        "id": str(row.get("id") or ""),
        "label": str(row.get("label") or row.get("id") or ""),
        "type": str(row.get("type") or node_type),
        "node_type": str(node_type),
        "template_type": str(row.get("template_type") or node_type),
        "criticality": str(row.get("criticality") or "medium"),
        "zone": str(row.get("zone") or "internal"),
        "description": str(description),
        "is_internet_exposed": bool(row.get("is_internet_exposed") or False),
        "has_admin_privileges": bool(row.get("has_admin_privileges") or False),
        "notes": str(row.get("notes") or ""),
    }


def _normalize_edge(row: dict[str, Any]) -> dict[str, Any]:
    edge_type = row.get("edge_type") or row.get("relationship") or "connects_to"
    description = row.get("description") or row.get("notes") or ""
    return {
        "id": str(row.get("id") or ""),
        "source": str(row.get("source") or ""),
        "target": str(row.get("target") or ""),
        "edge_type": str(edge_type),
        "relationship": str(row.get("relationship") or edge_type),
        "label": str(row.get("label") or edge_type),
        "risk_weight": _int_or_default(row.get("risk_weight"), 50),
        "direction": str(row.get("direction") or "directional"),
        "description": str(description),
        "risk_can_spread_both_ways": bool(row.get("risk_can_spread_both_ways") or False),
        "notes": str(row.get("notes") or ""),
    }


def _int_or_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def sdk_available() -> bool:
    try:
        import turingdb  # noqa: F401
    except Exception:
        return False
    return True
