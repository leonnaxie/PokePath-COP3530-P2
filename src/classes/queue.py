class ListNode:
    def __init__(self, val):
        self.val = val
        self.nxt = None

class Queue:
    def __init__(self):
        self.head = self.tail = None
        self.count = 0

    def enqueue(self, val):
        curr = ListNode(val)

        if self.tail is None:
            self.head = curr
            self.tail = curr
        else:
            self.tail.nxt = curr
            self.tail = curr

        self.count += 1

    def dequeue(self):
        if self.head is None:
            return None

        curr = self.head.val
        self.head = self.head.nxt

        if self.head is None:
            self.tail = None

        self.count -= 1

        return curr

    def get_size(self):
        return self.count

    def is_empty(self):
        return self.count == 0