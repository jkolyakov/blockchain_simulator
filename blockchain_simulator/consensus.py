from abc import ABC, abstractmethod

class ConsensusProtocol(ABC):
    """Abstract class for defining custom consensus protocols."""
    
    @abstractmethod
    def select_best_block(self, node):
        """Select the best block for a node."""
        pass


class GHOSTProtocol(ConsensusProtocol):
    """Implements the GHOST consensus protocol."""
    
    def select_best_block(self, node):
        """Selects the heaviest subtree using GHOST."""
        current = node.blockchain.blocks[0]  # Start at genesis
        while current.children:
            current = max(current.children, key=lambda b: b.weight)
        return current

class LongestChainProtocol(ConsensusProtocol):
    """Implements the Longest Chain consensus protocol (Bitcoin-style)."""
    
    def select_best_block(self, node):
        """Selects the longest chain's tip as the best block."""
        current = node.blockchain.blocks[0]
        while current.children:
            current = max(current.children, key=lambda b: len(b.children))
        return current

class PoSProtocol(ConsensusProtocol):
    """Implements Proof-of-Stake (PoS) consensus."""
    
    def select_best_block(self, node):
        """Selects the block with the highest stake contribution."""
        current = node.blockchain.blocks[0]
        while current.children:
            current = max(current.children, key=lambda b: node.network.stakes.get(b.miner_id, 1))
        return current

class DAGProtocol(ConsensusProtocol):
    """Implements GHOSTDAG for DAG-based blockchains."""
    
    def select_best_block(self, node):
        """Selects the block with the highest weight in the DAG."""
        sorted_blocks = sorted(node.blockchain.blocks.values(), key=lambda b: b.weight, reverse=True)
        return sorted_blocks[0] if sorted_blocks else node.blockchain.blocks[0]