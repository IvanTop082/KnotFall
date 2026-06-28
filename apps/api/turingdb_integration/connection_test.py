"""Manual TuringDB connection test for BreachPath.

This script is intentionally separate from the FastAPI app. The existing API
still uses local JSON data until the project is ready for a TuringDBPathFinder.
"""


TURINGDB_HOST = "http://localhost:16666"
GRAPH_NAME = "attack_scenarios"
TEST_QUERY = "MATCH (n) RETURN n LIMIT 5"


def main():
    try:
        from turingdb import TuringDB
    except Exception as error:
        print("TuringDB SDK is not installed or could not be imported.")
        print("Install it with: python -m pip install turingdb")
        print(f"Original error: {error}")
        return

    try:
        # Connect to the local TuringDB HTTP API. Start TuringDB first from the
        # hackathon dataset repo with the Docker notes in scripts/.
        client = TuringDB("json", host=TURINGDB_HOST)

        # Load and select the provided EDTH hackathon cyber graph.
        client.load_graph(GRAPH_NAME)
        client.set_graph(GRAPH_NAME)

        # Run a small read-only query so this stays safe and defensive.
        result = client.query(TEST_QUERY)

        print("Connected to TuringDB successfully.")
        print(f"Host: {TURINGDB_HOST}")
        print(f"Graph: {GRAPH_NAME}")
        print(f"Query: {TEST_QUERY}")
        print("Result:")
        print(result)
    except Exception as error:
        print(
            "Could not connect to TuringDB. Make sure TuringDB is running on "
            "http://localhost:16666 and that the hackathon dataset repo was "
            "started with the UI/server enabled."
        )
        print(f"Original error: {error}")


if __name__ == "__main__":
    main()
