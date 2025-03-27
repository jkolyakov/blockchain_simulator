from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
import random
from blockchain_simulator.blueprint import NetworkTopologyBase, NodeBase
import logging
# ============================
# CONSENSUS PROTOCOL ABSTRACT CLASS
# ============================

class FullyConnectedTopology(NetworkTopologyBase): 
    def create_network_topology(self, node_list: List[NodeBase]) -> None:
        """Creates a fully connected network where every node is connected to every other node."""
        for node in node_list:
            for peer in node_list:
                if node.node_id != peer.node_id:  # Don't connect to self
                    node.add_peer(peer)

class StarTopology(NetworkTopologyBase): 
    def create_network_topology(self, node_list: List[NodeBase]) -> None:
        """Creates a star network where every node is connected to a central node."""
        central_node = node_list[0]
        for node in node_list:
            if node.node_id != central_node.node_id:
                node.add_peer(central_node)
                central_node.add_peer(node)

class RandomTopology(NetworkTopologyBase):


    def __init__(self, 
                 max_delay: float = 0.5,
                 min_delay: float = 0.1,
                 expected_peers: int = 3):
        super.__init__(max_delay, min_delay, nodes, expected_peers)
        

    def create_network_topology(self, node_list: List[NodeBase]) -> None:
        """Creates a random network where each node is connected to a random number of other nodes."""

        edge_sampling_prob = self.expected_peers / len(node_list)
        for node in node_list:
            for peer in node_list:
                if node.node_id != peer.node_id and random.random() < edge_sampling_prob:
                    node.add_peer(peer)
                    peer.add_peer(node)

class RingTopology(NetworkTopologyBase):

    def create_network_topology(self, node_list: List[NodeBase]) -> None:
        """Creates a ring network where each node is connected to two other nodes."""
        for node in node_list:
            node
            prev_node = node_list[i - 1]
            next_node = node_list[(i + 1) % len(node_list)]
            node.add_peer(prev_node)
            node.add_peer(next_node)