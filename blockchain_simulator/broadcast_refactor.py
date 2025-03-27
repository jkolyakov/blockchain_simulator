from blockchain_simulator.blueprint import BlockchainBase, BlockBase, NodeBase, ConsensusProtocolBase, BroadcastProtocolBase, BlockchainSimulatorBase
from typing import Set
import random

class GossipProtocol(BroadcastProtocolBase):
    def __init__(self):
        self.seen_requests: Set[tuple[int, int]] = set()
    
    def broadcast_block(self, node: NodeBase, block: BlockBase):
        targets = []
        for peer in node.get_peers():
            if (block.block_id, peer.node_id) in node.recent_senders: # TODO: Always being hit and targets is always empty
                continue
            is_dropped = random.randint(1, 100) <= node.network.get_drop_rate()
            targets.append((peer.node_id, is_dropped, peer.blockchain.contains_block(block.block_id)))
            if not is_dropped:
                delay = node.network.network_topology.get_delay_between_nodes(node, peer)
                node.get_env().process(self._deliver_block_with_delay(peer, block, delay, node))
            else:
                # node.network.metrics["dropped_blocks"] += 1
                pass
        
        #  One log for all peers
        node.network.animator.log_event(
            f"Node {node.get_node_id()} broadcasting block {block} to {targets}", 
            timestamp=node.env.now
        )
    
    def receive_block(self, recipient: NodeBase, block: BlockBase, sender: NodeBase):
        recipient.recent_senders.add((block.get_block_id(), sender.get_node_id()))
        if recipient.blockchain.contains_block(block.get_block_id()):
            recipient.network.animator.log_event(
                f"Node {recipient.get_node_id()} received duplicate block {block.get_block_id()}",
                timestamp=recipient.get_env().now)
            return
        
        if recipient.blockchain.is_parent_missing(block):
            self._request_missing_block(recipient, block.get_parent_id(), recipient.get_node_id())
            return
        
        recipient.get_consensus_protocol().propose_block(recipient, block)
    
    def _deliver_block_with_delay(self, recipient: NodeBase, block: BlockBase, delay: float, sender: NodeBase):
        yield recipient.get_env().timeout(delay)
        recipient.broadcast_protocol.receive_block(recipient, block, sender)
    
    def _propagate_block_request(self, node: NodeBase, block_id: int, ttl: int, delay: float, request_origin: int):
        if self._request_already_seen(block_id, request_origin):
            return
        node.network.animator.log_event(f"Node {node.get_node_id()} requested parent block {block_id}, from: {node.get_peers()} with ttl: {ttl}", timestamp=node.env.now)
        for peer in node.get_peers():
            if peer.blockchain.contains_block(block_id):
                block = peer.blockchain.get_block(block_id).clone()
                delay = node.network.network_topology.get_delay_between_nodes(node, peer)
                node.network.animator.log_event(
                f"Node {peer.get_node_id()} sending requested parent block {block} to {[(node.get_node_id(), False, node.blockchain.contains_block(block.block_id))]}", timestamp=node.env.now) 
                node.get_env().process(self._deliver_block_with_delay(node, block, delay, peer))
            else:
                node.network.animator.log_event(f"Node {peer.get_node_id()} does not have block {block_id}, sending request to its peers: {peer.get_peers()} with ttl: {ttl}", timestamp=node.env.now)
                peer.get_env().process(self._propagate_block_request(peer, block_id, ttl - 1, delay, request_origin))
        yield node.get_env().timeout(0)
    
    def _request_missing_block(self, requester: NodeBase, block_id: int, request_origin: int, ttl: int = 3):
        if ttl <= 0 or self._request_already_seen(block_id, request_origin):
            return
        self._propagate_block_request(requester, block_id, ttl, 0, requester.node_id)
        
    def _request_already_seen(self, block_id: int, request_origin: int) -> bool:
        key = (request_origin, block_id)
        if key in self.seen_requests:
            return True
        self.seen_requests.add(key)
        return False