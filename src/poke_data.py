import json
import requests
import sqlite3

API = "https://pokeapi.co/api/v2"

#processing pokemon data from API
def get_poke(name):
    info_url = f"{API}/pokemon/{name}/"

    # get name data
    info = requests.get(info_url, timeout = 30)
    info.raise_for_status()
    poke_data = info.json()

    return poke_data

def get_species(name):
    info_url = f"{API}/pokemon-species/{name}/"

    # get species data
    species = requests.get(info_url, timeout = 30)
    species.raise_for_status()
    species_data = species.json()

    return species_data

# direct evolutions
def get_evolutions(evolutionary_line):
    evolutions = []
    direct_evolution = evolutionary_line["species"]["name"]

    for pokemon in evolutionary_line["evolves_to"]:
        next_pokemon = pokemon["species"]["name"]
        evolutions.append((direct_evolution, next_pokemon))
        evolutions.extend(get_evolutions(pokemon))

    return evolutions


# get list of all pokemon names
output = requests.get(f"{API}/pokemon?limit=10" , timeout = 30)
output.raise_for_status()

names = []
pokemon_list = []
pokemon_graph = {}
for pokemon in output.json()["results"]:
    names.append(pokemon["name"])

for name in names:
    poke_data = get_poke(name)
    species_data = get_species(name)

    #get evolutions
    next_evolution_url = species_data["evolution_chain"]["url"]
    evolution_output = requests.get(next_evolution_url, timeout = 30)
    evolution_output.raise_for_status()
    evolutions = evolution_output.json()
    evolutions_list = get_evolutions(evolutions["chain"])

    # create a graph for each pokemon (linked by name)
    pokemon_graph[name] = {
        "evolutions": evolutions_list,
        "species": species_data["name"],
        "egg_groups": [group["name"] for group in species_data["egg_groups"]
        ],
        "moves" : [move["move"]["name"] for move in poke_data["moves"]
        ]
    }

print(pokemon_graph)

# generating edges
edge_names = {}

def add_edge(a, b, relationship):
    # pokemon are the same
    if a == b:
        return

    # check if pokemon exists in the graph
    if a not in pokemon_graph or b not in pokemon_graph:
        return

    match = tuple(sorted([a,b]))
    if match not in edge_names:
        edge_names[match] = set()

    edge_names[match].add(relationship)

direct_evolutions = set()

for poke_data in pokemon_graph.values():
    for pair in poke_data["evolutions"]:
        direct_evolutions.add(pair)


for i in range(len(names)):
    for j in range(i + 1, len(names)):
        a = names[i]
        b = names[j]

        a_info = pokemon_graph[a]
        b_info = pokemon_graph[b]

        # Direct evolution
        if (a, b) in direct_evolutions or (b,a) in direct_evolutions:
            add_edge(a,b, "direct_evolution")

        # Egg group
        if set(a_info["egg_groups"]) & set(b_info["egg_groups"]):
            add_edge(a,b,"shared_egg_group")

        # Moves
        if set(a_info["moves"]) & set(b_info["moves"]):
            add_edge(a,b,"shared_move")


print("=== Poke Data ===")
print(pokemon_graph)

print("\nEdges: ")
for (a,b), relationships in edge_names.items():
    print(a, ">>", b)

# creates adjacecy list
graph = {}
for name in pokemon_graph:
    graph[name] = []

for (a, b), relationships in edge_names.items():
    weight = 1

    graph[a].append((b, weight))
    graph[b].append((a, weight))

print("\n=== MAP ===")
for pokemon, neighbors in graph.items():
    print(pokemon, ":", neighbors)


""""
=== CODE TO TEST SHORTEST PATH ===
weedle -> raticate

from collections import deque
def shortest_path(graph, start, target):
    if start not in graph or target not in graph:
        return None
    queue = deque([start])
    previous = {start: None}
    while queue:
        current = queue.popleft()
        if current == target:
            break
        for neighbor, weight in graph[current]:
            if neighbor not in previous:
                previous[neighbor] = current
                queue.append(neighbor)
    if target not in previous:
        return None
    path = []
    current = target
    while current is not None:
        path.append(current)
        current = previous[current]
    return path[::-1]

path = shortest_path(graph, "weedle", "raticate")

if path is None:
    print("No path found.")
else:
    print("Shortest path:", " -> ".join(path))
    print("Path length (edges):", len(path) - 1)
"""