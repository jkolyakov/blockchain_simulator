import random
from simulator import BlockchainSimulator
from blockchain import BlockchainBase
from block import BlockBase
from consensus import ConsensusProtocol

# ============================
# 🏗️ Custom Proof-of-Work Block
# ============================
class PoWBlock(BlockBase):
    def __init__(self, block_id, parents, miner_id, timestamp):
        super().__init__(block_id, parents, miner_id, timestamp)
        self.nonce = None
        self.weight = 1

    def mine(self, difficulty=4):
        self.nonce = 0
        while not str(hash(str(self.block_id) + str(self.nonce))).startswith("0" * difficulty):
            self.nonce += 1
        print(f"⛏️  Mined Block {self.block_id} with nonce {self.nonce}")

    def update_weight(self):
        self.weight = 1 + sum(child.weight for child in self.children)

# ============================
# ⛓️ Custom Proof-of-Work Blockchain
# ============================
class PoWBlockchain(BlockchainBase):
    def __init__(self, block_class):
        super().__init__(block_class)

    def create_genesis_block(self):
        genesis = self.block_class(block_id=0, parents=None, miner_id=-1, timestamp=0)
        self.blocks[0] = genesis
        return genesis

    def add_block(self, block, node):
        block.mine(difficulty=4)
        self.blocks[block.block_id] = block
        for parent in block.parents:
            if parent:
                parent.children.append(block)
                parent.update_weight()

# ============================
# 🔗 Custom PoW Consensus Protocol
# ============================
class PoWConsensus(ConsensusProtocol):
    def select_best_block(self, node):
        current = node.blockchain.blocks[0]
        while current.children:
            current = max(current.children, key=lambda b: len(b.children))
        return current

# ============================
# 🚀 Running the Custom PoW Blockchain
# ============================
if __name__ == "__main__":
    sim = BlockchainSimulator(
        num_nodes=5,
        avg_peers=3,
        max_delay=2,
        consensus_protocol=PoWConsensus,
        blockchain_impl=PoWBlockchain,
        block_class=PoWBlock
    )

    sim.start_mining(node_ids=[0])
    sim.run(duration=20)
