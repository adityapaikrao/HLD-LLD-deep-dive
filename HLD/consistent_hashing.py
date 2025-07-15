import bisect

class ConsisentHashRing:
    def __init(self, nodes, replicas=100):
        self.replicas = replicas
        self._ring = {}
        self._sorted_keys = []

        for node in nodes:
            self.add_node(node)
    
    def add_node(self, node):
        for i in range(self.replicas):
            key = f"{node}:{i}"
            hashed_key = hash(key)
            self._ring[hashed_key] = node
            bisect.insort(self._sorted_keys, hashed_key)
        
        return
    
    def remove_node(self, node):
        for i in range(self.replicas):
            key = f"{node}:{i}"
            hashed_key = hash(key)
            self._ring.pop(hashed_key, None)

            idx = bisect.bisect_left(self._sorted_keys, hashed_key)
            self._sorted_keys.pop(idx)
        
        return
    
    def get_node(self, key):
        if not self._ring:
            return None
        
        hashed_key = hash(key)
        idx = bisect.bisect(self._sorted_keys, hashed_key)

        return self._ring[self._sorted_keys[idx % len(self._sorted_keys)]]