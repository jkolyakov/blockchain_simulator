import sys
import os

# Get the parent directory of blockchain simulator
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Append the parent directory to sys.path
sys.path.append(parent_dir)

from blockchain_simulator.block import PoWBlock
from blockchain_simulator.blockchain import BasicBlockchain
from blockchain_simulator.node import BasicNode
from blockchain_simulator.simulator import BlockchainSimulator
from blockchain_simulator.consensus import GHOSTProtocol, LongestChainProtocol, PoSProtocol, DAGProtocol

if __name__ == "__main__":
    sim = BlockchainSimulator(
        num_nodes=10,  # Increased node count for a larger simulation
        avg_peers=4,
        max_delay=10,
        consensus_impl=GHOSTProtocol,
        blockchain_impl=BasicBlockchain,
        block_class=PoWBlock,
        node_class=BasicNode,
        network_topology="random"
    )

    print("🚀 Starting Blockchain Simulation...")
    sim.start_mining(node_ids=[0, 1, 2])  # Start mining on multiple nodes
    sim.run(duration=20) # Run the simulation for 50 seconds