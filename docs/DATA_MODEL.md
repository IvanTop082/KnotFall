# Data Model

This document explains the Bit 2 demo data in beginner-friendly terms.

## Node

A node is a thing in the network.

Examples include a workstation, server, account, database, network device, security tool, or critical asset.

Each node has an `id`, a readable `label`, a `type`, a `zone`, a `criticality` score, and a short `description`.

## Edge

An edge is a relationship between two nodes.

For example, one node may be able to access another node, store credentials for it, control it, monitor it, or back it up.

Each edge has a `source`, a `target`, a `relationship`, a `risk_weight`, and a short `description`.

## Attack Path

An attack path is a route an attacker could use to move from a compromised node to something important.

For example:

```text
workstation-17 -> file-server -> admin-account -> domain-controller -> drone-ops-server
```

This means an attacker who starts on `workstation-17` may be able to move through connected systems until they reach a critical asset.

## Criticality

Criticality is a number from 1 to 100 that describes how important a node is.

A low number means the node is less important to the mission. A high number means the node is more important and should be protected carefully.

For example, the domain controller has very high criticality because it controls identity and access across the network.

## Risk Weight

Risk weight is a number that describes how risky an edge is.

A higher number means the relationship is more dangerous if an attacker can use it. For example, a file server storing admin credentials is high risk because it can help an attacker gain more control.

## Improvement

An improvement is a defensive action that could reduce risk.

Examples include isolating a server, disabling an account, removing stored credentials, segmenting the network, or improving monitoring.

Each improvement includes the target node, the expected effect, the operational cost, and the reason it may help.

## Future Backend Use

Later, the backend will load this data and use it to:

1. Build an in-memory graph.
2. Start from a compromised node selected by the user.
3. Find paths to critical assets.
4. Estimate risk using criticality and risk weights.
5. Compare improvements and explain which defensive action reduces risk the most.
