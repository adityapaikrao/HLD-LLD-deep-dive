"""
Consistent Hashing

Implements a consistent hashing algorithm for distributed systems.
Useful for sharding data across multiple nodes with minimal re-distribution
when nodes are added or removed.
"""

import bisect


class ConsistentHashRing:
    def __init__(self, nodes, replicas: int = 100):
        """
        Initialize the consistent hash ring.

        Args:
            nodes (list): Initial list of nodes to add to the ring.
            replicas (int): Number of virtual replicas per node for better key distribution.
        """
        self.replicas = replicas
        self._ring = {}  # Mapping of hashed keys -> node
        self._sorted_keys = []  # Sorted list of hashed keys (the ring)

        for node in nodes:
            self.add_node(node)

    def add_node(self, node):
        """
        Add a node (and its replicas) to the consistent hash ring.

        Args:
            node (str): Identifier for the node to be added (e.g., hostname, IP).

        Example:
            >>> ring.add_node("server3")
        """
        for i in range(self.replicas):
            virtual_node_key = f"{node}:{i}"
            hashed_key = hash(virtual_node_key)
            self._ring[hashed_key] = node
            bisect.insort(self._sorted_keys, hashed_key)

    def remove_node(self, node):
        """
        Remove a node (and its replicas) from the consistent hash ring.

        Args:
            node (str): Identifier for the node to be removed.

        Example:
            >>> ring.remove_node("server1")
        """
        for i in range(self.replicas):
            virtual_node_key = f"{node}:{i}"
            hashed_key = hash(virtual_node_key)
            self._ring.pop(hashed_key, None)

            idx = bisect.bisect_left(self._sorted_keys, hashed_key)
            if idx < len(self._sorted_keys) and self._sorted_keys[idx] == hashed_key:
                self._sorted_keys.pop(idx)

    def get_node(self, key):
        """
        Get the node responsible for a given key.

        Args:
            key (str): Key to be mapped to a node.

        Returns:
            str: The node that should store this key, or None if the ring is empty.

        Example:
            >>> node = ring.get_node("user:1234")
            >>> print(node)
            "server2"
        """
        if not self._ring:
            return None

        hashed_key = hash(key)
        idx = bisect.bisect(self._sorted_keys, hashed_key)
        return self._ring[self._sorted_keys[idx % len(self._sorted_keys)]]
