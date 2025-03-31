from __future__ import annotations
from abc import ABC, abstractmethod, staticmethod
from typing import Optional, Set, Dict, List, TYPE_CHECKING
import hashlib
import time

if TYPE_CHECKING:
    from blockchain_simulator.blueprint import BlockBase, NodeBase

class PoWBlock(BlockBase):
    
    @staticmethod
    def create_block(parent: 'BlockBase', time_stamp: float, miner: 'NodeBase')->'BlockBase':
        """Creates a new block based on the defined block type."""
        block = PoWBlock.__new__(PoWBlock)
        block.block_id = block.generate_block_id()
        block.parent = parent
        block.timestamp = time_stamp
        block.miner_id = miner.node_id
        block.children = []
        block.nonce = None
        return block

    @staticmethod
    def create_genesis_block()->'BlockBase':
        """Creates a genesis block based on the defined block type."""
        block = PoWBlock.__new__(PoWBlock)
        block.block_id = 0
        block.parent = None
        block.timestamp = time.time()
        block.miner_id = -1
        block.children = []
        block.nonce = None
        return block
    
    def clone(self) -> 'BlockBase':
        copy = PoWBlock.__new__(PoWBlock)
        copy.block_id = self.block_id
        copy.parent = self.parent
        copy.children = list(self.children)
        copy.timestamp = self.timestamp
        copy.miner_id = self.miner_id
        copy.nonce = self.nonce
        copy.hash = self.hash
        return copy
    
    def verify_block(self, owner: 'NodeBase') -> bool:
        """ Abstract method to verify block validity"""
        if self.nonce is None:
            return False
        block_hash = hashlib.sha256(f"{self.block_id}{self.nonce}".encode()).hexdigest()
        return block_hash.startswith("0" * owner.difficulty) and block_hash == self.hash
    
    def get_block_id(self) -> int:
        return self.block_id
    
    def get_parent_id(self) -> int:
        return self.parent.block_id if self.parent else -1
    
    def get_children_ids(self) -> List[int]:
        """Returns the children block ids"""
        return [child.block_id for child in self.children]
    
    def add_child(self, child_id: int) -> None:
        self.children.append(child_id)

    def set_parent(self, parent_id: int) -> None:
        self.parent.block_id = parent_id   

    def get_weight(self) -> int:
        return self.weight
    
    def set_weight(self, weight: int) -> None:
        self.weight = weight

    def __repr__(self) -> str:
        """Returns the string representation of the block"""
        return f"Block(id={self.block_id}, miner={self.miner_id}, weight={self.weight}, time={self.timestamp})"
    
    def generate_block_id(self) -> int:
        """Generates a unique block ID using SHA-256."""
        block_data = f"{self.parent.block_id if self.parent else 'genesis'}-{self.miner_id}-{self.timestamp}"
        return int(hashlib.sha256(block_data.encode()).hexdigest(), 16) % (10**10)
    

