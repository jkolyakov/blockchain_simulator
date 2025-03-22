from __future__ import annotations
from abc import ABC, abstractmethod
import asyncio
import copy
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
    
    def __init__(self, block_class: Type['BlockBase'], owner: 'NodeBase'):
        self.blocks: Dict[int, 'BlockBase'] = {}  # Maps block_id to Block object
        self.block_class: Type['BlockBase'] = block_class
        self.genesis: 'BlockBase' = self.create_block(None, miner_id=0, timestamp=0)
        self.blocks[self.genesis.block_id] = self.genesis # Add genesis block to the blockchain
        self.head = self.genesis                      # Stores the head of the main chain for this node.
        self.owner = owner

    def create_block(self, parent: BlockBase, miner_id: int, timestamp: float) -> BlockBase:
        """Creates a new block based on the defined block type."""
        new_block = self.block_class(parent=parent, miner_id=miner_id, timestamp=timestamp)
        return new_block  # The block ID is generated inside the class

    @abstractmethod
    def add_block(self, block: BlockBase) -> bool:
        """Adds a block to the blockchain."""
        pass
    
    @abstractmethod
    def add_self_proposed_block(self, block: BlockBase) -> 'BlockBase':      
        """Adds a block to the blockchain if the block is proposed by the node itself. The function returns the block that is added to the blockchain"""
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
    
    def add_consensus_block_to_chain(self, consensus_output: 'BlockBase') -> bool:
        """Invokes the underlying consensus protocol and adds the propogates the output of the consensus to nodes in the network for them to add it in their blockchain"""
        # 
        consensus_output = self.add_self_proposed_block(consensus_output)
        
        #create the broadcastmessage to be sent to other nodes
        message_payload = {}
        message_payload['block'] = consensus_output
        message_payload['consensus_type'] = ConsensusBroadcast.CONSENSUS_TYPE['final']
        broadcast_message = ConsensusBroadcast(self.owner.node_id,message_payload)
        # print(f"BROADCAST payload {message_payload}")
        
        broadcast_message.send_message_to_peers(self.owner)

    def receive_final_consensus_block(self, broadcast_message: ConsensusBroadcast) -> bool:
        """processes the output of the broadcast message containing the final consensus block. Returns true of the processing is successful"""
        block = copy.deepcopy(broadcast_message.data['block'])
        

        # if self.owner.node_id == 3:
        #     print(f"Message received by node {self.owner.node_id} {block.block_id} {block.verify_block()}")
        
        if not block.verify_block():
            
            log_message = broadcast_message.to_json()
            print(f"Node {self.owner.node_id} received an invalid final consensus block {log_message}")
            return False
        self.add_block(block)
        return True

# ============================
# BLOCKCHAIN IMPLEMENTATION
# ============================

class BasicBlockchain(BlockchainBase):
    """Basic blockchain implementation."""

    def __init__(self, block_class: Type['BlockBase'], owner: 'NodeBase'):
        super().__init__(block_class, owner)

    def create_genesis_block(self) -> 'BlockBase':
        """Creates a genesis block."""
        genesis = self.block_class(block_id=0, miner_id=1, timestamp=0)
        self.blocks[0] = genesis
        return genesis

    def add_self_proposed_block(self, block):

        logging.warning(f"Adding block {block.block_id} to the blockchain")
        if not self.is_valid_block(block):
            logging.warning(f"Block {block.block_id} is not a valid block")
            return False
        
        if block.block_id in self.blocks:
            logging.warning(f"Block {block.block_id} already exists!")
            return False # Block already exists
        
        self.blocks[block.block_id] = block

        self.owner.network.metrics["blockchain_size"][self.owner.node_id] += 1  
        self.owner.network.metrics["blockchain_ids"][self.owner.node_id].append(block.block_id)  
            
        # Connect to parent 

        block.parent = self.head
        self.head.add_child(block)
        self.head = block
        return block
        

    def add_block(self, block: 'BlockBase') -> bool:
        """Adds a block and updates the weight.
        Assumes parents are properly linked to block
        """
        
        # if self.owner.node_id == 3:
        #     print(f"Adding block {block.block_id} to the blockchain")

        logging.warning(f"Adding block {block.block_id} to the blockchain")
        if not self.is_valid_block(block):
            logging.warning(f"Block {block.block_id} is not a valid block")
            return False
        
        if block.block_id in self.blocks:
            logging.warning(f"Block {block.block_id} already exists!")
            return False # Block already exists
        
       
        
        # Add the block to the blockchain

        if not block.parent and not block.parent in self.blocks:
            print(f"Parent block {block.parent.block_id} of {block.block_id} is missing!")
            logging.warning(f"Parent block {block.parent.block_id} of {block.block_id} is missing!")
            
        # Connect to parent 

        if not block.parent.block_id:
            print(f"Parent block {block.parent.block_id} of {block.block_id} is missing!")
            # logging.warning(f"Parent block {block.parent.block_id} of {block.block_id} is missing!")
            return False
        block_parent = self.blocks[block.parent.block_id] if block.parent.block_id in self.blocks else None


        if block_parent and block.block_id not in [x.block_id for x in block_parent.children]:

            if self.owner.node_id == 3:
                print(f"parent id :::: {block_parent.block_id} children of parent node {[x.block_id for x in block_parent.children]}")
            
            self.blocks[block.block_id] = block
            self.owner.network.metrics["blockchain_size"][self.owner.node_id] += 1
            self.owner.network.metrics["blockchain_ids"][self.owner.node_id].append(block.block_id)  
            block_parent.add_child(block)
            self.head = self.owner.consensus_protocol.select_best_block(self.owner.blockchain)
            if not self.head.block_id == block.block_id:
                self.owner.network.metrics["fork_resolutions"] += 1

            # if self.owner.node_id == 3:
            #     chain = []
            #     head = self.genesis
            #     while head:
            #         chain.append(head.block_id)
            #         head = head.children[0] if head.children else None
            #     print(f"parent node {block_parent.block_id if block_parent else None}. Current chain {chain}")
            #     print(f"Added block {block.block_id}. Current chain {chain}")
            
        return True

        