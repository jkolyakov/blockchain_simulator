from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from blockchain_simulator.block import BlockBase
    from blockchain_simulator.node import NodeBase

# ============================
# BLOCKCHAIN ABSTRACT CLASS
# ============================

class BlockchainBase(ABC):
    """Abstract class for defining custom blockchain implementations."""
    
    def __init__(self, block_class: Type['BlockBase']):
        self.blocks: Dict[int, 'BlockBase'] = {}  # Maps block_id to Block object
        self.block_class: Type['BlockBase'] = block_class
        self.genesis: 'BlockBase' = self.create_genesis_block()
        
    @abstractmethod
    def create_genesis_block(self) -> 'BlockBase':
        """Creates the genesis block."""
        pass

    @abstractmethod
    def add_block(self, block: 'BlockBase', node: 'NodeBase'):
        """Adds a block to the blockchain."""
        pass

    @abstractmethod
    def get_last_block(self) -> 'BlockBase':
        """Returns the last block in the blockchain."""
        pass

# ============================
# BLOCKCHAIN IMPLEMENTATION
# ============================

class BasicBlockchain(BlockchainBase):
    """Basic blockchain implementation."""

    def __init__(self, block_class: Type['BlockBase']):
        super().__init__(block_class)

    def create_genesis_block(self) -> 'BlockBase':
        """Creates a genesis block."""
        genesis = self.block_class(block_id=0, parents=[], miner_id=1, timestamp=0)
        self.blocks[0] = genesis
        return genesis

    def add_block(self, block: 'BlockBase', node: 'NodeBase'):
        """Adds a block and updates the weight.
        Assumes parents are properly linked to block
        """
        self.blocks[block.block_id] = block
        
        for parent in block.parents:
            parent.children.append(block)
    
    def get_last_block(self) -> list['BlockBase']:
        """Returns the last block in the blockchain."""
        return [max(self.blocks.values(), key=lambda b: b.timestamp)] #TODO: inefficient