import sys
import os

# Get the parent directory of blockchain simulator
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Append the parent directory to sys.path
sys.path.append(parent_dir)

from blockchain_simulator.blockchain_refactor import Blockchain
from blockchain_simulator.node_refactor import Node
from blockchain_simulator.consensus_refactor import GHOSTProtocol
from blockchain_simulator.simulator import BlockchainSimulator
from blockchain_simulator.block_refactor import PoWBlock
from blockchain_simulator.broadcast_refactor import GossipProtocol
from blockchain_simulator.simulator_refactor import BlockchainSimulator
from blockchain_simulator.network_topology import SimpleRandomTopology

if __name__ == "__main__":
    sim = BlockchainSimulator(
        num_nodes=10,  # Increased node count for a larger simulation
        consensus_protocol_class=GHOSTProtocol,
        blockchain_class=Blockchain,
        block_class=PoWBlock,
        broadcast_protocol_class=GossipProtocol,
        node_class=Node,
        network_topology_class=SimpleRandomTopology,
        mining_difficulty=4,
        drop_rate=20,
        render_animation=True,
    )

    print("🚀 Starting Blockchain Simulation...")
    sim.start_mining(10)  # Start mining on multiple nodes
    sim.run(duration=20)  # Run the simulation for 50 seconds