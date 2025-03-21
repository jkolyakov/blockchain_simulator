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
                self.confirm_consensus_candidate(node, block)
                # Track the number of consensus executions
                node.network.metrics["consensus_executions"] += 1
                node.broadcast_protocol.broadcast_block(block)
        else:
            self.confirm_consensus_candidate(node, selected_blocks)
            # Track the number of consensus executions
            node.network.metrics["consensus_executions"] += 1
            node.broadcast_protocol.broadcast_block(block)
            
    @abstractmethod
    def confirm_consensus_candidate(self, node: 'NodeBase', block: 'BlockBase') -> bool:
        """
        Accepts a block into the blockchain.

        :param node: The node running the protocol.
        :param block: The block to accept.
        """
        pass
            
    @abstractmethod
    def receive_consensus_block(self, node: NodeBase, block: BlockBase):
        """Processes an incoming consensus-finalized block."""
        pass
    
    @abstractmethod
    def update_weights(self, block: 'BlockBase') -> None:
        """
        Updates the weight of all ancestor blocks in the tree.

        :param block: The block to update weights from.
        """
        pass
    
    @abstractmethod
    def propose_block(self, node: NodeBase, block: BlockBase):
        """Handles how blocks are proposed based on the consensus protocol."""
        pass

    @abstractmethod
    def find_tip_of_main_chain(self, chain: 'BlockchainBase') -> 'BlockBase':
        """
        Selects the best block for a mined node's parent based on the consensus protocol.

        :param node: The node running the protocol.
        :return: The best block to extend from.
        """
        pass
    
    @abstractmethod
    def select_consensus_candidate(self, node: 'NodeBase') -> 'BlockBase':
        """
        Selects a block from the proposed blocks via the consensus protocol.

        :param node: The node running the protocol.
        :return: The selected block.
        """
        pass
    
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
        Returns the number of nodes in the chain.

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
        while block:
            block.weight = 1 + sum(child.weight for child in block.children)
            block = block.parent  # Move up the chain
            
    def receive_consensus_block(self, node: 'NodeBase', block: 'BlockBase'):
        """Processes an incoming consensus-finalized block in GHOST."""
        if node.blockchain.contains_block(block.block_id):
            return  # Block already part of the chain
        
        # node.blockchain.add_block(block, node)
        self.propose_block(node, block)  # Add to proposed blocks
    
    def confirm_consensus_candidate(self, node: 'NodeBase', block: 'BlockBase') -> bool:
        """
        Accepts a block into the blockchain.

        :param node: The node running the protocol.
        :param block: The block to accept.
        """
        node.blockchain.add_block(block, node)
        node.proposed_blocks.discard(block)  # Remove from proposed blocks (doesn't matter if not present)
        
        # Ensure the block weight updates correctly
        self.update_weights(block)
        old_head = node.blockchain.head
        node.blockchain.head = self.find_tip_of_main_chain(node.blockchain)  # Update the head
        # Check if a fork was resolved
        if node.blockchain.head != node.blockchain.genesis and old_head.block_id != node.blockchain.head.parent.block_id:
            node.network.metrics["forks"] += 1
    
class LongestChainProtocol(ConsensusProtocol):
    """Implements the Longest Chain consensus protocol (Bitcoin-style)."""
    
    def find_tip_of_main_chain(self, node: 'NodeBase') -> 'BlockBase':
        """
        Selects the longest chain's tip.

        :param node: The node running the protocol.
        :return: The block at the tip of the longest chain.
        """
        current: 'BlockBase' = node.blockchain.blocks[0]
        while current.children:
            current = max(current.children, key=lambda b: len(b.children))
        return current

class PoSProtocol(ConsensusProtocol):
    """Implements Proof-of-Stake (PoS) consensus."""
    
    def find_tip_of_main_chain(self, node: 'NodeBase') -> 'BlockBase':
        """
        Selects the block with the highest stake contribution.

        :param node: The node running the protocol.
        :return: The block with the highest stake-weighted contribution.
        """
        current: 'BlockBase' = node.blockchain.blocks[0]
        while current.children:
            current = max(current.children, key=lambda b: node.network.stakes.get(b.miner_id, 1))
        return current

class DAGProtocol(ConsensusProtocol):
    """Implements GHOSTDAG for DAG-based blockchains."""
    
    def find_tip_of_main_chain(self, node: 'NodeBase') -> 'BlockBase':
        """
        Selects the block with the highest weight in the DAG.

        :param node: The node running the protocol.
        :return: The highest-weighted block in the DAG structure.
        """
        sorted_blocks = sorted(node.blockchain.blocks.values(), key=lambda b: b.weight, reverse=True)
        return sorted_blocks[0] if sorted_blocks else node.blockchain.blocks[0]