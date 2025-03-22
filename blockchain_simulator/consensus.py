from __future__ import annotations
from abc import ABC, abstractmethod
import logging
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
    
    
    def get_candidate_block(self, node: 'NodeBase') -> 'BlockBase':
        """
        Selects a block from its list of blocks that will act as the candidate block of node in the consensus protocol.

        :param node: The node running the protocol.
        :return: The selected block.
        """
        return node.get_from_blockqueue()

    
    @abstractmethod
    def execute_consensus(self) -> 'BlockBase':
        """
        Executes the consensus protocol.
        :return: return the block that is the output of consensus protocol
        """
        pass
    #TODO: Include the code to get candidate block
    
    # def accept_consensus_block(self, node: 'NodeBase', block: 'BlockBase') -> None:
    #     """
    #     Accepts a block into the blockchain.

    #     :param node: The node running the protocol.
    #     :param block: The block to accept.
    #     :param is_proposer: indicates if the node was the proposer of the block or not
    #     """
        
    #     node.blockchain.add_block(block)
    #     node.remove_from_blockqueue(block.block_id)
    
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
    def receive_consensus_block(self, node: NodeBase, block: BlockBase, delay: float):
        """Processes an incoming consensus-finalized block."""
        pass
    
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

        # node.blockchain.add_block(block,False)

        # node.network.metrics["fork_resolutions"] += 1

    def execute_consensus(self, node: 'NodeBase') -> 'BlockBase':
        candidate_block = self.get_candidate_block(node)
        # logging.info(f"Node {node.node_id} selected block {candidate_block.block_id} as candidate block")
        return candidate_block
        
    
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