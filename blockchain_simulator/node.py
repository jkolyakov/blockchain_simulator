import logging
import random
import simpy
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Type
from blockchain_simulator.block import BlockBase
from blockchain_simulator.blockchain import BlockchainBase
from blockchain_simulator.consensus import ConsensusProtocol
from blockchain_simulator.simulator import BlockchainSimulator
# ============================
# ABSTRACT NODE CLASS
# ============================

class NodeBase(ABC):
    """Abstract base class for defining a blockchain node."""

    def __init__(self, env: simpy.Environment, node_id: int, network: "BlockchainSimulator", 
                 consensus_protocol: ConsensusProtocol, blockchain: BlockchainBase):
        self.env = env
        self.node_id = node_id
        self.network = network
        self.peers: List["NodeBase"] = []
        self.consensus_protocol = consensus_protocol
        self.blockchain = blockchain
        self.head = blockchain.genesis
        self.received_blocks: Dict[int, float] = {}  # Stores when blocks were received

    def add_peer(self, peer: "NodeBase"):
        """Connects this node to a peer."""
        if peer not in self.peers:
            self.peers.append(peer)

    @abstractmethod
    def mine_block(self) -> None:
        """Abstract method for mining a block."""
        pass

    @abstractmethod
    def broadcast_block(self, block: BlockBase):
        """Abstract method for broadcasting a block to peers."""
        pass

    @abstractmethod
    def receive_block(self, block: BlockBase, delay: float, sender_id: int):
        """Abstract method for processing an incoming block."""
        pass

# ============================
# BASIC NODE CLASS
# ============================

class BasicNode(NodeBase):
    """A basic node implementation that follows the consensus protocol and mines blocks."""

    def mine_block(self):
        """Mines a new block and broadcasts it."""
        new_block_id = len(self.blockchain.blocks)
        new_block = self.blockchain.block_class(
            block_id=new_block_id, 
            parents=self.head, 
            miner_id=self.node_id, 
            timestamp=self.env.now
        )

        self.blockchain.add_block(new_block, self)
        self.head = self.consensus_protocol.select_best_block(self)

        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} mined block {new_block_id}")
        self.network.metrics["total_blocks_mined"] += 1

        self.broadcast_block(new_block)

    def broadcast_block(self, block: BlockBase) -> None:
        """Broadcasts a block to all connected peers with a random network delay."""
        for peer in self.peers:
            delay = random.uniform(1, self.network.max_delay)
            self.env.process(peer.receive_block(block, delay, self.node_id))

    def receive_block(self, block: BlockBase, delay: float, sender_id: int):
        """Processes an incoming block after a delay."""
        yield self.env.timeout(delay)

        # Log block propagation time
        if block.block_id not in self.received_blocks:
            self.received_blocks[block.block_id] = self.env.now
            self.network.metrics["block_propagation_times"].append(self.env.now - block.timestamp)

        # Add block if it's not already in the blockchain
        if block.block_id not in self.blockchain.blocks:
            self.blockchain.add_block(block, self)
            self.head = self.consensus_protocol.select_best_block(self)
            logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} received block {block.block_id} from Node {sender_id}")
            self.broadcast_block(block)