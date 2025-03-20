from __future__ import annotations
from abc import ABC, abstractmethod
import asyncio
from typing import Dict, Type, Optional, TYPE_CHECKING

from blockchain_simulator.broadcastMessage import ConsensusBroadcast

if TYPE_CHECKING:
    from blockchain_simulator.block import BlockBase, PoWBlock
    from blockchain_simulator.node import NodeBase
import logging
# ============================
# BLOCKCHAIN ABSTRACT CLASS
# ============================

class BlockchainBase(ABC):
    """Abstract class for defining custom blockchain implementations."""
    
    def __init__(self, block_class: Type['BlockBase'], owner_node: 'NodeBase'):
        self.blocks: Dict[int, 'BlockBase'] = {}  # Maps block_id to Block object.
        self.block_class: Type['BlockBase'] = block_class
        self.genesis: 'BlockBase' = self.create_block(None, miner_id=0, timestamp=0)
        self.blocks[self.genesis.block_id] = self.genesis # Add genesis block to the blockchain
        self.owner: 'NodeBase' = owner_node                 #stores the node that owns the blockchain object
        self.head = self.genesis                      # Stores the head of the main chain for this node.

    def create_block(self, parent: BlockBase, miner_id: int, timestamp: float) -> BlockBase:
        """Creates a new block based on the defined block type."""
        new_block = self.block_class(parent=parent, miner_id=miner_id, timestamp=timestamp)
        return new_block  # The block ID is generated inside the class

    @abstractmethod
    def add_block(self, block: BlockBase) -> bool:
        """Adds a block to the blockchain."""
        # if not self.is_valid_block(block):
        #     return False
        
        # if block.block_id not in self.blocks:
        #     self.blocks[block.block_id] = block
        #     logging.warning(f"Block {block.block_id} added to the blockchain!")
        #     return True
        
        # logging.warning(f"Block {block.block_id} already exists!")
        # return False
        pass
    
    # For testing purposes
    def get_block(self, block_id: int) -> Optional['BlockBase']:
        """Get a block by its ID."""
        return self.blocks.get(block_id)
    
    # For testing purposes
    def contains_block(self, block_id: int) -> bool:
        """Check if the blockchain contains a block with the given ID."""
        return block_id in self.blocks
    
    def is_valid_block(self, block: 'BlockBase') -> bool:
        """Checks if a block is valid before adding it to the chain."""        
        # TODO: Note no parent block is needed because blocks are being proposed in batches? note sure why but ensuring parent exists and is in the chain already fails
        if not block.parent:
            return False  # Has no parent
        if not block.verify_block():
            return False  # PoW block is invalid
        
        return True
    
    async def add_consensus_block_to_chain(self) -> bool:
        """Invokes the underlying consensus protocol and adds the propogates the output of the consensus to nodes in the network for them to add it in their blockchain"""

        consensus_output = await self.owner.consensus_protocol.execute_consensus(self.owner)
        self.add_block(consensus_output)

        #create the broadcastmessage to be sent to other nodes
        message_payload = {}
        message_payload['block'] = consensus_output
        message_payload['consensus_type'] = ConsensusBroadcast.CONSENSUS_TYPE['final']
        broadcast_message = ConsensusBroadcast(self.node_id,message_payload, self.private_key)

        broadcast_message.send_message_to_peers(self.owner)

    async def receive_final_consensus_block(self, broadcast_message: ConsensusBroadcast) -> bool:
        """processes the output of the broadcast message containing the final consensus block. Returns true of the processing is successful"""
        block = broadcast_message.data['block']
        if not block.verify_block():
            log_message = broadcast_message.to_json()
            print(f"Node {self.owner.node_id} received an invalid final consensus block {log_message}")
            return False
        self.blockchain.add_block(broadcast_message.data['block'])
        return True

# ============================
# BLOCKCHAIN IMPLEMENTATION
# ============================

class BasicBlockchain(BlockchainBase):
    """Basic blockchain implementation."""

    def __init__(self, block_class: Type['BlockBase'], owner_node: 'NodeBase'):
        super().__init__(block_class,owner_node)

    def create_genesis_block(self) -> 'BlockBase':
        """Creates a genesis block."""
        genesis = self.block_class(block_id=0, miner_id=1, timestamp=0)
        self.blocks[0] = genesis
        return genesis

    def add_block(self, block: 'BlockBase') -> bool:
        """Adds a block and updates the weight.
        Assumes parents are properly linked to block
        """
        logging.warning(f"Adding block {block.block_id} to the blockchain")
        if not self.is_valid_block(block):
            logging.warning(f"Block {block.block_id} is not a valid block")
            return False
        
        if block.block_id in self.blocks:
            logging.warning(f"Block {block.block_id} already exists!")
            return False # Block already exists
        
        # Add the block to the blockchain
        self.blocks[block.block_id] = block
        # block.parent.children.append(block) # Assume all parents have blocks because genesis block must have been created already

        if not block.parent and not block.parent in self.blocks:
            logging.warning(f"Parent block {block.parent.block_id} of {block.block_id} is missing!")
            
        # Connect to parent if it exists
        if block.parent and block.parent.block_id in self.blocks:
            if block not in block.parent.children:
                block.parent.children.append(block)
                self.owner.consensus_protocol.select_best_block(self.owner)
        return True

        