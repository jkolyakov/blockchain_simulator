from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Type, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from blockchain_simulator.node import NodeBase
    from blockchain_simulator.block import BlockBase
    from blockchain_simulator.blockchain import BlockchainBase
    from blockchain_simulator.broadcast import GossipBroadcast
import logging
# ============================
# CONSENSUS PROTOCOL ABSTRACT CLASS
# ============================

class ConsensusProtocol(ABC):
    """Abstract class for defining custom consensus protocols."""
    
    def execute_consensus(self, node: 'NodeBase') -> None:
        """
        Executes a step in the consensus protocol.

        :param node: The node running the protocol.
        """
        if not node.proposed_blocks:
            return  # No blocks proposed
        
        selected_blocks = self.select_consensus_candidate(node)
        
        if isinstance(selected_blocks, list): # If the best block is a list of blocks we should try to accept all of them
            for block in selected_blocks:
                if self.confirm_consensus_candidate(node, block):
                    node.broadcast_protocol._process_pending_blocks(node, block.block_id)
                    node.broadcast_protocol.broadcast_block(block)
                # Track the number of consensus executions
                node.network.metrics["consensus_executions"] += 1
        else:
            if self.confirm_consensus_candidate(node, selected_blocks):
                node.broadcast_protocol._process_pending_blocks(node, block.block_id)
                node.broadcast_protocol.broadcast_block(block)   
            # Track the number of consensus executions
            node.network.metrics["consensus_executions"] += 1
            
    @abstractmethod
    def confirm_consensus_candidate(self, node: 'NodeBase', block: 'BlockBase') -> bool:
        """
        Runs the protocol specific logic to confirm a block as part of the main chain.

        :param node: The node running the protocol.
        :param block: The block to potentially accept.
        """
        raise NotImplementedError("Subclasses must implement the confirm_consensus_candidate() method.")
    
    @abstractmethod
    def update_weights(self, block: 'BlockBase') -> None:
        """
        Updates the weight of all ancestor blocks in the tree.

        :param block: The block to update weights from.
        """
        raise NotImplementedError("Subclasses must implement the update_weights() method.")
    
    @abstractmethod
    def propose_block(self, node: NodeBase, block: BlockBase):
        """Handles how blocks are proposed based on the consensus protocol."""
        raise NotImplementedError("Subclasses must implement the propose_block() method.")

    @abstractmethod
    def find_tip_of_main_chain(self, chain: 'BlockchainBase') -> 'BlockBase':
        """
        Selects the best block for a new mined node's parent based on the consensus protocol.

        :param node: The node running the protocol.
        :return: The best block to extend from.
        """
        raise NotImplementedError("Subclasses must implement the find_tip_of_main_chain() method.")
    
    @abstractmethod
    def select_consensus_candidate(self, node: 'NodeBase') -> 'BlockBase':
        """
        Selects a block from the proposed blocks via the consensus protocol.

        :param node: The node running the protocol.
        :return: The selected block.
        """
        raise NotImplementedError("Subclasses must implement the select_consensus_candidate() method.")
    
    def count_orphaned_blocks(self, node: 'NodeBase') -> int:
        """
        Counts the number of orphaned blocks in the blockchain.
        Needs to be implemented to track orphaned blocks for metrics

        :param node: The node running the protocol.
        :return: The number of orphaned blocks.
        """
        return max(0, len(node.blockchain.blocks) - self.main_chain_length(node)) # max to avoid negative values

    
    def main_chain_length(self, node: 'NodeBase') -> int:
        """
        Returns the length of the longest chain.

        :param node: The node running the protocol.
        :return: The length of the chain.
        """
        length = 0
        current = self.find_tip_of_main_chain(node.blockchain)
        while current:
            length += 1
            current = current.parent
        return length

    def chain_length(self, node: 'NodeBase'):
        """
        Returns the number of nodes in the blockchain.

        :param node: The node running the protocol.
        :return: The length of the chain.
        """
        return len(node.blockchain.blocks)
    
# ============================
# CONSENSUS PROTOCOL IMPLEMENTATIONS
# ============================
class GHOSTProtocol(ConsensusProtocol):
    """Implements the GHOST (Greedy Heaviest Observed Subtree) consensus protocol."""

    def find_tip_of_main_chain(self, chain: 'BlockchainBase') -> 'BlockBase':
        """
        Selects the heaviest subtree using the GHOST protocol.
        The best block is the one with the most cumulative weight.

        :param chain: The blockchain instance.
        :return: The block with the highest weight.
        """
        current = chain.genesis  # Start from genesis
        while current.children:
            current = max(current.children, key=lambda b: (b.weight, -b.block_id)) # Break ties by smallest block ID (hence the negative)
        return current

    def select_consensus_candidate(self, node: 'NodeBase') -> list['BlockBase']:
        """
        For GHOST, all blocks proposed blocks should be added to the blockchain.

        :param node: The node running the protocol.
        :return: The block with the highest weight.
        """
        return list(node.proposed_blocks)

    def propose_block(self, node: NodeBase, block: BlockBase):
        """In GHOST, all blocks are added to the blockchain immediately."""
        if node.blockchain.is_valid_block(block, node.mining_difficulty): # Ensure the block is valid
            node.proposed_blocks.add(block)
            block.nodes_seen.add(node.node_id)

    def update_weights(self, block: 'BlockBase'):
        """Updates the weight of all ancestor blocks in the tree."""
        if len(block.children) == 0:
            block.weight = 1  # Leaf blocks have weight 1
        else:
            block.weight = 1 + sum(child.weight for child in block.children)

        if block.parent is not None:
            self.update_weights(block.parent)  # Recursively update ancestors
    
    def confirm_consensus_candidate(self, node: 'NodeBase', block: 'BlockBase') -> bool:
        """
        Accepts a block into the blockchain.

        :param node: The node running the protocol.
        :param block: The block to accept.
        """
        block_clone = block.clone()  # Clone the block to avoid modifying the original
        if not node.blockchain.add_block(block_clone, node):
            logging.warning(f"Node {node.node_id} rejected block {block.block_id}")
            return False # Block was, potentially waiting for parents to be added
        node.proposed_blocks.discard(block)  # Remove from original block proposed blocks (doesn't matter if not present)
        
        # Ensure the block weight updates correctly
        self.update_weights(block_clone)
        old_head = node.blockchain.head
        node.blockchain.head = self.find_tip_of_main_chain(node.blockchain)  # Update the head
        # Check if a fork was resolved
        if node.blockchain.head != node.blockchain.genesis and old_head.block_id != node.blockchain.head.parent.block_id:
            node.network.metrics["forks"] += 1
            
        # if block is successfully added, process any pending children
        node.broadcast_protocol._process_pending_blocks(node, block.block_id)
        return True
    