import simpy
import random
import logging
import pandas as pd
import matplotlib.pyplot as plt
from abc import ABC, abstractmethod

# Set up logging
logging.basicConfig(filename="blockchain_simulation.log", level=logging.INFO, format="%(message)s")

class Block:
    """Represents a blockchain block."""
    def __init__(self, block_id, parent, miner_id, timestamp):
        self.block_id = block_id
        self.parent = parent
        self.miner_id = miner_id
        self.children = []
        self.weight = 1  # Used for consensus rule
        self.timestamp = timestamp  # Block creation time

    def add_child(self, child):
        """Add a child block and update weight recursively."""
        self.children.append(child)

class ConsensusProtocol(ABC):
    """Abstract base class for defining a custom blockchain consensus protocol."""
    
    @abstractmethod
    def select_best_block(self, node):
        """Select the best block for a node based on the consensus algorithm."""
        pass

class GHOSTProtocol(ConsensusProtocol):
    """Implements the GHOST consensus protocol."""
    
    def select_best_block(self, node):
        """Selects the heaviest subtree using GHOST."""
        current = node.blockchain[0]  # Start at the genesis block
        while current.children:
            current = max(current.children, key=lambda b: b.weight)
        return current

class Node:
    """Represents a blockchain node."""
    def __init__(self, env, node_id, network, consensus_protocol):
        self.env = env
        self.node_id = node_id
        self.network = network
        self.peers = []
        self.blockchain = {}
        self.head = None
        self.received_blocks = {}
        self.consensus_protocol = consensus_protocol  # Use a provided consensus protocol

        # Initialize with Genesis Block
        genesis = Block(block_id=0, parent=None, miner_id=-1, timestamp=0)
        self.blockchain[0] = genesis
        self.head = genesis

    def add_peer(self, peer):
        """Connect this node to another node."""
        if peer not in self.peers:
            self.peers.append(peer)

    def mine_block(self):
        """Mine a new block and broadcast it."""
        new_block_id = len(self.blockchain)
        new_block = Block(block_id=new_block_id, parent=self.head, miner_id=self.node_id, timestamp=self.env.now)

        self.blockchain[new_block_id] = new_block
        self.head.add_child(new_block)
        self.head = new_block

        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} mined block {new_block_id}")
        self.network.metrics["total_blocks_mined"] += 1

        self.broadcast_block(new_block)

    def broadcast_block(self, block):
        """Broadcast a block to peers."""
        for peer in self.peers:
            delay = random.uniform(1, self.network.max_delay)
            self.env.process(peer.receive_block(block, delay, self.node_id))

    def receive_block(self, block, delay, sender_id):
        """Process an incoming block after a delay."""
        yield self.env.timeout(delay)

        # Log block propagation time
        if block.block_id not in self.received_blocks:
            self.received_blocks[block.block_id] = self.env.now
            self.network.metrics["block_propagation_times"].append(self.env.now - block.timestamp)

        if block.block_id not in self.blockchain:
            self.blockchain[block.block_id] = block
            block.parent.add_child(block)

            # Apply custom consensus protocol
            self.head = self.consensus_protocol.select_best_block(self)

            logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} received block {block.block_id} from Node {sender_id}")
            self.broadcast_block(block)

class BlockchainSimulator:
    """API for running blockchain network simulations with custom consensus protocols."""
    
    def __init__(self, num_nodes=10, avg_peers=3, max_delay=5, consensus_protocol=GHOSTProtocol):
        self.env = simpy.Environment()
        self.num_nodes = num_nodes
        self.max_delay = max_delay
        self.consensus_protocol = consensus_protocol()
        self.nodes = [Node(self.env, i, self, self.consensus_protocol) for i in range(num_nodes)]
        self.metrics = {
            "total_blocks_mined": 0,
            "block_propagation_times": [],
            "orphaned_blocks": 0
        }

        self.create_random_topology(avg_peers)

    def create_random_topology(self, avg_peers):
        """Randomly connect nodes to form a network."""
        for node in self.nodes:
            num_peers = min(random.randint(1, avg_peers), self.num_nodes - 1)
            possible_peers = [n for n in self.nodes if n != node]
            connected_peers = random.sample(possible_peers, num_peers)
            for peer in connected_peers:
                node.add_peer(peer)
                peer.add_peer(node)

    def start_mining(self, node_id):
        """Trigger mining at a specific node."""
        if 0 <= node_id < self.num_nodes:
            self.env.process(self.nodes[node_id].mine_block())

    def run(self, duration=20):
        """Run the simulation."""
        self.env.run(until=duration)
        self.calculate_metrics()
        self.visualize_metrics()

    def calculate_metrics(self):
        """Analyze blockchain performance metrics."""
        orphaned_blocks = 0
        for node in self.nodes:
            for block in node.blockchain.values():
                if block.block_id != 0 and block.weight == 1:
                    orphaned_blocks += 1

        self.metrics["orphaned_blocks"] = orphaned_blocks
        logging.info(f"Total Blocks Mined: {self.metrics['total_blocks_mined']}")
        logging.info(f"Total Orphaned Blocks: {self.metrics['orphaned_blocks']}")

    def visualize_metrics(self):
        """Plot key blockchain metrics."""
        df = pd.DataFrame({"block_propagation_time": self.metrics["block_propagation_times"]})

        plt.figure(figsize=(8, 5))
        plt.hist(df["block_propagation_time"], bins=10, alpha=0.75)
        plt.xlabel("Block Propagation Time (seconds)")
        plt.ylabel("Frequency")
        plt.title("Block Propagation Times")
        plt.show()

# ===========================
# EXAMPLE: CUSTOM CONSENSUS PROTOCOL
# ===========================
class LongestChainProtocol(ConsensusProtocol):
    """A simple longest-chain consensus protocol (like Bitcoin)."""
    
    def select_best_block(self, node):
        """Select the longest chain's tip as the best block."""
        current = node.blockchain[0]  # Start at genesis
        while current.children:
            current = max(current.children, key=lambda b: len(b.children))
        return current

# ===========================
# TESTING THE ENHANCED API
# ===========================
if __name__ == "__main__":
    # Using default GHOST consensus
    sim1 = BlockchainSimulator(num_nodes=10, avg_peers=3, max_delay=3, consensus_protocol=GHOSTProtocol)
    sim1.start_mining(node_id=0)
    sim1.run(duration=50)

    # Using Longest-Chain (Bitcoin-style) consensus
    sim2 = BlockchainSimulator(num_nodes=10, avg_peers=3, max_delay=3, consensus_protocol=LongestChainProtocol)
    sim2.start_mining(node_id=0)
    sim2.run(duration=50)