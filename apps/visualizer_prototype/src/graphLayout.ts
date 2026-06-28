import type { GraphNode } from "./types";

const zoneOrder = [
  "user_zone",
  "server_zone",
  "identity_zone",
  "operations_zone",
  "security_zone",
];

export function positionForNode(node: GraphNode, rowByZone: Map<string, number>) {
  const zoneIndex = Math.max(zoneOrder.indexOf(node.zone), 0);
  const row = rowByZone.get(node.zone) || 0;
  rowByZone.set(node.zone, row + 1);

  return {
    x: zoneIndex * 280,
    y: row * 150,
  };
}
