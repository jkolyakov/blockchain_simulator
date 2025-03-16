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

        best_block = self.select_from_proposed(node)

        # If the best block is already in the chain, do nothing
        if best_block.block_id in node.blockchain.blocks:
            return

        # Accept the block into the blockchain
        self.accept_consensus_block(node, best_block, True)

        # If the protocol requires broadcasting, send it to peers
        if self.requires_broadcast():
            self.broadcast_consensus_block(node, best_block)
    
    def accept_consensus_block(self, node: 'NodeBase', block: 'BlockBase', is_proposer: bool) -> None:
        """
        Accepts a block into the blockchain.

        :param node: The node running the protocol.
        :param block: The block to accept.
        :param is_proposer: indicates if the node was the proposer of the block or not
        """
        node.blockchain.add_received_block(block,is_proposer)
        for node_block in node.proposed_block_queue:
            if node_block.block_id == block.block_id:
                node.proposed_block_queue.remove(node_block)            #delete the block from proposed block list if it is the same as the output of consensus since it has already been added to the main chain

    
    def requires_broadcast(self) -> bool:
        """
        Returns whether the consensus protocol requires broadcasting.

        :return: True if the protocol requires broadcasting.
        """
        return False

    def broadcast_consensus_block(self, node: 'NodeBase', block: 'BlockBase') -> None:
        """
        Broadcasts a block to all peers.

        :param node: The node broadcasting the block.
        :param block: The block to broadcast.
        """
        for peer in node.peers:
            delay = random.uniform(1, node.network.max_delay) # TODO: Fix via network get_delay function
            node.env.process(peer.receive_consensus_block(block, delay, node.node_id))

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
            current = max(current.children, key=lambda b: b.weight)
        return current

    def select_from_proposed(self, node: 'NodeBase') -> 'BlockBase':
        """
        Selects the best block from the proposed blocks based on the heaviest subtree rule.

        :param node: The node running the protocol.
        :return: The block with the highest weight.
        """
        # if not node.proposed_blocks:
            # return node.head  # If no proposed blocks, continue extending the current chain

        # return max(node.proposed_blocks, key=lambda b: b.weight, default=node.head)

        return node.get_proposed_block(self)

    def requires_broadcast(self) -> bool:
        """
        GHOST requires broadcasting the chosen block since it ensures chain synchronization.

        :return: True (GHOST broadcasts selected blocks).
        """
        return True
    
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