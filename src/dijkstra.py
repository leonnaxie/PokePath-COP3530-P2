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