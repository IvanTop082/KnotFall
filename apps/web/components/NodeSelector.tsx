import type { GraphNode } from "../lib/types";

interface NodeSelectorProps {
  nodes: GraphNode[];
  selectedNodeId: string;
  onSelect: (nodeId: string) => void;
}

const preferredTypes = new Set([
  "workstation",
  "server",
  "identity",
  "network_device",
]);

function optionLabel(node: GraphNode) {
  return `${node.label} (${node.type.replace("_", " ")})`;
}

export default function NodeSelector({
  nodes,
  selectedNodeId,
  onSelect,
}: NodeSelectorProps) {
  const preferredNodes = nodes.filter((node) => preferredTypes.has(node.type));
  const otherNodes = nodes.filter((node) => !preferredTypes.has(node.type));
  const selectedNode = nodes.find((node) => node.id === selectedNodeId);

  return (
    <section className="rounded-lg border border-slate-800 bg-breach-panel p-5">
      <label
        htmlFor="compromised-node"
        className="text-sm font-medium text-slate-200"
      >
        Compromised node
      </label>
      <select
        id="compromised-node"
        value={selectedNodeId}
        onChange={(event) => onSelect(event.target.value)}
        className="mt-3 w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition focus:border-orange-400 focus:ring-2 focus:ring-orange-400/20"
      >
        <option value="">Select a node</option>
        <optgroup label="Useful starting points">
          {preferredNodes.map((node) => (
            <option key={node.id} value={node.id}>
              {optionLabel(node)}
            </option>
          ))}
        </optgroup>
        <optgroup label="Other nodes">
          {otherNodes.map((node) => (
            <option key={node.id} value={node.id}>
              {optionLabel(node)}
            </option>
          ))}
        </optgroup>
      </select>

      {selectedNode ? (
        <div className="mt-4 rounded-md border border-slate-800 bg-slate-950/70 p-3">
          <p className="text-sm font-semibold text-slate-100">
            {selectedNode.label}
          </p>
          <p className="mt-1 text-xs uppercase text-slate-500">
            {selectedNode.zone.replace("_", " ")} · criticality{" "}
            {selectedNode.criticality}
          </p>
          <p className="mt-2 text-sm text-slate-300">
            {selectedNode.description}
          </p>
        </div>
      ) : null}
    </section>
  );
}
