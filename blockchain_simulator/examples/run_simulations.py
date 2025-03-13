import sys
import os

# Get the parent directory of blockchain simulator
parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Append the parent directory to sys.path
sys.path.append(parent_dir)

from blockchain_simulator.block import BasicBlock
from blockchain_simulator.blockchain import BasicBlockchain
from blockchain_simulator.node import BasicNode
from blockchain_simulator.simulator import BlockchainSimulator
from blockchain_simulator.consensus import GHOSTProtocol, LongestChainProtocol, PoSProtocol, DAGProtocol

if __name__ == "__main__":
    sim = BlockchainSimulator(
        num_nodes=10,
        avg_peers=3,
        max_delay=3,
        consensus_protocol=GHOSTProtocol,
        blockchain_impl=BasicBlockchain,
        block_class=BasicBlock
    )

    sim.start_mining(node_id=0)
    sim.run(duration=50)