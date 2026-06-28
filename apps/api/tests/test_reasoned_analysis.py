import unittest

from fastapi.testclient import TestClient

from apps.api.main import app


class ReasonedAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def analyse(self, graph, node_id, simulation_type):
        response = self.client.post(
            "/analysis/compromised",
            json={
                "node_id": node_id,
                "simulation_type": simulation_type,
                "graph": graph,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_phone_compromise_does_not_highlight_entire_graph_or_router_admin(self):
        graph = build_test_graph(include_direct_phone_nas=True)

        analysis = self.analyse(graph, "phone-1", "compromise")
        highlighted = set(analysis["highlighted_nodes"])
        recommendation_text = " ".join(
            recommendation["title"].lower()
            for recommendation in analysis["recommendations"]
        )

        self.assertLess(len(highlighted), len(graph["nodes"]))
        self.assertIn("phone-1", highlighted)
        self.assertIn("nas-1", highlighted)
        self.assertNotIn("printer-1", highlighted)
        self.assertNotIn("router admin password", recommendation_text)
        self.assertTrue(
            any(
                recommendation["type"] == "segment_network"
                for recommendation in analysis["recommendations"]
            )
        )

    def test_phone_data_leak_prioritises_sensitive_data_not_printer(self):
        graph = build_test_graph(include_direct_phone_nas=True)

        analysis = self.analyse(graph, "phone-1", "data_leak")
        highlighted = set(analysis["highlighted_nodes"])
        recommendation_text = " ".join(
            f"{recommendation['title']} {recommendation.get('reason') or ''}".lower()
            for recommendation in analysis["recommendations"]
        )

        self.assertIn("nas-1", highlighted)
        self.assertNotIn("printer-1", highlighted)
        self.assertIn("data", recommendation_text)
        self.assertNotIn("firmware", recommendation_text)

    def test_router_offline_focuses_on_availability_not_credentials(self):
        graph = build_test_graph(include_direct_phone_nas=True)

        analysis = self.analyse(graph, "router-1", "offline")
        highlighted = set(analysis["highlighted_nodes"])
        recommendation_text = " ".join(
            f"{recommendation['title']} {recommendation.get('reason') or ''}".lower()
            for recommendation in analysis["recommendations"]
        )

        self.assertIn("work-laptop-1", highlighted)
        self.assertIn("nas-1", highlighted)
        self.assertNotIn("rotate", recommendation_text)
        self.assertNotIn("credential", recommendation_text)
        self.assertTrue(
            "availability" in recommendation_text
            or "resilience" in recommendation_text
        )

    def test_firewall_blocks_phone_to_nas_exposure(self):
        graph = build_test_graph(blocked_firewall_only=True)

        analysis = self.analyse(graph, "phone-1", "compromise")
        highlighted = set(analysis["highlighted_nodes"])
        blocked_reasons = " ".join(
            path["reason"].lower()
            for path in analysis["blocked_or_reduced_paths"]
        )
        recommendation_text = " ".join(
            f"{recommendation['title']} {recommendation.get('reason') or ''}".lower()
            for recommendation in analysis["recommendations"]
        )

        self.assertNotIn("nas-1", highlighted)
        self.assertTrue(analysis["blocked_or_reduced_paths"])
        self.assertIn("firewall", blocked_reasons)
        self.assertIn("firewall", recommendation_text)

    def test_work_laptop_lateral_movement_explains_privilege_path(self):
        graph = build_test_graph(include_direct_phone_nas=True)

        analysis = self.analyse(graph, "work-laptop-1", "lateral_movement")
        highlighted = set(analysis["highlighted_nodes"])
        recommendation_text = " ".join(
            f"{recommendation['title']} {recommendation.get('reason') or ''}".lower()
            for recommendation in analysis["recommendations"]
        )
        triggered_paths = [
            recommendation["triggered_by_path"]
            for recommendation in analysis["recommendations"]
        ]

        self.assertIn("admin-1", highlighted)
        self.assertIn("database-1", highlighted)
        self.assertTrue("admin" in recommendation_text or "credential" in recommendation_text)
        self.assertTrue(
            any("admin-1" in path and "database-1" in path for path in triggered_paths)
        )

    def test_admin_file_server_direction_is_explained_until_access_edge_is_added(self):
        graph = build_admin_direction_graph(include_admin_to_file_access=False)

        analysis = self.analyse(graph, "admin-account", "lateral_movement")
        highlighted = set(analysis["highlighted_nodes"])
        skipped_reasons = " ".join(
            edge["reason"].lower()
            for edge in analysis["traversal_explanation"]["skipped_edges"]
        )
        connected_reasons = {
            item["node_id"]: item["reason"].lower()
            for item in analysis["traversal_explanation"]["connected_but_not_highlighted"]
        }

        self.assertIn("domain-controller", highlighted)
        self.assertIn("database", highlighted)
        self.assertNotIn("file-server", highlighted)
        self.assertIn("directional", skipped_reasons)
        self.assertIn("file-server", connected_reasons)

        graph_with_access = build_admin_direction_graph(include_admin_to_file_access=True)
        analysis_with_access = self.analyse(
            graph_with_access,
            "admin-account",
            "lateral_movement",
        )
        followed_edges = analysis_with_access["traversal_explanation"]["followed_edges"]

        self.assertTrue(
            any(
                edge["to"] == "file-server"
                and edge["edge_type"] == "can_access"
                and edge["decision"] == "followed"
                for edge in followed_edges
            )
        )


def build_test_graph(
    include_direct_phone_nas=False,
    blocked_firewall_only=False,
):
    nodes = [
        node("phone-1", "Phone", "phone", 35, "Personal phone on the home network."),
        node("router-1", "Router", "router", 80, "Home router and routing chokepoint."),
        node("printer-1", "Printer", "printer", 25, "Low-impact network printer."),
        node("nas-1", "NAS", "nas_home_server", 88, "Sensitive shared storage."),
        node("admin-1", "Admin Account", "admin_account", 92, "Privileged account."),
        node("firewall-1", "Firewall", "firewall", 85, "Segmentation control."),
        node("work-laptop-1", "Work Laptop", "work_laptop", 78, "Work laptop."),
        node("database-1", "Database", "database", 95, "Critical customer database."),
    ]

    if blocked_firewall_only:
        edges = [
            edge("e-phone-firewall", "phone-1", "firewall-1", "routes_through", 45),
            edge(
                "e-firewall-nas",
                "firewall-1",
                "nas-1",
                "can_access",
                85,
                allowed_by_firewall=False,
            ),
        ]
    else:
        edges = [
            edge("e-phone-router", "phone-1", "router-1", "same_network", 35),
            edge("e-router-printer", "router-1", "printer-1", "can_access", 20),
            edge("e-router-nas", "router-1", "nas-1", "can_access", 75),
            edge("e-phone-firewall", "phone-1", "firewall-1", "routes_through", 45),
            edge(
                "e-firewall-nas",
                "firewall-1",
                "nas-1",
                "can_access",
                85,
                allowed_by_firewall=False,
            ),
            edge("e-work-admin", "work-laptop-1", "admin-1", "stores_credentials_for", 85),
            edge("e-admin-db", "admin-1", "database-1", "controls", 85),
            edge("e-work-router", "work-laptop-1", "router-1", "depends_on", 60),
            edge("e-nas-router", "nas-1", "router-1", "depends_on", 65),
            edge("e-printer-router", "printer-1", "router-1", "depends_on", 45),
        ]

        if include_direct_phone_nas:
            edges.append(edge("e-phone-nas", "phone-1", "nas-1", "can_access", 55))

    return {
        "metadata": {"name": "Reasoned analysis test graph"},
        "nodes": nodes,
        "edges": edges,
    }


def build_admin_direction_graph(include_admin_to_file_access):
    edges = [
        edge("e-admin-dc", "admin-account", "domain-controller", "administers", 90),
        edge("e-dc-db", "domain-controller", "database", "controls", 90),
        edge("e-dc-fw", "domain-controller", "firewall", "can_access", 65),
        edge("e-fw-internet", "firewall", "internet", "routes_through", 65),
        edge("e-file-admin", "file-server", "admin-account", "stores_credentials_for", 90),
        edge("e-file-workstation", "file-server", "workstation", "can_access", 45),
        edge("e-file-backup", "file-server", "backup-server", "backs_up", 45),
    ]

    if include_admin_to_file_access:
        edges.append(edge("e-admin-file", "admin-account", "file-server", "can_access", 65))

    return {
        "metadata": {"name": "Admin direction transparency test graph"},
        "nodes": [
            node("admin-account", "Admin Account", "admin_account", 92, "Privileged account."),
            node(
                "domain-controller",
                "Domain Controller",
                "domain_controller",
                100,
                "Critical identity controller.",
            ),
            node("database", "Database", "database", 95, "Critical database."),
            node("firewall", "Firewall", "firewall", 85, "Segmentation control."),
            node("internet", "Internet", "internet", 100, "External boundary."),
            node("file-server", "File Server", "file_server", 80, "Shared storage."),
            node("workstation", "Workstation", "workstation", 45, "User workstation."),
            node("backup-server", "Backup Server", "backup_server", 82, "Backup server."),
        ],
        "edges": edges,
    }


def node(node_id, label, node_type, criticality, description):
    return {
        "id": node_id,
        "label": label,
        "type": node_type,
        "zone": "test_zone",
        "criticality": criticality,
        "description": description,
    }


def edge(
    edge_id,
    source,
    target,
    relationship,
    risk_weight,
    allowed_by_firewall=None,
):
    payload = {
        "id": edge_id,
        "source": source,
        "target": target,
        "relationship": relationship,
        "risk_weight": risk_weight,
        "description": f"{source} {relationship} {target}",
    }
    if allowed_by_firewall is not None:
        payload["allowed_by_firewall"] = allowed_by_firewall
    return payload


if __name__ == "__main__":
    unittest.main()
