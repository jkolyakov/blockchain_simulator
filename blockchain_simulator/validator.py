"""
Validation module for blockchain simulations.
Contains classes for validating the correctness of blockchain simulations.
"""

from typing import Dict, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from blockchain_simulator.simulator import BlockchainSimulator

class BlockchainValidator:
    """Class for validating blockchain simulations."""
    
    def __init__(self, simulator: 'BlockchainSimulator'):
        """
        Initialize the validator with a simulator instance.
        
        :param simulator: The blockchain simulator to validate.
        """
        self.simulator = simulator
    
    def validate_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Run all validation checks and return the results.
        
        :return: Dictionary of validation results.
        """
        results = {
            "fork_resolution": self.validate_fork_resolution(),
            "chain_consistency": self.validate_chain_consistency(),
            "block_propagation": self.validate_block_propagation(),
            "consensus_correctness": self.validate_consensus_correctness(),
            "network_health": self.validate_network_health()
        }
        
        return results
    
    def validate_fork_resolution(self) -> Dict[str, Any]:
        """
        Validates that forks are resolved correctly according to the consensus protocol.
        
        :return: Validation results.
        """
        # Count unresolved forks
        unresolved_forks = self._count_forks()
        
        # Check convergence
        convergence = self._measure_convergence()[1]
        
        return {
            "unresolved_forks": unresolved_forks,
            "convergence": convergence,
            "passed": convergence > 0.8  # At least 80% agreement
        }
    
    def validate_chain_consistency(self) -> Dict[str, Any]:
        """
        Validates that all nodes have consistent chains (no contradictions).
        
        :return: Validation results.
        """
        # Check if the same block has different parents in different nodes
        inconsistencies = []
        
        # Map of block_id -> parent_id across all nodes
        block_parents = {}
        
        for node in self.simulator.nodes:
            for block_id, block in node.blockchain.blocks.items():
                if block.parent:
                    parent_id = block.parent.block_id
                    if block_id in block_parents and block_parents[block_id] != parent_id:
                        inconsistencies.append(f"Block {block_id} has different parents: {block_parents[block_id]} vs {parent_id}")
                    else:
                        block_parents[block_id] = parent_id
        
        return {
            "inconsistencies": inconsistencies,
            "passed": len(inconsistencies) == 0
        }
    
    def validate_block_propagation(self) -> Dict[str, Any]:
        """
        Validates that blocks are properly propagated across the network.
        
        :return: Validation results.
        """
        # Check if all nodes have received similar numbers of blocks
        active_nodes = [node for node in self.simulator.nodes if node.active]
        if not active_nodes:
            return {
                "max_blocks": 0,
                "min_blocks": 0,
                "avg_blocks": 0,
                "std_dev": 0,
                "passed": False,
                "error": "No active nodes in the network"
            }
            
        block_counts = [len(node.blockchain.blocks) for node in active_nodes]
        max_blocks = max(block_counts)
        min_blocks = min(block_counts)
        
        # Calculate block distribution stats
        avg_blocks = sum(block_counts) / len(block_counts)
        block_std_dev = (sum((c - avg_blocks) ** 2 for c in block_counts) / len(block_counts)) ** 0.5
        
        # We consider propagation successful if the standard deviation is less than 20% of the average
        # but only if the average is at least 5 blocks (to avoid initial state issues)
        passed = block_std_dev / avg_blocks < 0.2 if avg_blocks >= 5 else False
        
        return {
            "max_blocks": max_blocks,
            "min_blocks": min_blocks,
            "avg_blocks": avg_blocks,
            "std_dev": block_std_dev,
            "passed": passed
        }
    
    def validate_consensus_correctness(self) -> Dict[str, Any]:
        """
        Validates that the consensus protocol is working correctly.
        
        :return: Validation results.
        """
        # This is a simplified check that ensures nodes agree on the best block
        active_nodes = [node for node in self.simulator.nodes if node.active]
        if not active_nodes:
            return {
                "total_different_heads": 0,
                "majority_head": None,
                "majority_percentage": 0,
                "passed": False,
                "error": "No active nodes in the network"
            }
        
        heads = {}
        for node in active_nodes:
            head_id = node.blockchain.head.block_id
            if head_id in heads:
                heads[head_id] += 1
            else:
                heads[head_id] = 1
        
        # Calculate metrics
        total_heads = len(heads)
        majority_head, majority_count = max(heads.items(), key=lambda x: x[1]) if heads else (None, 0)
        majority_percentage = majority_count / len(active_nodes)
        
        return {
            "total_different_heads": total_heads,
            "majority_head": majority_head,
            "majority_percentage": majority_percentage,
            "passed": majority_percentage > 0.7  # At least 70% agreement
        }
    
    def validate_network_health(self) -> Dict[str, Any]:
        """
        Validates the general health of the network.
        
        :return: Validation results.
        """
        # Check for disconnected nodes
        isolated_nodes = 0
        for node in self.simulator.nodes:
            if node.active and len(node.peers) == 0:
                isolated_nodes += 1
        
        # Check block mining distribution
        mining_counts = list(self.simulator.metrics["blocks_by_node"].values())
        max_mined = max(mining_counts) if mining_counts else 0
        min_mined = min(mining_counts) if mining_counts else 0
        
        # Check for major imbalances in mining power
        mining_imbalance = max_mined > 3 * min_mined if min_mined > 0 else False
        
        return {
            "isolated_nodes": isolated_nodes,
            "max_blocks_mined": max_mined,
            "min_blocks_mined": min_mined,
            "mining_imbalance": mining_imbalance,
            "passed": isolated_nodes == 0 and not mining_imbalance
        }
    
    def _count_forks(self) -> int:
        """Count the number of fork points in the blockchain."""
        fork_count = 0
        
        # Check each block to see if it has multiple children
        for node in self.simulator.nodes:
            for block_id, block in node.blockchain.blocks.items():
                if len(block.children) > 1:
                    fork_count += 1
        
        return fork_count
    
    def _measure_convergence(self) -> float:
        """Measure the percentage of nodes that agree on the same chain."""
        active_nodes = [node for node in self.simulator.nodes if node.active]
        if not active_nodes:
            return 0.0
            
        heads = {}
        
        # Count occurrences of each head block
        for node in active_nodes:
            head_id = node.blockchain.head.block_id
            if head_id in heads:
                heads[head_id] += 1
            else:
                heads[head_id] = 1
        
        # Find the most common head
        if not heads:
            return 0.0
            
        most_common_head, count = max(heads.items(), key=lambda x: x[1])
        
        # Calculate the percentage of nodes with this head
        return most_common_head, count / len(active_nodes)