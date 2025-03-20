from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Type, TYPE_CHECKING
import random
import logging

if TYPE_CHECKING:
    from blockchain_simulator.node import NodeBase
    from blockchain_simulator.block import BlockBase
    from blockchain_simulator.blockchain import BlockchainBase

# ============================
# CONSENSUS PROTOCOL ABSTRACT CLASS
# ============================

class ConsensusProtocol(ABC):
    """Abstract class for defining custom consensus protocols."""
    
    @abstractmethod
    def select_main_chain(self, chain: 'BlockchainBase') -> 'BlockBase':
        """
        Selects the best block for a mined node's parent based on the consensus protocol.

        :param node: The node running the protocol.
        :return: The best block to extend from.
        """
        pass
    
    @abstractmethod
    def select_from_proposed(self, node: 'NodeBase') -> 'BlockBase':
        """
        Selects a block from the proposed blocks via the consensus protocol.

        :param node: The node running the protocol.
        :return: The selected block.
        """
        pass
    
    def execute_consensus(self, node: 'NodeBase') -> None:
        """
        Executes a step in the consensus protocol.

        :param node: The node running the protocol.
        """
        if not node.proposed_blocks:
            return  # No blocks proposed
        
        logging.warning(f"Time {node.env.now:.2f}: Trying to select from proposed blocks", repr([block.block_id for block in node.proposed_blocks]))
        selected_blocks = self.select_from_proposed(node)


        if isinstance(selected_blocks, list): # If the best block is a list of blocks we should try to accept all of them
            for block in selected_blocks:
                # logging.warning(f"Time {node.env.now:.2f}: Node {node.node_id} trying to propose block in loop {block.block_id}")
                if block.block_id not in node.blockchain.blocks:
                    # logging.warning(f"Time {node.env.now:.2f}: block {block.block_id} not in blockchain. THIS IS GOOD")
                    self.accept_consensus_block(node, block)
                    node.network.metrics["consensus_executions"] += 1  
                    self.broadcast_consensus_block(node, block)
                else:
                    # logging.warning(f"Time {node.env.now:.2f}: block {block.block_id} is in blockchain. THIS IS BAD")
                    pass
                    
        else:
            # logging.warning(f"Time {node.env.now:.2f}: Node {node.node_id} trying to propose block else {block.block_id}")
            if block.block_id not in node.blockchain.blocks:
                # logging.warning(f"Time {node.env.now:.2f}: block {block.block_id} not in blockchain. THIS IS GOOD")
                self.accept_consensus_block(node, selected_blocks)
                node.network.metrics["consensus_executions"] += 1
                self.broadcast_consensus_block(node, selected_blocks)
            else:
                logging.warning(f"Time {node.env.now:.2f}: block {block.block_id} is in blockchain. THIS IS BAD")
                pass
                
        
    
    def accept_consensus_block(self, node: 'NodeBase', block: 'BlockBase') -> bool:
        """
        Accepts a block into the blockchain.

        :param node: The node running the protocol.
        :param block: The block to accept.
        """
        node.blockchain.add_block(block, node)
        node.proposed_blocks.discard(block)  # Remove from proposed blocks (doesn't matter if not present)
        # Ensure the block weight updates correctly
        self.update_weights(block)
        old_head = node.head
        node.head = self.select_main_chain(node.blockchain)  # Update the head
        if (node.head.parent != old_head): # If the head has changed, we have a fork
            node.network.metrics["forks"] += 1


    def requires_broadcast(self) -> bool:
        """
        Returns whether the consensus protocol requires broadcasting.
        """
        return False

    def broadcast_consensus_block(self, node: 'NodeBase', block: 'BlockBase') -> None:
        """
        Broadcasts a block to all peers.

        :param node: The node broadcasting the block.
        :param block: The block to broadcast.
        """
        if not self.requires_broadcast():
            return  # No need to broadcast
        for peer in node.peers:
            delay = node.network.get_network_delay(node, peer)
            node.env.process(self.receive_consensus_block(peer, block, delay))
            
    @abstractmethod
    def receive_consensus_block(self, node: NodeBase, block: BlockBase, delay: float, sender_id: int):
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
    def add_to_block_queue(self, node: NodeBase, block: BlockBase):
        """Handles how blocks are proposed based on the consensus protocol."""
        pass
    
    def count_orphaned_blocks(self, node: 'NodeBase') -> int:
        """
        Counts the number of orphaned blocks in the blockchain.
        Needs to be implemented to track orphaned blocks for metrics

        :param node: The node running the protocol.
        :return: The number of orphaned blocks.
        """
        return len(node.blockchain.blocks) - self.chain_length(node)

    
    def chain_length(self, node: 'NodeBase') -> int:
        """
        Returns the length of the longest chain.

        :param node: The node running the protocol.
        :return: The length of the chain.
        """
        length = 0
        current = self.select_main_chain(node.blockchain)
        while current:
            length += 1
            current = current.parent
        return length
    
# ============================
# CONSENSUS PROTOCOL IMPLEMENTATIONS
# ============================
class GHOSTProtocol(ConsensusProtocol):
    """Implements the GHOST (Greedy Heaviest Observed Subtree) consensus protocol."""

    def select_main_chain(self, chain: 'BlockchainBase') -> 'BlockBase':
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

    def select_from_proposed(self, node: 'NodeBase') -> list['BlockBase']:
        """
        For GHOST, all blocks proposed blocks should be added to the blockchain.

        :param node: The node running the protocol.
        :return: The block with the highest weight.
        """
        return list(node.proposed_blocks)
    

    def add_to_block_queue(self, node: NodeBase, block: BlockBase):
        """In GHOST, all blocks are added to the blockchain immediately."""
        if node.blockchain.is_valid_block(block):
            node.proposed_blocks.add(block)

    def requires_broadcast(self) -> bool:
        """
        GHOST requires broadcasting the chosen block since it ensures chain synchronization.

        :return: True (GHOST broadcasts selected blocks).
        """
        return True
    
    def update_weights(self, block: 'BlockBase'):
        """Updates the weight of all ancestor blocks in the tree."""
        while block:
            block.weight = 1 + sum(child.weight for child in block.children)
            block = block.parent  # Move up the chain
            
    def receive_consensus_block(self, node: NodeBase, block: BlockBase, delay: float):
        """Processes an incoming consensus-finalized block in GHOST."""

        if block.block_id in node.blockchain.blocks:
            return  # Block already part of the chain

        self.add_to_block_queue(node, block)
    
class LongestChainProtocol(ConsensusProtocol):
    """Implements the Longest Chain consensus protocol (Bitcoin-style)."""
    
    def select_main_chain(self, node: 'NodeBase') -> 'BlockBase':
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
    
    def select_main_chain(self, node: 'NodeBase') -> 'BlockBase':
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
    
    def select_main_chain(self, node: 'NodeBase') -> 'BlockBase':
        """
        Selects the block with the highest weight in the DAG.

        :param node: The node running the protocol.
        :return: The highest-weighted block in the DAG structure.
        """
        sorted_blocks = sorted(node.blockchain.blocks.values(), key=lambda b: b.weight, reverse=True)
        return sorted_blocks[0] if sorted_blocks else node.blockchain.blocks[0]