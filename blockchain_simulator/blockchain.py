from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Type, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from blockchain_simulator.block import BlockBase, PoWBlock
    from blockchain_simulator.node import NodeBase
import logging
# ============================
# BLOCKCHAIN ABSTRACT CLASS
# ============================

class BlockchainBase(ABC):
    """Abstract class for defining custom blockchain implementations."""
    
    def __init__(self, block_class: Type['BlockBase'], genesis_block: 'BlockBase'):
        self.blocks: Dict[int, 'BlockBase'] = {}  # Maps block_id to Block object
        self.block_class: Type['BlockBase'] = block_class
        self.genesis: 'BlockBase' = genesis_block
        self.blocks[self.genesis.block_id] = self.genesis # Add genesis block to the blockchain
        self.head = self.genesis  # The head of the blockchain

    def create_block(self, parent: 'BlockBase', miner_id: int, timestamp: float) -> BlockBase:
        """Creates a new block based on the defined block type."""
        new_block = self.block_class(parent=parent, miner_id=miner_id, timestamp=timestamp)
        return new_block  # The block ID is generated inside the class

    def add_block(self, block: 'BlockBase', node: 'NodeBase') -> bool:
        """Adds a block and updates the weight.
        Assumes parents are properly linked to block.
        Assumes that block param is a clone of the original block before adding.
        """
        if not self.is_valid_block(block, node.mining_difficulty):
            return False
        
        if self.contains_block(block.block_id):
            return False # Block already exists
        
        # parent is guaranteed to be on blockchain, so get the local parent block object
        parent = self.get_block(block.parent.block_id)
        if parent is None:
            logging.error(f"Parent block {block.parent.block_id} not found!")
            # return False
        block.parent = parent # Reassign parent block to the local parent block object
        
        # Add the block to the local blockchain
        self.blocks[block.block_id] = block
        node.network.animator.log_event(f"Node {node.node_id} added block {block} to the blockchain", timestamp=node.env.now)
        
        if block not in parent.children:
            parent.children.append(block) # Connect to local parent
        return True
    
    # For testing purposes
    def get_block(self, block_id: int) -> Optional['BlockBase']:
        """Get a block by its ID."""
        return self.blocks.get(block_id)
    
    # For testing purposes
    def contains_block(self, block_id: int) -> bool:
        """Check if the blockchain contains a block with the given ID."""
        return block_id in self.blocks
    
    def is_valid_block(self, block: 'BlockBase', difficulty: int) -> bool:
        """Checks if a block is valid before adding it to the chain."""
        if not block.parent:
            return False  # Has no parent
        if not block.verify_block(difficulty) or self.contains_block(block.block_id):
            return False  # Block is invalid
        return True
    
    def __repr__(self):
        # Return a string representation of the blockchain
        return f"Blockchain(blocks={len(self.blocks)}, head={self.head.block_id}, genesis={self.genesis.block_id}, block_class={self.block_class.__name__})"

# ============================
# BLOCKCHAIN IMPLEMENTATION
# ============================

class BasicBlockchain(BlockchainBase):
    """Basic blockchain implementation"""

    pass # No need to implement anything new for this blockchain