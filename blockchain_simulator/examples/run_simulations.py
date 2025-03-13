from blockchain_simulator import block, blockchain, node, simulator, consensus
from block import BasicBlock
from blockchain import BasicBlockchain
from node import Node
from simulator import BlockchainSimulator
from consensus import GHOSTProtocol, LongestChainProtocol, PoSProtocol, DAGProtocol

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