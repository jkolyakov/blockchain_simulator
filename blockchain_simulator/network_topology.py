import random
from typing import List, Dict, Tuple
from blockchain_simulator.blueprint import NodeBase, NetworkTopologyBase

class SimpleRandomTopology(NetworkTopologyBase):
    def __init__(self, 
                 min_delay: float = 0.5,
                 max_delay: float = 0.1,
                 nodes: List[NodeBase] = []):
        self.max_delay = max_delay
        self.min_delay = min_delay
        self.nodes = nodes

        if nodes:
            self.create_network_topology(nodes)

    def create_network_topology(self, nodes: List[NodeBase]) -> None:
        node_count = len(nodes)
        connected_edges = set()
        # Attempt random connections between each unique pair of nodes
        for i in range(node_count):
            for j in range(i + 1, node_count):
                # Skip if already connected
                if (i, j) in connected_edges or (j, i) in connected_edges:
                    continue
                
                # Randomly decide to connect the two nodes
                should_connect = random.random() < 0.3
                if should_connect:
                    node_a = nodes[i]
                    node_b = nodes[j]
                    node_a.add_peer(node_b)
                    node_b.add_peer(node_a)
                    connected_edges.add((i, j))
    
        # Ensure no node is isolated
        for node in nodes:
            if not node.get_peers():
                other_nodes = [n for n in nodes if n != node]
                chosen_peer = random.choice(other_nodes)
                node.add_peer(chosen_peer)
                chosen_peer.add_peer(node)

    def get_delay_between_nodes(self, node1: NodeBase, node2: NodeBase) -> float:
        return random.uniform(self.min_delay, self.max_delay)
    

class FullyConnectedTopology(SimpleRandomTopology):
    
    def create_network_topology(self, node_list: List[NodeBase]) -> None:
        """Creates a fully connected network where every node is connected to every other node."""
        for node in node_list:
            for peer in node_list:
                if node.node_id != peer.node_id:  # Don't connect to self
                    node.add_peer(peer)
    

class StarTopology(SimpleRandomTopology): 
    
    def create_network_topology(self, node_list: List[NodeBase]) -> None:
        """Creates a star network where every node is connected to a central node."""
        central_node = node_list[0]
        for node in node_list:
            if node.node_id != central_node.node_id:
                node.add_peer(central_node)
                central_node.add_peer(node)
    
class RingTopology(SimpleRandomTopology):
        
    def create_network_topology(self, node_list: List[NodeBase]) -> None:
        """Creates a ring network where each node is connected to two other nodes."""
        for i, node in enumerate(node_list):
            prev_node = node_list[i - 1]
            next_node = node_list[(i + 1) % len(node_list)]
            node.add_peer(prev_node)
            node.add_peer(next_node)

class LineTopology(SimpleRandomTopology):
    def create_network_topology(self, nodes):
        for i in range(len(nodes) - 1):
            nodes[i].add_peer(nodes[i + 1])
            nodes[(i + 1) % len(nodes)].add_peer(nodes[i])
            
class TreeTopology(SimpleRandomTopology):
    def __init__(self, min_delay, max_delay, nodes):
        self.branching_factor = 2
        super().__init__(min_delay, max_delay, nodes)

    def create_network_topology(self, nodes):
        for i, parent in enumerate(nodes):
            for j in range(1, self.branching_factor + 1):
                child_index = self.branching_factor * i + j
                if child_index < len(nodes):
                    child = nodes[child_index]
                    parent.add_peer(child)
                    child.add_peer(parent)