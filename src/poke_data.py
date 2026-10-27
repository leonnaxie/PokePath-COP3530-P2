import json
import requests

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

def get_evolutions(evolutionary_line):
    evolutions = [evolutionary_line["species"]["name"]]

    for pokemon in evolutionary_line["evolves_to"]:
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
        "species": species_data["name"],
        "egg_groups": [group["name"] for group in species_data["egg_groups"]
        ],
        "moves" : [move["move"]["name"] for move in poke_data["moves"]
        ],
        "evolutions": evolutions_list
    }

print(pokemon_graph)

# generating edges


