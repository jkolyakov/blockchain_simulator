from blockchain_simulator.blueprint import BlockchainBase, BlockBase, NodeBase, ConsensusProtocolBase, BroadcastProtocolBase, BlockchainSimulatorBase
from typing import Set, Dict
import random

class GossipProtocol(BroadcastProtocolBase):
    def __init__(self):
        self.seen_requests: Set[tuple[int, int]] = set() # (block_id, request_origin)
        
    def broadcast_block(self, node: NodeBase, block: BlockBase):
        targets = []
        for peer in node.get_peers():
            if (block.block_id, peer.node_id) in node.recent_senders:
                continue
            is_dropped = random.randint(1, 100) <= node.network.get_drop_rate()
            targets.append((peer.node_id, is_dropped, peer.blockchain.contains_block(block.block_id)))
            if not is_dropped:
                node.get_env().process(node.network.send_block_to_node(node, peer, block)) 
            else:
                # node.network.metrics["dropped_blocks"] += 1
                pass
        
        #  One log for all peers
        node.network.animator.log_event(f"Node {node.get_node_id()} broadcasting block {block} to {targets}", timestamp=node.env.now)
    
    def process_block(self, recipient: NodeBase, sender: NodeBase, block: BlockBase):
        """Process a received block or forward if part of a request response."""
        recipient.recent_senders.add((block.get_block_id(), sender.get_node_id()))
        
        # If this block is a response to a prior request, forward it
        origin = recipient.network.get_request_origin(block.get_block_id(), recipient)
        if origin:
            recipient.get_env().process(recipient.network.send_block_to_node(recipient, origin, block))
        
        # If the block is already in the chain, log for animation
        if recipient.blockchain.contains_block(block.get_block_id()):
            recipient.network.animator.log_event(f"Node {recipient.get_node_id()} received duplicate block {block.get_block_id()}",timestamp=recipient.get_env().now)
            return
        
        # If the block is new, process it
        if recipient.blockchain.is_parent_missing(block):
            # print("\033[91m PARENT MISSING. REQUESTING...\033[0m")
            recipient.get_env().process(self._request_missing_block(recipient, block.get_parent_id(), 3, recipient.get_node_id()))
            return
        
        # Propose the block to the consensus protocol
        recipient.get_consensus_protocol().propose_block(recipient, block)
        
    def _request_missing_block(self, requester: NodeBase, block_id: int, ttl: int, origin_id: int):
        if ttl <= 0 or self._request_already_seen(block_id, requester.get_node_id()):
            return

        # Log the request
        requester.network.animator.log_event(f"Node {requester.get_node_id()} requesting block {block_id} with TTL={ttl}",timestamp=requester.env.now)

        for peer in requester.get_peers():
            requester.network.register_request_origin(block_id, peer, requester)

            if peer.blockchain.contains_block(block_id):
                block = peer.blockchain.get_block(block_id).clone()
                requester.get_env().process(requester.network.send_block_to_node(peer, requester, block))
            else:
                peer.get_env().process(self._request_missing_block(peer, block_id, ttl - 1, origin_id))
        yield requester.get_env().timeout(0)
        
    def _request_already_seen(self, block_id: int, node_id: int) -> bool:
        key = (block_id, node_id)
        if key in self.seen_requests:
            return True
        self.seen_requests.add(key)
        return False