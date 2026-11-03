import time

from flask import Flask, jsonify, request

from algorithms.spfa import shortest_path_faster_algorithm
from dijkstra import dijkstra
from poke_data import build_graph, pokemon_names, edge_between

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
    "bellmanford": run_spfa,
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

        # Get relationship information for every pair of consecutive Pokemon
        links = []
        for i in range(len(path) - 1):
            link = edge_between(path[i], path[i + 1], edges)
            links.append(link)

        results.append({
            "algorithm": algorithm,
            "path": [name.title() for name in path],
            "links": links,
            "cost": cost,
            "time_ms": round(elapsed_ms, 3),
        })

    return jsonify({"results": results})


if __name__ == "__main__":
    app.run(debug=True, port=5001)

"""Loads Pokemon data from PokeAPI (cached on disk) and builds the graph the path finders use."""

import json
import os
from functools import lru_cache

import requests

API = "https://pokeapi.co/api/v2"
CACHE_PATH = os.path.join(os.path.dirname(__file__), "pokemon_cache.json")

# How many Pokemon to load. If you change this, delete pokemon_cache.json so it reloads.
POKEMON_LIMIT = 1

# Two Pokemon count as "sharing moves" only if they have at least this many in common.
MIN_SHARED_MOVES = 1

# Checkbox value sent by the page -> (relationship name used on edges, edge weight)
FEATURES = {
    "evolution": ("direct_evolution", 1),
    "egg": ("shared_egg_group", 2),
    "moves": ("shared_move", 3),
}

# Color palette matching classic Pokémon UI & themes
RELATIONSHIP_COLORS = {
    "direct_evolution": "#FFCB05",  # Classic Pokémon Yellow / Gold
    "shared_egg_group": "#E868A2",  # Soft Breeding / Egg Pink
    "shared_move": "#3B82F6",       # Vibrant Battle / Move Blue
}


# ---------- loading data from the API (runs once, then cached) ----------

def _get(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def get_evolutions(evolutionary_line):
    """Returns (pokemon, next_pokemon) pairs for every direct evolution in a chain."""
    evolutions = []
    current = evolutionary_line["species"]["name"]

    for nxt in evolutionary_line["evolves_to"]:
        evolutions.append((current, nxt["species"]["name"]))
        evolutions.extend(get_evolutions(nxt))

    return evolutions


def fetch_pokemon_data(limit=POKEMON_LIMIT):
    names = [p["name"] for p in _get(f"{API}/pokemon?limit={limit}")["results"]]

    data = {}
    chains = {}  # evolution chains are shared by a whole family, so fetch each once

    for name in names:
        poke = _get(f"{API}/pokemon/{name}/")
        species = _get(f"{API}/pokemon-species/{name}/")

        chain_url = species["evolution_chain"]["url"]
        if chain_url not in chains:
            chains[chain_url] = get_evolutions(_get(chain_url)["chain"])

        data[name] = {
            "evolutions": chains[chain_url],
            "egg_groups": [g["name"] for g in species["egg_groups"]],
            "moves": [m["move"]["name"] for m in poke["moves"]],
        }

    return data


@lru_cache(maxsize=1)
def load_data():
    """Reads the local cache, or downloads everything the first time."""
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            return json.load(f)

    data = fetch_pokemon_data()
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


# ---------- building edges and the graph ----------

@lru_cache(maxsize=1)
def get_edges():
    """Maps each connected pair (a, b) to the set of relationships between them."""
    data = load_data()
    names = list(data)

    direct = set()
    for info in data.values():
        direct.update(tuple(pair) for pair in info["evolutions"])

    egg_groups = {n: set(d["egg_groups"]) for n, d in data.items()}
    moves = {n: set(d["moves"]) for n, d in data.items()}

    edges = {}

    def add_edge(a, b, relationship):
        edges.setdefault(tuple(sorted((a, b))), set()).add(relationship)

    for i, a in enumerate(names):
        for b in names[i + 1:]:
            if (a, b) in direct or (b, a) in direct:
                add_edge(a, b, "direct_evolution")
            if egg_groups[a] & egg_groups[b]:
                add_edge(a, b, "shared_egg_group")
            if len(moves[a] & moves[b]) >= MIN_SHARED_MOVES:
                add_edge(a, b, "shared_move")

    return edges


@lru_cache(maxsize=None)
def build_graph(features):
    """Adjacency list using only the checked path features."""
    wanted = {FEATURES[f][0]: FEATURES[f][1] for f in features if f in FEATURES}
    graph = {name: [] for name in load_data()}

    for (a, b), relationships in get_edges().items():
        weights = [wanted[r] for r in relationships if r in wanted]
        if weights:
            w = min(weights)
            graph[a].append((b, w))
            graph[b].append((a, w))

    return graph


def edge_between(a, b, features):
    """The relationship, weight, and color assigned to the edge a-b (None if not connected)."""
    wanted = {FEATURES[f][0]: FEATURES[f][1] for f in features if f in FEATURES}
    relationships = get_edges().get(tuple(sorted((a, b))), set())
    options = [(wanted[r], r) for r in relationships if r in wanted]
    if not options:
        return None
    weight, relationship = min(options)
    
    return {
        "relationship": relationship,
        "weight": weight,
        "color": RELATIONSHIP_COLORS.get(relationship, "#94A3B8")  # Fallback gray if unmatched
    }


def pokemon_names():
    """Sorted list of every loaded Pokemon name (handy for autocomplete)."""
    return sorted(load_data())


if __name__ == "__main__":
    g = build_graph(("evolution", "egg", "moves"))
    print(f"{len(g)} Pokemon, {sum(len(v) for v in g.values()) // 2} edges")