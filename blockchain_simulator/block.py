from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from blockchain_simulator.block import BlockBase
    from blockchain_simulator.node import NodeBase

import hashlib
import time



# ============================
# BLOCK ABSTRACT CLASS
# ============================

class BlockBase(ABC):
    """Abstract base class for defining a custom block structure."""

    def __init__(self, parent: Optional[BlockBase], miner_id: int, timestamp: Optional[float] = None):
        self.parent: Optional[BlockBase] = parent  # Supports DAG & Chain
        self.miner_id: int = miner_id
        self.children: List[BlockBase] = []
        self.timestamp: float = timestamp if timestamp else time.time()  # Block creation time
        self.block_id: int = self.generate_block_id()  # Auto-generated block ID
        self.weight: int = 1  # Default weight
        self.nodes_seen: set[int] = set()  # Nodes that have seen this block

    def generate_block_id(self) -> int:
        """Generates a unique block ID using SHA-256."""
        block_data = f"{self.parent.block_id if self.parent else 'genesis'}-{self.miner_id}-{self.timestamp}"
        return int(hashlib.sha256(block_data.encode()).hexdigest(), 16) % (10**10)  # Mod to keep ID readable

    @abstractmethod
    def update_weight(self) -> None:
        """Abstract method to update block weight based on consensus rules."""
        pass

    @abstractmethod
    def verify_block(self) -> bool:
        """Abstract method to update block weight based on consensus rules."""
        pass
    
    @abstractmethod
    def mine(self, difficulty: int = 4) -> None:
        """Abstract method to mine the block based on consensus rules."""
        pass
    
    @abstractmethod
    def clone(self) -> BlockBase:
        """Clone the block. Should be overridden by subclasses to copy specific attributes. Meant for sending copy of blocks to other nodes instead of the original block."""
        raise NotImplementedError("Subclasses must implement the clone() method.")

    def __repr__(self):
        return f"Block(id={self.block_id}, miner={self.miner_id}, weight={self.weight}, time={self.timestamp})"


# ============================
# BLOCK IMPLEMENTATIONS
# ============================

class BasicBlock(BlockBase):
    """A simple block structure with basic weight calculation."""

    def __init__(self, parent: Optional[BlockBase], miner_id: int, timestamp: Optional[float] = None):
        super().__init__(parent, miner_id, timestamp)

    def update_weight(self) -> None:
        """Updates weight based on the number of children."""
        self.weight = 1 + sum(child.weight for child in self.children)

    def clone(self) -> BasicBlock:
        copy = BasicBlock.__new__(BasicBlock)  # Bypass __init__
        copy.parent = self.parent
        copy.miner_id = self.miner_id
        copy.timestamp = self.timestamp
        copy.block_id = self.block_id  # Preserve block ID
        copy.weight = self.weight
        copy.children = list(self.children)
        copy.nodes_seen = set(self.nodes_seen)
        return copy

class PoWBlock(BlockBase):
    """A proof-of-work block structure with mining and weight calculation."""

    def __init__(self, parent: Optional[BlockBase], miner_id: int, timestamp: Optional[float] = None):
        super().__init__(parent, miner_id, timestamp)
        self.nonce: Optional[int] = None  # Stores the successful nonce
        self.hash: Optional[str] = None  # Hash of the block
        
    def mine(self, node: 'NodeBase', difficulty: int = 4):
        """Proof-of-work mining algorithm."""
        self.nonce = 0
        hash_attempts = 0
        target_prefix = "0" * difficulty
        while node.is_mining:
            self.hash = hashlib.sha256(f"{self.block_id}{self.nonce}".encode()).hexdigest()
            hash_attempts += 1
            if self.hash.startswith(target_prefix):
                break
            self.nonce += 1
            if hash_attempts % 1000 == 0:
                yield node.env.timeout(0.01)
        # assert self.verify_block(difficulty), f"Block {self.block_id} was not mined correctly!"
        # print(f"⛏️  Mined Block {self.block_id} with nonce {self.nonce} in {hash_attempts} attempts")

    def update_weight(self) -> None:
        """Updates weight based on mining difficulty."""
        self.weight = 1 + sum(child.weight for child in self.children)

    def verify_block(self, difficulty: int) -> bool:
        """Verifies that the block was mined correctly."""
        if self.nonce is None:
            return False  # No nonce means it wasn't mined
        # Check if the stored hash is valid
        block_hash = hashlib.sha256(f"{self.block_id}{self.nonce}".encode()).hexdigest()
        return block_hash.startswith("0" * difficulty) and block_hash == self.hash

    def clone(self) -> PoWBlock:
        """ Clones the block, resetting the weight and children. Meant for sending copy of blocks to other nodes instead of the original block."""
        copy = PoWBlock.__new__(PoWBlock)
        copy.parent = self.parent
        copy.miner_id = self.miner_id
        copy.timestamp = self.timestamp
        copy.block_id = self.block_id
        copy.weight = 1 # Reset weight to 1 
        copy.children = [] # Reset children
        copy.nodes_seen = set(self.nodes_seen)
        copy.nonce = self.nonce
        copy.hash = self.hash
        return copy
    
class PoSBlock(BlockBase):
    """A proof-of-stake block structure where weight depends on stake."""

    def __init__(self, parent: Optional[BlockBase], miner_id: int, stake: float, timestamp: Optional[float] = None):
        super().__init__(parent, miner_id, timestamp)
        self.stake = stake  # Stake value for the miner

    def update_weight(self) -> None:
        """Updates weight based on stake contribution."""
        self.weight = self.stake + sum(child.weight for child in self.children)