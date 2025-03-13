import simpy
import random
import logging
import pandas as pd
import matplotlib.pyplot as plt
from blockchain_simulator.node import Node

logging.basicConfig(filename="blockchain_simulation.log", level=logging.INFO, format="%(message)s")

class BlockchainSimulator:
    """API for running blockchain network simulations with custom implementations."""

    def __init__(self, num_nodes=10, avg_peers=3, max_delay=5, consensus_protocol=None, blockchain_impl=None, block_class=None):
        self.env = simpy.Environment()
        self.num_nodes = num_nodes
        self.max_delay = max_delay
        self.consensus_protocol = consensus_protocol() if consensus_protocol else None
        self.blockchain = blockchain_impl(block_class) if blockchain_impl else None
        self.nodes = [Node(self.env, i, self, self.consensus_protocol, self.blockchain) for i in range(num_nodes)]
        self.metrics = {"total_blocks_mined": 0, "block_propagation_times": []}

        self.create_random_topology(avg_peers)

    def create_random_topology(self, avg_peers):
        """Randomly connects nodes to form a network."""
        for node in self.nodes:
            num_peers = min(random.randint(1, avg_peers), self.num_nodes - 1)
            possible_peers = [n for n in self.nodes if n != node]
            connected_peers = random.sample(possible_peers, num_peers)
            for peer in connected_peers:
                node.add_peer(peer)
                peer.add_peer(node)

    def start_mining(self, node_id):
        """Triggers mining at a specific node."""
        if 0 <= node_id < self.num_nodes:
            self.env.process(self.nodes[node_id].mine_block())

    def run(self, duration=20):
        """Runs the simulation for a given duration."""
        print(f"🚀 Running blockchain simulation for {duration} seconds...\n")
        self.env.run(until=duration)