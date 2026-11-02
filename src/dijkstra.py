# Dijkstra's shortest path algorithm for the PokePath graph.

class MinHeap:
    def __init__(self):
        self.items = []

    def is_empty(self):
        return len(self.items) == 0

    def push(self, item):
        self.items.append(item)
        self._move_up(len(self.items) - 1)

    def pop(self):
        if self.is_empty():
            raise IndexError("pop from an empty heap")

        smallest = self.items[0]
        last = self.items.pop()

        if not self.is_empty():
            self.items[0] = last
            self._move_down(0)

        return smallest

    def _move_up(self, index):
        while index > 0:
            parent = (index - 1) // 2

            if self.items[parent][0] <= self.items[index][0]:
                break

            self.items[parent], self.items[index] = (
                self.items[index],
                self.items[parent],
            )
            index = parent

    def _move_down(self, index):
        size = len(self.items)

        while True:
            left = index * 2 + 1
            right = index * 2 + 2
            smallest = index

            if left < size and self.items[left][0] < self.items[smallest][0]:
                smallest = left

            if right < size and self.items[right][0] < self.items[smallest][0]:
                smallest = right

            if smallest == index:
                break

            self.items[index], self.items[smallest] = (
                self.items[smallest],
                self.items[index],
            )
            index = smallest

def dijkstra(graph, start, target):
    #Return the shortest path and cost between two Pokemon.
    #Graph should map a Pokémon name to a list of (neighbor, weight)
    #pairs. All edge weights must be non-negative.

    if start not in graph or target not in graph:
        raise ValueError("start and target must be in the graph")

    distances = {pokemon: float("inf") for pokemon in graph}
    previous = {}
    distances[start] = 0

    heap = MinHeap()
    heap.push((0, start))

    while not heap.is_empty():
        current_cost, current = heap.pop()

        #Older entries can remain after a shorter path is found.
        if current_cost != distances[current]:
            continue

        if current == target:
            break

        for neighbor, weight in graph[current]:
            if weight < 0:
                raise ValueError("Dijkstra's algorithm needs non-negative weights")

            new_cost = current_cost + weight
            if new_cost < distances.get(neighbor, float("inf")):
                distances[neighbor] = new_cost
                previous[neighbor] = current
                heap.push((new_cost, neighbor))

    if distances[target] == float("inf"):
        return [], float("inf")

    path = []
    current = target
    while current != start:
        path.append(current)
        current = previous[current]
    path.append(start)
    path.reverse()

    return path, distances[target]