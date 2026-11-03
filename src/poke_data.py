"""Loads Pokemon data from PokeAPI (cached on disk) and builds the graph the path finders use."""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache

import requests

API = "https://pokeapi.co/api/v2"
CACHE_PATH = os.path.join(os.path.dirname(__file__), "pokemon_cache.json")
CACHE_TMP_PATH = CACHE_PATH + ".tmp"

# How many Pokemon to load. The first 151 include the original Pokemon such as
# Pikachu and Charizard while keeping the first-run PokeAPI download manageable.
# If you change this, delete pokemon_cache.json so it reloads.
POKEMON_LIMIT = 151

# Two Pokemon count as "sharing moves" only if they have at least this many in common.
# With 1, almost every pair is connected, so paths are nearly always a single hop.
MIN_SHARED_MOVES = 1

# Checkbox value sent by the page -> (relationship name used on edges, edge weight)
FEATURES = {
    "evolution": ("direct_evolution", 1),
    "egg": ("shared_egg_group", 2),
    "moves": ("shared_move", 3),
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


def fetch_pokemon_data(limit=POKEMON_LIMIT, names=None, data=None):
    if names is None:
        names = [p["name"] for p in _get(f"{API}/pokemon?limit={limit}")["results"]]
    if data is None:
        data = {}
    else:
        data = dict(data)

    names = [name for name in names if name not in data]

    def fetch_details(name):
        poke = _get(f"{API}/pokemon/{name}/")
        species = _get(f"{API}/pokemon-species/{name}/")
        return name, poke, species

    for start in range(0, len(names), 25):
        batch = names[start:start + 25]

        # The API calls are independent. Fetching them concurrently keeps each
        # batch small enough to cache safely if the process is interrupted.
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
    """Save completed batches atomically so interrupted downloads keep progress."""
    with open(CACHE_TMP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(CACHE_TMP_PATH, CACHE_PATH)


@lru_cache(maxsize=1)
def load_data():
    """Load cached data and download only Pokemon missing from that cache."""
    data = {}
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, encoding="utf-8") as f:
            data = json.load(f)

    if len(data) < POKEMON_LIMIT:
        names = [p["name"] for p in _get(f"{API}/pokemon?limit={POKEMON_LIMIT}")["results"]]
        data = fetch_pokemon_data(names=names, data=data)

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
    """Adjacency list using only the checked path features.

    features: a tuple of checkbox values, e.g. ("egg", "evolution").
    Returns {name: [(neighbor, weight), ...]}, the shape your algorithms expect.
    If a pair is connected in several selected ways, the cheapest edge is used.
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
    """The relationship and weight actually used for the edge a-b (None if not connected)."""
    wanted = {FEATURES[f][0]: FEATURES[f][1] for f in features if f in FEATURES}
    relationships = get_edges().get(tuple(sorted((a, b))), set())
    options = [(wanted[r], r) for r in relationships if r in wanted]
    if not options:
        return None
    weight, relationship = min(options)
    return {"relationship": relationship, "weight": weight}

def pokemon_names():
    """Sorted list of every loaded Pokemon name (handy for autocomplete)."""
    return sorted(load_data())


if __name__ == "__main__":
    # Run `python poke_data.py` once to download and cache the data before starting the server.
    g = build_graph(("evolution", "egg", "moves"))
    print(f"{len(g)} Pokemon, {sum(len(v) for v in g.values()) // 2} edges")
