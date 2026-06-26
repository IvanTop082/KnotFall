# BreachPath Idea

BreachPath is a cyber defence graph tool for understanding how an attacker could move through a network.

## The Problem

Cyber defenders often know that one machine may be compromised, but they need to know what the attacker can reach next.

## The Solution

BreachPath models the network as a graph and finds attack paths from a compromised node to critical assets.

## Simple Example

Workstation-17 -> File Server -> Admin Account -> Domain Controller

## Key Concepts

- Node = a thing in the network, such as a computer, server, account, or database.
- Edge = a relationship, such as "can access", "stores credentials", or "controls".
- Attack path = a route an attacker could use to move from a hacked machine to something important.

## Future Winning Feature

The system will compare defensive actions, such as isolating a server or disabling an admin account, and explain which action reduces the most risk.
