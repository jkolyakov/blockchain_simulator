from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Type, Set, TYPE_CHECKING
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
    
    @abstractmethod
    def receive_block(self, recipient: 'NodeBase', block: 'BlockBase'):
        """Receives a block from a peer."""
        pass
    
    @abstractmethod
    def send_block(self, peer: 'NodeBase', block: 'BlockBase', delay: float):
        """Sends a block to a peer with a given delay."""
        pass
    
    @abstractmethod
    def _deliver_block_with_delay(self, recipient: 'NodeBase', block: 'BlockBase', delay: float):
        """Delivers a block to a peer with a given delay."""
        pass
    
    @abstractmethod
    def _propagate_block_request(self, node: 'NodeBase', block_id: int, ttl: int, delay: float, request_origin: int):
        """Gossip-style recursive propagation of block fetch requests."""
        pass
    
    @abstractmethod
    def _request_missing_block(self, requester: 'NodeBase', block_id: int, ttl: int = 3):
        """Attempts to retrieve a missing block from peers, with TTL-limited recursion. Does this recursively for parents as well."""
        pass
    
    @abstractmethod
    def _process_pending_blocks(self, node: 'NodeBase', parent_id: int):
        """Processes any pending blocks that were waiting on the given block."""
        pass
    
    @abstractmethod
    def _propagate_block_request(self, node: 'NodeBase', block_id: int, ttl: int, delay: float, request_origin: int):
        """Gossip-style recursive propagation of block fetch requests."""
        pass
    
    @abstractmethod
    def is_parent_missing(self, block: 'BlockBase') -> bool:
        """Checks if the parent block is missing from the blockchain. If it is, the block is added to the pending queue on the node"""
        pass

# ============================
# BROADCAST PROTOCOL IMPLEMENTATION
# ============================
class GossipProtocol(BroadcastProtocol):
    """Implements a gossip protocol for broadcasting messages."""
    def __init__(self, node: 'NodeBase'):
        super().__init__(node)
        self.seen_requests: Set[tuple[int, int]] = set()  # Track block requests to prevent cycles, (request_origin, block_id)

        
    def broadcast_block(self, block: 'BlockBase'):
        """Broadcasts a block to all peers using gossip with random drops"""
        for peer in self.node.peers:
            # Drop the block with a certain probability
            if random.randint(1, 100) <= self.node.network.drop_rate:
                self.node.network.metrics["dropped_blocks"] += 1
                continue
            
            delay = self.node.network.get_network_delay(self.node, peer)
            logging.warning(f"Node {self.node.node_id} broadcasting block {block.block_id} to {peer.node_id} from {self.node.node_id} with delay {delay}")
            self.node.env.process(self.send_block(peer, block, delay))
    
    def send_block(self, peer:'NodeBase', block: 'BlockBase', delay):
        """Sends a block to a peer with a given delay."""
        yield self.node.env.timeout(delay)
        logging.warning(f"Node {self.node.node_id} sending block {block.block_id} to {peer.node_id}")
        self.receive_block(peer, block)
    
    def receive_block(self, recipient: 'NodeBase', block: 'BlockBase'):
        """Receives a block from a peer."""
        if recipient.blockchain.contains_block(block.block_id):
            return
        
        # If parent is missing, add block to pending queue and request it before processing
        # print the block id and a list of the recipient's blockchain block_ids
        if self.is_parent_missing(recipient, block):
            self._request_missing_block(recipient, block.parent.block_id, request_origin=recipient.node_id, ttl=3)
            return
        
        # Propose the block to the node
        recipient.consensus_protocol.propose_block(recipient, block)

        # If added successfully, process any pending children
        self._process_pending_blocks(recipient, block.block_id)
    
    def _process_pending_blocks(self, node: 'NodeBase', parent_id: int):
        """Processes any pending blocks that were waiting on the given block."""
        if parent_id in node.pending_blocks:
            pending_list = node.pending_blocks.pop(parent_id)
            logging.warning(f"Node {node.node_id} processing {len(pending_list)} pending blocks waiting for {parent_id}")
            for pending in pending_list:
                node.consensus_protocol.propose_block(node, pending)
    
    def _request_missing_block(self, requester: 'NodeBase', block_id: int, ttl: int = 3, request_origin: int = None):
        """Attempts to retrieve a missing block from peers, with TTL-limited recursion. Does this recursively for parents as well."""
        logging.warning(f"Node {requester.node_id} checking peers for block {block_id}")
        
        if request_origin is None:
            request_origin = requester.node_id

        key = (request_origin, block_id)
        # Prevent cycles. Requester has already requested this block
        if key in self.seen_requests:
            return
        self.seen_requests.add(key)
        
        if ttl <= 0:
            logging.warning(f"Node {requester.node_id} TTL expired for block {block_id}")
            return
        
        for peer in requester.peers:
            if peer.blockchain.contains_block(block_id):
                block = peer.blockchain.get_block(block_id)
                delay = self.node.network.get_network_delay(peer, requester)
                requester.env.process(self._deliver_block_with_delay(requester, block, delay))
                logging.warning(f"Node {requester.node_id} found block {block_id} from {peer.node_id}")
                return # Block found, no need to request again
        
        # Propogate the request to other peers
        for peer in requester.peers:
            delay = self.node.network.get_network_delay(requester, peer)
            requester.env.process(self._propagate_block_request(peer, block_id, ttl - 1, delay, request_origin))
    
    def _deliver_block_with_delay(self, recipient: 'NodeBase', block: 'BlockBase', delay: int):
        """Delivers a block to a peer with a given delay."""
        yield self.node.env.timeout(delay)
        logging.warning(f"Node {recipient.node_id} received block {block.block_id} with parent {block.parent.block_id}")
        self.receive_block(recipient, block)
        
    
    def _propagate_block_request(self, node: 'NodeBase', block_id: int, ttl: int, delay: float, request_origin: int):
        """Gossip-style recursive propagation of block fetch requests."""
        yield self.node.env.timeout(delay)
        self._request_missing_block(node, block_id, ttl, request_origin=request_origin)
    
    def is_parent_missing(self, node: 'NodeBase', block: 'BlockBase') -> bool:
        """Checks if the parent is missing. Adds block to pending if true."""
        if not node.blockchain.contains_block(block.parent.block_id):
            node.pending_blocks.setdefault(block.parent.block_id, []).append(block)
            logging.warning(f"Block {block.block_id} is waiting for missing parent {block.parent.block_id}. Queued in pending_blocks.")
            return True
        return False