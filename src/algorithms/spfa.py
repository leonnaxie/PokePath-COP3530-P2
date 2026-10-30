"""Shortest Path, Faster Algorithm - An extension of Bellman-Ford that I initially was going to do
but thought this comparison would be more interesting compared to Dijkstra's. """

from collections import deque

def shortest_path_faster_algorithm(graph, source, target):
    if source not in graph or target not in graph:
        return None

    queue = deque([source])
