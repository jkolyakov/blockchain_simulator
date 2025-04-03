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
from blockchain_simulator.network_topology import SimpleRandomTopology, StarTopology, FullyConnectedTopology, RingTopology, TreeTopology
from blockchain_simulator.broadcast import GossipProtocol

#ring is super fast, so is star, tree is fine
#fully connected is much slower bs more network congestion

#so show one and the of fast and then fully connected and reason about it

#fully connected O(n^2) vs star O(n) vs ring O(n) vs tree O(log n) (when balanced) else O(n)


# thruput as func of  mining difficulty 
'''
#4. Mining Difficulty 0
if __name__ == "__main__":
    sim = BlockchainSimulator(
        network_topology_class = TreeTopology, 
        consensus_protocol_class= GHOSTProtocol, 
        blockchain_class= Blockchain, 
        broadcast_protocol_class= GossipProtocol,
        node_class= Node,
        block_class= PoWBlock,
        num_nodes=25,
        mining_difficulty=0,
        render_animation= False,
        min_delay= 0.5,
        max_delay= 0.5,
        consensus_interval= 0.15,
        drop_rate=0,
        set_bandwidth= False,
    )

    print("🚀 Starting Blockchain Simulation...")
    sim.start_mining(10)  # Start mining on multiple nodes
    sim.run(duration=10)  # Run the simulation for 50 seconds

'''



'''
#4. Mining Difficulty 5
if __name__ == "__main__":
    sim = BlockchainSimulator(
        network_topology_class = TreeTopology, 
        consensus_protocol_class= GHOSTProtocol, 
        blockchain_class= Blockchain, 
        broadcast_protocol_class= GossipProtocol,
        node_class= Node,
        block_class= PoWBlock,
        num_nodes=25,
        mining_difficulty=5,
        render_animation= False,
        min_delay= 0.5,
        max_delay= 0.5,
        consensus_interval= 0.15,
        drop_rate=0,
        set_bandwidth= False,
    )

    print("🚀 Starting Blockchain Simulation...")
    sim.start_mining(10)  # Start mining on multiple nodes
    sim.run(duration=10)  # Run the simulation for 50 seconds

'''


#drop rate demonstration
'''
# drop rate 100 
if __name__ == "__main__":
    sim = BlockchainSimulator(
        network_topology_class = StarTopology, 
        consensus_protocol_class= GHOSTProtocol, 
        blockchain_class= Blockchain, 
        broadcast_protocol_class= GossipProtocol,
        node_class= Node,
        block_class= PoWBlock,
        num_nodes=25,
        mining_difficulty=3,
        render_animation= False,
        min_delay= 0.5,
        max_delay= 0.5,
        consensus_interval= 0.15,
        drop_rate=100,
        set_bandwidth= False,
    )

    print("🚀 Starting Blockchain Simulation...")
    sim.start_mining(10)  # Start mining on multiple nodes
    sim.run(duration=10)  # Run the simulation for 50 seconds
'''


'''
# drop rate 0 
if __name__ == "__main__":
    sim = BlockchainSimulator(
        network_topology_class = StarTopology, 
        consensus_protocol_class= GHOSTProtocol, 
        blockchain_class= Blockchain, 
        broadcast_protocol_class= GossipProtocol,
        node_class= Node,
        block_class= PoWBlock,
        num_nodes=25,
        mining_difficulty=3,
        render_animation= False,
        min_delay= 0.5,
        max_delay= 0.5,
        consensus_interval= 0.15,
        drop_rate=0,
        set_bandwidth= False,
    )

    print("🚀 Starting Blockchain Simulation...")
    sim.start_mining(10)  # Start mining on multiple nodes
    sim.run(duration=10)  # Run the simulation for 50 seconds

'''


#network demonstration
'''
#tree topolgy 
if __name__ == "__main__":
    sim = BlockchainSimulator(
        network_topology_class = TreeTopology, 
        consensus_protocol_class= GHOSTProtocol, 
        blockchain_class= Blockchain, 
        broadcast_protocol_class= GossipProtocol,
        node_class= Node,
        block_class= PoWBlock,
        num_nodes=25,
        mining_difficulty=3,
        render_animation= False,
        min_delay= 0.5,
        max_delay= 0.5,
        consensus_interval= 0.15,
        drop_rate=50,
        set_bandwidth= False,
    )

    print("🚀 Starting Blockchain Simulation...")
    sim.start_mining(10)  # Start mining on multiple nodes
    sim.run(duration=10)  # Run the simulation for 50 seconds

'''

'''
#SimpleRandomTopology

if __name__ == "__main__":
    sim = BlockchainSimulator(
        network_topology_class = SimpleRandomTopology,
        consensus_protocol_class= GHOSTProtocol, 
        blockchain_class= Blockchain, 
        broadcast_protocol_class= GossipProtocol,
        node_class= Node,
        block_class= PoWBlock,
        num_nodes=25,
        mining_difficulty=3,
        render_animation= False,
        min_delay= 0.5,
        max_delay= 0.5,
        consensus_interval= 0.15,
        drop_rate=50,
        set_bandwidth= False,
    )

    print("🚀 Starting Blockchain Simulation...")
    sim.start_mining(10)  # Start mining on multiple nodes
    sim.run(duration=10)  # Run the simulation for 50 seconds

'''


'''
# with bandwidth on





'''


if __name__ == "__main__":
    sim = BlockchainSimulator(
        network_topology_class = TreeTopology, 
        consensus_protocol_class= GHOSTProtocol, 
        blockchain_class= Blockchain, 
        broadcast_protocol_class= GossipProtocol,
        node_class= Node,
        block_class= PoWBlock,
        num_nodes=25,
        mining_difficulty=0,
        render_animation= False,
        min_delay= 0.5,
        max_delay= 0.5,
        consensus_interval= 0.15,
        drop_rate=0,
        set_bandwidth= False,
    )

    print("🚀 Starting Blockchain Simulation...")
    sim.start_mining(10)  # Start mining on multiple nodes
    sim.run(duration=10)  # Run the simulation for 50 seconds