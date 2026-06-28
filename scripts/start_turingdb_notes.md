# Start TuringDB Notes

## Step A

```powershell
cd external/turingdb-hackathon-defense
```

## Step B

```powershell
turingdb start -turing-dir . -ui
```

If that fails, try:

```powershell
turingdb -ui
```

## Step C

Open:

```text
http://localhost:18080
```

## Step D

In the visualizer, select:

```text
attack_scenarios
```

## Step E

Run:

```cypher
MATCH (n) RETURN n LIMIT 50
```

## Step F

The API should be available at:

```text
http://localhost:16666
```

## Step G

From the BreachPath project root, run:

```powershell
python apps/api/turingdb_integration/connection_test.py
```
