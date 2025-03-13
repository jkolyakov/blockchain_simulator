import simpy
import random
import logging
import pandas as pd
import matplotlib.pyplot as plt
from typing import Type, Optional, List, Dict
from blockchain_simulator.node import NodeBase, BasicNode
from blockchain_simulator.blockchain import BlockchainBase
from blockchain_simulator.block import BlockBase
from blockchain_simulator.consensus import ConsensusProtocol

# Configure logging
logging.basicConfig(filename="blockchain_simulation.log", level=logging.INFO, format="%(message)s")

class BlockchainSimulator:
    """API for running blockchain network simulations with custom implementations."""

    def __init__(
        self,
        num_nodes: int = 10,
        avg_peers: int = 3,
        max_delay: int = 5,
        consensus_protocol: Optional[Type[ConsensusProtocol]] = None,
        blockchain_impl: Optional[Type[BlockchainBase]] = None,
        block_class: Optional[Type[BlockBase]] = None,
        node_class: Type[NodeBase] = BasicNode
    ):
        """
        Initializes the blockchain simulator.

        :param num_nodes: Number of nodes in the simulation
        :param avg_peers: Average number of peers per node
        :param max_delay: Maximum network delay in seconds
        :param consensus_protocol: Consensus protocol class
        :param blockchain_impl: Blockchain implementation class
        :param block_class: Block class
        :param node_class: Node class (default: BasicNode)
        """
        self.env: simpy.Environment = simpy.Environment()
        self.num_nodes: int = num_nodes
        self.max_delay: int = max_delay
        self.consensus_protocol: Optional[ConsensusProtocol] = consensus_protocol() if consensus_protocol else None
        self.blockchain: Optional[BlockchainBase] = blockchain_impl(block_class) if blockchain_impl else None
        self.nodes: List[NodeBase] = [
            node_class(self.env, i, self, self.consensus_protocol, self.blockchain)
            for i in range(num_nodes)
        ]
        self.metrics: Dict[str, List[float]] = {
            "total_blocks_mined": [],
            "block_propagation_times": []
        }

        self.create_random_topology(avg_peers)

    def create_random_topology(self, avg_peers: int):
        """
        Randomly connects nodes to form a network.

        :param avg_peers: Average number of peers per node.
        """
        for node in self.nodes:
            num_peers: int = min(random.randint(1, avg_peers), self.num_nodes - 1)
            possible_peers: List[NodeBase] = [n for n in self.nodes if n != node]
            connected_peers: List[NodeBase] = random.sample(possible_peers, num_peers)
            for peer in connected_peers:
                node.add_peer(peer)
                peer.add_peer(node)

    def start_mining(self, node_id: int) -> None:
        """
        Triggers mining at a specific node.

        :param node_id: The ID of the node that will start mining.
        """
        if 0 <= node_id < self.num_nodes:
            self.env.process(self.nodes[node_id].mine_block())

    def run(self, duration: int = 20) -> None:
        """
        Runs the simulation for a given duration.

        :param duration: Duration of the simulation in seconds.
        """
        print(f"🚀 Running blockchain simulation for {duration} seconds...\n")
        self.env.run(until=duration)

        # Display results
        self.display_metrics()

    def display_metrics(self) -> None:
        """
        Prints a summary of blockchain metrics after the simulation.
        """
        print("\n📊 Blockchain Simulation Summary")
        print("-" * 40)
        print(f"🔹 Total Blocks Mined: {len(self.metrics['total_blocks_mined'])}")
        print(f"🔹 Average Block Propagation Time: {self.get_average_propagation_time():.2f} seconds\n")

    def get_average_propagation_time(self) -> float:
        """
        Calculates the average block propagation time.

        :return: The average block propagation time.
        """
        times: List[float] = self.metrics["block_propagation_times"]
        return sum(times) / len(times) if times else 0