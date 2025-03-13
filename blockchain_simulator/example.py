from blockchain_simulator import BlockchainSimulator, BlockchainBase, BlockBase, ConsensusProtocol
import random

# ============================
# 🏗️ Custom Proof-of-Work Block
# ============================
class PoWBlock(BlockBase):
    """A block that uses a simple Proof-of-Work mechanism."""
    
    def __init__(self, block_id, parents, miner_id, timestamp):
        super().__init__(block_id, parents, miner_id, timestamp)
        self.nonce = None  # PoW nonce
        self.weight = 1  # Default weight

    def mine(self, difficulty=4):
        """Simple Proof-of-Work: Find a nonce where hash(block_id + nonce) starts with '0000'."""
        self.nonce = 0
        while not str(hash(str(self.block_id) + str(self.nonce))).startswith("0" * difficulty):
            self.nonce += 1
        print(f"⛏️  Mined Block {self.block_id} with nonce {self.nonce}")

    def update_weight(self):
        """Updates weight based on number of children (for PoW, weight remains constant)."""
        self.weight = 1 + sum(child.weight for child in self.children)

# ============================
# ⛓️ Custom Proof-of-Work Blockchain
# ============================
class PoWBlockchain(BlockchainBase):
    """A blockchain that requires Proof-of-Work for adding blocks."""
    
    def __init__(self, block_class):
        super().__init__(block_class)

    def create_genesis_block(self):
        """Creates the genesis block."""
        genesis = self.block_class(block_id=0, parents=None, miner_id=-1, timestamp=0)
        self.blocks[0] = genesis
        return genesis
    
    def add_block(self, block, node):
        """Adds a block to the blockchain only after PoW is completed."""
        block.mine(difficulty=4)  # Require mining before adding to chain
        self.blocks[block.block_id] = block
        for parent in block.parents:
            if parent:
                parent.children.append(block)
                parent.update_weight()

# ============================
# 🔗 Custom PoW Consensus Protocol
# ============================
class PoWConsensus(ConsensusProtocol):
    """Selects the longest chain tip as the best block (Bitcoin-style)."""
    
    def select_best_block(self, node):
        """Chooses the longest chain tip."""
        current = node.blockchain.blocks[0]  # Start at genesis
        while current.children:
            current = max(current.children, key=lambda b: len(b.children))
        return current

# ============================
# 🚀 Running the Custom PoW Blockchain
# ============================
if __name__ == "__main__":
    sim = BlockchainSimulator(
        num_nodes=5,                      # 5 mining nodes
        avg_peers=3,                      # Each node has ~3 peers
        max_delay=2,                       # Low network latency
        consensus_protocol=PoWConsensus,   # Using custom PoW consensus
        blockchain_impl=PoWBlockchain,     # Using custom PoW blockchain
        block_class=PoWBlock               # Using custom PoW block
    )

    sim.start_mining(node_id=0)  # Start mining from Node 0
    sim.run(duration=20)         # Run simulation for 20 seconds