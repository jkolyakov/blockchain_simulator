import sys
import os

# Get the parent directory of blockchain simulator
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Append the parent directory to sys.path
sys.path.append(parent_dir)

from blockchain_simulator.block import  PoWBlock
from blockchain_simulator.blockchain import Blockchain
from blockchain_simulator.node import Node
from blockchain_simulator.simulator import BlockchainSimulator
from blockchain_simulator.consensus import GHOSTProtocol
from blockchain_simulator.network_topology import SimpleRandomTopology, StarTopology, FullyConnectedTopology, RingTopology
from blockchain_simulator.broadcast import GossipProtocol

if __name__ == "__main__":
    sim = BlockchainSimulator(
        network_topology_class = SimpleRandomTopology, 
        consensus_protocol_class= GHOSTProtocol, 
        blockchain_class= Blockchain, 
        broadcast_protocol_class= GossipProtocol,
        node_class= Node,
        block_class= PoWBlock,
        num_nodes=10,
        mining_difficulty=2,
        render_animation= True,
        min_delay= 0.1,
        max_delay= 0.5,
        consensus_interval= 0.1,
        drop_rate= 20
    )

    print("🚀 Starting Blockchain Simulation...")
    sim.start_mining(10)  # Start mining on multiple nodes
    sim.run(duration=20)  # Run the simulation for 50 seconds