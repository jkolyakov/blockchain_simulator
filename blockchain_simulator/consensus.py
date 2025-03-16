from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Type, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from blockchain_simulator.node import NodeBase
    from blockchain_simulator.block import BlockBase,GhostBlock
    from blockchain_simulator.blockchain import BlockchainBase

# ============================
# CONSENSUS PROTOCOL ABSTRACT CLASS
# ============================

class ConsensusProtocol(ABC):
    
    """Abstract class for defining custom consensus protocols."""
    
    @abstractmethod
    def select_best_block(self, chain: 'BlockchainBase') -> 'BlockBase':
        """
        Selects the best block for a mined node's parent based on the consensus protocol.

        :param node: The node running the protocol.
        :return: The best block to extend from.
        """
        pass
    
    @abstractmethod
    def select_proposed_block(self, node: 'NodeBase') -> 'BlockBase':
        """
        Selects a block from its list of blocks to serve as the proposed block for the consensus protocol.

        :param node: The node running the protocol.
        :return: The selected block.
        """
        pass
    
    @abstractmethod
    def execute_consensus(self, node: 'NodeBase') -> 'BlockBase':
        """
        Executes a step in the consensus protocol.

        :param node: The node running the protocol.
        :return: return the block that is the output of consensus protocol
        """
        
    
    def accept_consensus_block(self, node: 'NodeBase', block: 'BlockBase') -> None:
        """
        Accepts a block into the blockchain.

        :param node: The node running the protocol.
        :param block: The block to accept.
        :param is_proposer: indicates if the node was the proposer of the block or not
        """
        is_proposer = False

        if block.miner_id == node.node_id:
            is_proposer = True

        node.blockchain.add_block(block, node, is_proposer)
        node.proposed_blocks.clear()    #
    
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
    
    # @abstractmethod
    # def update_weights(self, block: 'BlockBase') -> None: 
    #     """
    #     SID_NOTE: This is supposed to be a property of block.py and not the consensus
    #     Updates the weight of all ancestor blocks in the tree.

    #     :param block: The block to update weights from.
    #     """
    #     pass
    
    @abstractmethod
    def propose_block(self, node: NodeBase, block: BlockBase):
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
        current = self.select_best_block(node.blockchain)
        while current:
            length += 1
            current = current.parent
        return length
    
# ============================
# CONSENSUS PROTOCOL IMPLEMENTATIONS
# ============================
class GHOSTProtocol(ConsensusProtocol):
    """Implements the GHOST (Greedy Heaviest Observed Subtree) consensus protocol."""

    def select_best_block(self, blockchain: 'BlockchainBase') -> 'GhostBlock':
        """
        Selects the heaviest subtree using the GHOST protocol.
        The best block is the one with the most cumulative weight.

        :param chain: The blockchain instance.
        :return: The block with the highest weight.
        """
        current = blockchain.genesis  # Start from genesis
        while current.children:
            current = max(current.children, key=lambda b: (b.tree_weight, -b.block_id)) # Break ties by smallest block ID (hence the negative)
        return current

    def select_proposed_block(self, node: 'NodeBase') -> list['BlockBase']:
        """
        For GHOST, all blocks proposed blocks should be added to the blockchain.

        :param node: The node running the protocol.
        :return: The block with the highest weight.
        """
        return node.get_proposed_block(self)

    def propose_block(self, node: NodeBase, block: BlockBase):
        """In GHOST, all blocks are added to the blockchain immediately."""
        if node.blockchain.is_valid_block(block): # Ensure the block is valid
            node.proposed_blocks.add(block)

    def requires_broadcast(self) -> bool:
        """
        GHOST requires broadcasting the chosen block since it ensures chain synchronization.

        :return: True (GHOST broadcasts selected blocks).
        """
        return True
    
            
    def receive_consensus_block(self, node: NodeBase, block: BlockBase, delay: float):
        """Processes an incoming consensus-finalized block in GHOST."""
        yield node.env.timeout(delay)

        if block.block_id in node.blockchain.blocks:
            return  # Block already part of the chain

        self.propose_block(node, block)

        node.network.metrics["fork_resolutions"] += 1
    
class LongestChainProtocol(ConsensusProtocol):
    """Implements the Longest Chain consensus protocol (Bitcoin-style)."""
    
    def select_best_block(self, node: 'NodeBase') -> 'BlockBase':
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
    
    def select_best_block(self, node: 'NodeBase') -> 'BlockBase':
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
    
    def select_best_block(self, node: 'NodeBase') -> 'BlockBase':
        """
        Selects the block with the highest weight in the DAG.

        :param node: The node running the protocol.
        :return: The highest-weighted block in the DAG structure.
        """
        sorted_blocks = sorted(node.blockchain.blocks.values(), key=lambda b: b.weight, reverse=True)
        return sorted_blocks[0] if sorted_blocks else node.blockchain.blocks[0]