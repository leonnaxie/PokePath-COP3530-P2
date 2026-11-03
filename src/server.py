import time

from flask import Flask, jsonify, request

from algorithms.spfa import shortest_path_faster_algorithm
from algorithms.dijkstra import dijkstra
from poke_data import build_graph, edge_between, pokemon_names

# Flask serves everything in src/static/ (index.html, logo.png) automatically
app = Flask(__name__)

def as_cost_and_path(result):
    # Accepts (cost, path) or (path, cost) and always returns (cost, path)
    first, second = result
    return (second, first) if isinstance(first, list) else (first, second)

def run_dijkstra(graph, start, end):
    return as_cost_and_path(dijkstra(graph, start, end))

def run_spfa(graph, start, end):
    return as_cost_and_path(shortest_path_faster_algorithm(graph, start, end))

# Each entry takes (graph, start, end) and returns (cost, path)
ALGORITHMS = {
    "dijkstra": run_dijkstra,
    "spfa": run_spfa,
}

@app.route("/")
def home():
    return app.send_static_file("index.html")

@app.route("/api/names")
def names():
    return jsonify(pokemon_names())

@app.route("/api/path")
def find_path():
    start = request.args.get("start", "").strip().lower()
    end = request.args.get("end", "").strip().lower()
    algorithms = [a for a in request.args.get("algorithms", "").split(",") if a in ALGORITHMS]
    edges = tuple(sorted(e for e in request.args.get("edges", "").split(",") if e))

    if not start or not end:
        return jsonify({"error": "Please enter both Pokemon."}), 400
    if not algorithms or not edges:
        return jsonify({"error": "Pick at least one algorithm and one path feature."}), 400

    graph = build_graph(edges)

    for name in (start, end):
        if name not in graph:
            return jsonify({"error": f"Couldn't find '{name}'. Check the spelling."}), 404

    results = []
    for algorithm in algorithms:
        t0 = time.perf_counter()
        cost, path = ALGORITHMS[algorithm](graph, start, end)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        if not path:
            return jsonify({"error": "No path between these two Pokemon!"}), 404

        results.append({
            "algorithm": algorithm,
            "path": [name.title() for name in path],
            "links": [edge_between(a, b, edges) for a, b in zip(path, path[1:])],
            "cost": cost,
            "time_ms": round(elapsed_ms, 3),
        })

    return jsonify({"results": results})

if __name__ == "__main__":
    app.run(debug=True, port=5001)
