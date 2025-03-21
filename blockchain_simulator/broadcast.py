from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Type, TYPE_CHECKING
import random

if TYPE_CHECKING:
    from blockchain_simulator.node import NodeBase
    from blockchain_simulator.block import BlockBase
    from blockchain_simulator.blockchain import BlockchainBase
import logging

class BroadcastProtocol(ABC):
    def __init__(self, node: 'NodeBase'):
        self.node = node # The node running the protocol
        
    @abstractmethod
    def broadcast_block(self, block: 'BlockBase'):
        """Broadcasts a block to all peers."""
        pass

class GossipProtocol(BroadcastProtocol):
    """Implements a gossip protocol for broadcasting messages."""
    def __init__(self, node: 'NodeBase'):
        super().__init__(node)
        
    def broadcast_block(self, block: 'BlockBase'):
        """Broadcasts a block to all peers using gossip with random drops"""
        for peer in self.node.peers:
            if peer.blockchain.contains_block(block.block_id):
                continue
            if random.randint(1, 100) <= self.node.network.drop_rate:
                self.node.network.metrics["dropped_blocks"] += 1
                continue
            
            delay = self.node.network.get_network_delay(self.node, peer)
            logging.info(f"Node {self.node.node_id} broadcasting block {block.block_id} to {peer.node_id} from {self.node.node_id} with delay {delay}")
            self.node.env.process(self.send_block(peer, block, delay))
    
    def send_block(self, peer:'NodeBase', block: 'BlockBase', delay):
        yield self.node.env.timeout(delay)
        logging.info(f"Node {self.node.node_id} sending block {block.block_id} to {peer.node_id}")
        peer.consensus_protocol.receive_consensus_block(self.node, block)