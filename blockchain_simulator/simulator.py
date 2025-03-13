import simpy
import random
import logging
import pandas as pd
import matplotlib.pyplot as plt
from abc import ABC, abstractmethod

# Set up logging
logging.basicConfig(filename="blockchain_simulation.log", level=logging.INFO, format="%(message)s")

# ============================
# ABSTRACT BASE CLASSES
# ============================

class BlockBase(ABC):
    """Abstract base class for defining a custom block structure."""

    def __init__(self, block_id, parent, miner_id, timestamp):
        self.block_id = block_id
        self.parent = parent
        self.miner_id = miner_id
        self.children = []
        self.timestamp = timestamp  # Block creation time

    @abstractmethod
    def update_weight(self):
        """Abstract method to update block weight based on consensus rules."""
        pass

class BlockchainBase(ABC):
    """Abstract class for defining custom blockchain implementations."""
    
    def __init__(self, block_class):
        self.blocks = {}  # Maps block_id to Block object
        self.block_class = block_class  # Custom block class
        self.genesis = self.create_genesis_block()
    
    @abstractmethod
    def create_genesis_block(self):
        """Creates the genesis block."""
        pass
    
    @abstractmethod
    def add_block(self, block, node):
        """Adds a block to the blockchain."""
        pass

class ConsensusProtocol(ABC):
    """Abstract class for defining custom consensus protocols."""
    
    @abstractmethod
    def select_best_block(self, node):
        """Select the best block for a node."""
        pass

# ============================
# BUILT-IN BLOCK IMPLEMENTATIONS
# ============================

class BasicBlock(BlockBase):
    """A simple block structure with basic weight calculation."""

    def __init__(self, block_id, parent, miner_id, timestamp):
        super().__init__(block_id, parent, miner_id, timestamp)
        self.weight = 1  # Default weight

    def update_weight(self):
        """Updates weight based on number of children."""
        self.weight = 1 + sum(child.weight for child in self.children)

# ============================
# BUILT-IN CONSENSUS PROTOCOLS
# ============================

class GHOSTProtocol(ConsensusProtocol):
    """Implements the GHOST consensus protocol."""
    
    def select_best_block(self, node):
        """Selects the heaviest subtree using GHOST."""
        current = node.blockchain.blocks[0]  # Start at genesis
        while current.children:
            current = max(current.children, key=lambda b: b.weight)
        return current

class LongestChainProtocol(ConsensusProtocol):
    """Implements the Longest Chain consensus protocol (Bitcoin-style)."""
    
    def select_best_block(self, node):
        """Selects the longest chain's tip as the best block."""
        current = node.blockchain.blocks[0]  # Start at genesis
        while current.children:
            current = max(current.children, key=lambda b: len(b.children))
        return current

# ============================
# BUILT-IN BLOCKCHAIN IMPLEMENTATIONS
# ============================

class BasicBlockchain(BlockchainBase):
    """Basic blockchain implementation."""
    
    def __init__(self, block_class):
        super().__init__(block_class)

    def create_genesis_block(self):
        """Creates a genesis block."""
        genesis = self.block_class(block_id=0, parent=None, miner_id=-1, timestamp=0)
        self.blocks[0] = genesis
        return genesis
    
    def add_block(self, block, node):
        """Adds a block and updates the weight."""
        self.blocks[block.block_id] = block
        block.parent.add_child(block)
        block.parent.update_weight()

# ============================
# NODE IMPLEMENTATION
# ============================

class Node:
    """Represents a blockchain node."""
    
    def __init__(self, env, node_id, network, consensus_protocol, blockchain):
        self.env = env
        self.node_id = node_id
        self.network = network
        self.peers = []
        self.consensus_protocol = consensus_protocol
        self.blockchain = blockchain
        self.head = blockchain.genesis
        self.received_blocks = {}

    def add_peer(self, peer):
        """Connects this node to a peer."""
        if peer not in self.peers:
            self.peers.append(peer)

    def mine_block(self):
        """Mines a new block and broadcasts it."""
        new_block_id = len(self.blockchain.blocks)
        new_block = self.blockchain.block_class(block_id=new_block_id, parent=self.head, miner_id=self.node_id, timestamp=self.env.now)

        self.blockchain.add_block(new_block, self)
        self.head = self.consensus_protocol.select_best_block(self)

        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} mined block {new_block_id}")
        self.network.metrics["total_blocks_mined"] += 1

        self.broadcast_block(new_block)

    def broadcast_block(self, block):
        """Broadcasts a block to peers."""
        for peer in self.peers:
            delay = random.uniform(1, self.network.max_delay)
            self.env.process(peer.receive_block(block, delay, self.node_id))

    def receive_block(self, block, delay, sender_id):
        """Processes an incoming block after a delay."""
        yield self.env.timeout(delay)

        if block.block_id not in self.received_blocks:
            self.received_blocks[block.block_id] = self.env.now
            self.network.metrics["block_propagation_times"].append(self.env.now - block.timestamp)

        if block.block_id not in self.blockchain.blocks:
            self.blockchain.add_block(block, self)
            self.head = self.consensus_protocol.select_best_block(self)
            logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} received block {block.block_id} from Node {sender_id}")
            self.broadcast_block(block)

# ============================
# BLOCKCHAIN SIMULATOR
# ============================

class BlockchainSimulator:
    """API for running blockchain network simulations with custom implementations."""
    
    def __init__(self, num_nodes=10, avg_peers=3, max_delay=5, consensus_protocol=GHOSTProtocol, blockchain_impl=BasicBlockchain, block_class=BasicBlock):
        self.env = simpy.Environment()
        self.num_nodes = num_nodes
        self.max_delay = max_delay
        self.consensus_protocol = consensus_protocol()
        self.blockchain = blockchain_impl(block_class)
        self.nodes = [Node(self.env, i, self, self.consensus_protocol, self.blockchain) for i in range(num_nodes)]
        self.metrics = {
            "total_blocks_mined": 0,
            "block_propagation_times": [],
            "orphaned_blocks": 0
        }

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
        """Runs the simulation."""
        self.env.run(until=duration)

# ============================
# TESTING THE MODULAR API
# ============================

if __name__ == "__main__":
    sim = BlockchainSimulator(num_nodes=10, avg_peers=3, max_delay=3, consensus_protocol=GHOSTProtocol, blockchain_impl=BasicBlockchain, block_class=BasicBlock)
    sim.start_mining(node_id=0)
    sim.run(duration=50)