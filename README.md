<H1> COP3530 FALL 2026 - Project 2 </h1>
<b>Team Rocket: Emily Chen, Isabelle Gomez, Leonna Xie</b>
<p>Our Project: There are thousands of Pokémon across generations and we are curious about the relationships between seemingly unrelated Pokémon. We will be able to explore these relationships using our own path-finding algorithms (We selected Dijkstra's and Shortest Path, Faster Algorithm).</p>

## How to Run
### Requirements
- Python 3
- pip
- Internet access for the initial Pokémon data download

### Setup
From the project's root directory, make sure to download these dependencies:
```bash
python -m pip install flask requests
```
(or whichever python command works for your computer, like python3, py, python)

Then you start the Flask server:
```bash
python src/server.py
```

Open this address in your browser: http://127.0.01:5001

The first run might take a couple of minutes while Pokémon data is downloaded from PokeAPI. Data is saved in `src/pokemon_cache.json` to speed up future runs.

In order to stop the server, press `Ctrl + C` in the terminal.

### How To Test
Start the server and use the browser interface to perform these manual tests:
1. **Evolution Path**
- Enter `Bulbasaur` as the start and `Venusaur` as the destination
- Select both algorithms and only evolutionary relationships
- Both of them should return a path from Bulbasaur -> Ivysaur -> Venusaur

2. **Compare algorithms**
- You can try different Pokémon pairings and combinations of path features with both algorithms selected
- Confirm that they both return the same minimum cost even if paths might differ when multiple short paths might exist
- Check that each result displays its path, cost, execution time and graph

3. **Same start and destination**
- Easily tested if you put `Pikachu` for the start and destination
- Confirm that both algorithms return a cost of 0 and only a single node in the graph

4. **No available path**
- Some Pokémon don't have paths to one another, you can try `Bulbasaur` and `Charmander` with only evolutionary relationships selected
- It should return a message about no path being available
