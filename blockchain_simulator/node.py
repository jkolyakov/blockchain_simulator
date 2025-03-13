import logging
import random

class Node:
    """Represents a blockchain node."""
    
    def __init__(self, env, node_id, network, consensus_protocol, blockchain):
        self.env = env
        self.node_id = node_id
        self.network = network
        self.peers = []
        self.consensus_protocol = consensus_protocol
        self.blockchain = blockchain
        self.head = blockchain.genesis
        self.received_blocks = {}

    def add_peer(self, peer):
        """Connects this node to a peer."""
        if peer not in self.peers:
            self.peers.append(peer)

    def mine_block(self):
        """Mines a new block and broadcasts it."""
        new_block_id = len(self.blockchain.blocks)
        new_block = self.blockchain.block_class(block_id=new_block_id, parents=self.head, miner_id=self.node_id, timestamp=self.env.now)

        self.blockchain.add_block(new_block, self)
        self.head = self.consensus_protocol.select_best_block(self)

        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} mined block {new_block_id}")
        self.network.metrics["total_blocks_mined"] += 1

        self.broadcast_block(new_block)