"""Load Pokemon data and build the graph used by the path algorithms."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
import requests

API = "https://pokeapi.co/api/v2"
CACHE_PATH = os.path.join(os.path.dirname(__file__), "pokemon_cache.json")
CACHE_TMP_PATH = CACHE_PATH + ".tmp"

# Number of Pokemon to load from the API. The data is saved in batches so the
# download can continue later if it gets interrupted.
POKEMON_LIMIT = 1025

# The Pokemon need at least this many moves in common to share a move edge.
MIN_SHARED_MOVES = 1

# Values from the page map to the relationship name and edge weight.
FEATURES = {
    "evolution": ("direct_evolution", 1),
    "egg": ("shared_egg_group", 2),
    "moves": ("shared_move", 3),
}

# loading data from the API

def _get(url):
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()

def get_evolutions(evolutionary_line):
    """Get all of the direct evolution pairs in an evolution chain."""
    evolutions = []
    current = evolutionary_line["species"]["name"]

    for nxt in evolutionary_line["evolves_to"]:
        evolutions.append((current, nxt["species"]["name"]))
        evolutions.extend(get_evolutions(nxt))

    return evolutions

def fetch_pokemon_data(limit=POKEMON_LIMIT, names=None, data=None):
    if names is None:
        names = [p["name"] for p in _get(f"{API}/pokemon-species?limit={limit}")["results"]]
    if data is None:
        data = {}
    else:
        data = dict(data)

    names = [name for name in names if name not in data]

    def fetch_details(name):
        species = _get(f"{API}/pokemon-species/{name}/")
        # Some species use a different name for their default Pokemon form.
        pokemon_name = species["varieties"][0]["pokemon"]["name"]
        poke = _get(f"{API}/pokemon/{pokemon_name}/")
        return name, poke, species

    for start in range(0, len(names), 25):
        batch = names[start:start + 25]

        # These requests do not depend on each other, so run several at once.
        # Saving each batch also means we do not lose everything if it stops.
        with ThreadPoolExecutor(max_workers=12) as executor:
            details = list(executor.map(fetch_details, batch))

        chain_urls = {species["evolution_chain"]["url"] for _, _, species in details}
        with ThreadPoolExecutor(max_workers=12) as executor:
            chains = dict(zip(chain_urls, executor.map(_get, chain_urls)))

        for name, poke, species in details:
            chain = chains[species["evolution_chain"]["url"]]
            data[name] = {
                "evolutions": get_evolutions(chain["chain"]),
                "egg_groups": [g["name"] for g in species["egg_groups"]],
                "moves": [m["move"]["name"] for m in poke["moves"]],
            }

        _save_cache(data)

    return data

def _save_cache(data):
    """Save the downloaded data without replacing a good cache halfway through."""
    with open(CACHE_TMP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(CACHE_TMP_PATH, CACHE_PATH)

@lru_cache(maxsize=1)
def load_data():
    """Read the cache and download anything that is still missing."""
    data = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)

    if len(data) < POKEMON_LIMIT:
        names = [p["name"] for p in _get(f"{API}/pokemon-species?limit={POKEMON_LIMIT}")["results"]]
        data = fetch_pokemon_data(names=names, data=data)

    return data

# Building the graph

@lru_cache(maxsize=1)
def get_edges():
    """Map each connected pair to the relationships between them."""
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
    """Build an adjacency list using the selected path features.

    If two Pokemon have more than one connection, use the lowest weight.
    """
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
    """Return the relationship and weight for an edge, if one exists."""
    wanted = {FEATURES[f][0]: FEATURES[f][1] for f in features if f in FEATURES}
    relationships = get_edges().get(tuple(sorted((a, b))), set())
    options = [(wanted[r], r) for r in relationships if r in wanted]
    if not options:
        return None
    weight, relationship = min(options)
    return {"relationship": relationship, "weight": weight}

def pokemon_names():
    """Return the loaded Pokemon names for the autocomplete list."""
    return sorted(load_data())

if __name__ == "__main__":
    # Run this once to download the data before starting the server.
    g = build_graph(("evolution", "egg", "moves"))
    print(f"{len(g)} Pokemon, {sum(len(v) for v in g.values()) // 2} edges")