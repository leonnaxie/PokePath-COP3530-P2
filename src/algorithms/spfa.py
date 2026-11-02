"""Shortest Path, Faster Algorithm - An extension of Bellman-Ford that I initially was going to do
but thought this comparison would be more interesting compared to Dijkstra's. """

from classes.queue import Queue

def shortest_path_faster_algorithm(graph, source, target):
    dist = {v: float('inf') for v in graph}
    dist[source] = 0

    parent = {v: None for v in graph}

    q = Queue()
    q.enqueue(source)

    in_queue = {v: False for v in graph}
    in_queue[source] = True

    while not q.is_empty():
        curr = q.dequeue()
        in_queue[curr] = False

        for neighbor, weight in graph[curr]:
            if dist[neighbor] > dist[curr] + weight:
                dist[neighbor] = dist[curr] + weight
                parent[neighbor] = curr

                if (in_queue[neighbor] == False):
                    q.enqueue(neighbor)
                    in_queue[neighbor] = True

    if dist[target] == float('inf'):
        return float('inf'), []

    path = []
    curr = target

    while curr is not None:
        path.append(curr)
        curr = parent[curr]

    path.reverse()

    return dist[target], path