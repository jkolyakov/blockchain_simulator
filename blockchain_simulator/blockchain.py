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

    def add_block(self, block: BlockBase, difficulty: int) -> bool:
        """Adds a block to the blockchain."""
        if not self.is_valid_block(block, difficulty):
            return False
        
        if not self.contains_block(block.block_id):
            self.blocks[block.block_id] = block
            logging.warning(f"Block {block.block_id} added to the blockchain!")
            return True
        
        logging.warning(f"Block {block.block_id} already exists!")
        return False
    
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
        if not block.parent: # TODO: Fix issue where children are being proposed before parents
            return False  # Has no parent
        if not block.verify_block(difficulty) or self.contains_block(block.block_id):
            return False  # PoW block is invalid
        return True

# ============================
# BLOCKCHAIN IMPLEMENTATION
# ============================

class BasicBlockchain(BlockchainBase):
    """Basic blockchain implementation"""

    def __init__(self, block_class: Type['BlockBase'], genesis_block: 'BlockBase'):
        super().__init__(block_class, genesis_block)

    def add_block(self, block: 'BlockBase', node: 'NodeBase') -> bool:
        """Adds a block and updates the weight.
        Assumes parents are properly linked to block.
        Assumes that block param is a clone of the original block before adding.
        """
        if not self.is_valid_block(block, node.mining_difficulty):
            return False
        
        if self.contains_block(block.block_id):
            logging.warning(f"Block {block.block_id} already exists!")
            return False # Block already exists
        
        # If parent block is missing, add to node's pending blocks which the GossipProtocol will handle
        if not self.contains_block(block.parent.block_id):
            node.pending_blocks.setdefault(block.parent.block_id, []).append(block)            
            logging.warning(f"Block {block.block_id} is waiting for parent {block.parent.block_id}. Queued in pending_blocks.")
            return False # Parent block is missing
        
        parent = self.get_block(block.parent.block_id)
        block.parent = parent # Reassign parent block to the local parent block object
        # Add the block to the blockchain
        self.blocks[block.block_id] = block
        
        if block not in parent.children:
            parent.children.append(block) # Connect to parent
            
        return True