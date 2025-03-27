from blockchain_simulator.blueprint import NodeBase, BlockBase
from typing import Set, Optional, Generator
import hashlib
class PoWBlock(BlockBase):
    def __init__(self):
        super().__init__()
        self.nonce: int
        self.weight: int

    @staticmethod
    def create_block(parent: BlockBase, time_stamp: float, miner: NodeBase) -> Generator[None, None, BlockBase]:
        """Creates a new block based on the defined block type. Mines if it needs to and only returns upon completion."""
        block = PoWBlock()
        block.parent_id = parent.get_block_id()
        block.miner_id = miner.get_node_id()
        block.timestamp = time_stamp
        block.weight = 1
        block.children_ids = set()
        block.nonce = 0
        block.block_id = block.generate_block_id()

        if miner.get_mining_difficulty() > 0:
            yield miner.get_env().process(block.mine(miner, miner.get_mining_difficulty()))
        return block
    
    @staticmethod
    def create_genesis_block()->BlockBase:
        """Creates a genesis block based on the defined block type."""
        block = PoWBlock()
        block.parent_id = -1
        block.miner_id = -1
        block.timestamp = 0
        block.block_id = 0
        block.weight = 1
        block.children_ids = set()
        block.nonce = 0
        return block
    
    def clone(self) -> BlockBase:
        """Clone the block. Should be overridden by subclasses to copy specific attributes. Meant for sending copy of blocks to other nodes instead of the original block."""
        copy = self.__class__.__new__(self.__class__)
        for key, value in self.__dict__.items():
            if key == "weight":
                setattr(copy, key, 1)
            elif key == "children_ids":
                setattr(copy, key, set())
            else:
                setattr(copy, key, value)
        return copy
        
    def mine(self, node: 'NodeBase', difficulty: int = 4):
        """Proof-of-work mining algorithm."""
        self.nonce = 0
        hash_attempts = 0
        target_prefix = "0" * difficulty
        while node.get_is_mining():
            hash = hashlib.sha256(f"{self.block_id}{self.nonce}".encode()).hexdigest()
            hash_attempts += 1
            if hash.startswith(target_prefix):
                break
            self.nonce += 1
            if hash_attempts % 1000 == 0:
                yield node.get_env().timeout(0.01)
                
    def verify_block(self, owner: NodeBase) -> bool:
        """ Abstract method to verify block validity"""
        if self.nonce is None:
            return False
        
        hash = hashlib.sha256(f"{self.block_id}{self.nonce}".encode()).hexdigest()
        return hash.startswith("0" * owner.get_mining_difficulty())
    
    def generate_block_id(self) -> int:
        """Generates a unique block ID using SHA-256."""
        block_data = f"{self.get_parent_id()}-{self.miner_id}-{self.timestamp}"
        return int(hashlib.sha256(block_data.encode()).hexdigest(), 16) % (10**10)  # Mod to keep ID readable
    
    def get_weight(self) -> int:
        """Returns the weight of the block."""
        return self.weight
    
    def set_weight(self, weight: int):
        """Sets the weight of the block."""
        self.weight = weight
        
    def __repr__(self) -> str:
        """Returns the string representation of the block"""
        return f"Block(id={self.block_id}, miner={self.miner_id}, parent={self.parent_id}, children={self.children_ids}, time={self.timestamp})"