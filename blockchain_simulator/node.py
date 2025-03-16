from __future__ import annotations
import logging
import random
import simpy
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from blockchain_simulator.block import BlockBase
    from blockchain_simulator.blockchain import BlockchainBase
    from blockchain_simulator.consensus import ConsensusProtocol
    from blockchain_simulator.simulator import BlockchainSimulator

# ============================
# ABSTRACT NODE CLASS
# ============================
class NodeBase(ABC):
    """Abstract base class for defining a blockchain node."""

    def __init__(self, env: simpy.Environment, node_id: int, network: 'BlockchainSimulator', 
                 consensus_protocol: 'ConsensusProtocol', blockchain: 'BlockchainBase'):
        self.env = env
        self.node_id = node_id
        self.network = network
        self.peers: List['NodeBase'] = []
        self.consensus_protocol = consensus_protocol
        self.blockchain = blockchain
        self.head: 'BlockBase' = blockchain.genesis
        self.proposed_blocks: set['BlockBase'] = set()
        self.is_mining = True
        self.active = True
        self.last_consensus_time = 0
        self.mining_difficulty = 4 # Default difficulty for PoW

    def add_peer(self, peer: 'NodeBase'):
        """Connects this node to a peer."""
        if peer not in self.peers:
            self.peers.append(peer)

    def remove_peer(self, peer: 'NodeBase'):
        """Disconnects this node from a peer."""
        if peer in self.peers:
            self.peers.remove(peer)
        if not self.peers:  # If no peers, deactivate the node
            self.deactivate()

    def deactivate(self):
        """Deactivates the node."""
        self.active = False

    def activate(self):
        """Activates the node."""
        self.active = True

    def consensus_step(self):
        """Executes the consensus protocol."""
        self.consensus_protocol.execute_consensus(self)
        self.last_consensus_time = self.env.now
        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} executed consensus, head: {self.head.block_id}")

    def mine_block(self):
        """Mines a new block and submits it according to the consensus protocol."""
        self.head = self.consensus_protocol.select_best_block(self.blockchain)
        if not self.head in self.blockchain.blocks:
            logging.warning(f"Time {self.env.now:.2f}: Node {self.node_id} head block not in blockchain")
        new_block = self.blockchain.create_block(self.head, self.node_id, self.env.now)
        new_block.mine(self, self.mining_difficulty)
        
        # Allows for simulation to stop mining
        if not self.is_mining:
            return 
        
        # Ensure the block meets PoW validity before adding it
        if not self.blockchain.add_block(new_block, self):
            logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} failed mining block {new_block.block_id}")
            return        
        
        # Increment the total blocks mined
        self.network.metrics["total_blocks_mined"] += 1
        self.network.metrics["blocks_by_node"][self.node_id] += 1
        
        # Handle block proposal based on the consensus protocol
        self.consensus_protocol.propose_block(self, new_block)

        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} mined block {new_block.block_id}")
        self.broadcast_block(new_block)
        yield self.env.timeout(0)  # Yield to make this a generator

    def broadcast_block(self, block: 'BlockBase'):
        """Broadcasts a block to all connected peers with a random network delay."""
        if block.block_id in self.blockchain.blocks:
            return

        for peer in self.peers:
            delay = self.network.get_network_delay(self.node_id, peer.node_id)
            self.env.process(peer.receive_block(block, delay, self.node_id))

        self.network.metrics["broadcasts"] += 1
        yield(self.env.timeout(0))  # Yield to make this a generator

    def receive_block(self, block: 'BlockBase', delay: float, sender_id: int):
        """Processes an incoming block after a delay."""
        yield self.env.timeout(delay)

        if block.block_id in self.blockchain.blocks:
            return  # Block already known, ignore it

        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} received block {block.block_id} from Node {sender_id}")
        # Handle block proposal based on the consensus protocol
        self.consensus_protocol.propose_block(self, block)
        self.network.metrics["block_propagation_times"].append(self.env.now - block.timestamp)

        # Rebroadcast the block
        yield self.env.process(self.broadcast_block(block))

    def step(self):
        """Executes a timestep in the simulation."""
        if not self.active:
            return

        if self.env.now >= self.last_consensus_time + self.network.consensus_interval:
            logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} executing consensus")
            if len(self.proposed_blocks) > 0:
                self.consensus_step()

        yield self.env.timeout(1)
        self.env.process(self.step())

    def start_mining(self):
        """Start the mining process for this node."""
        if not self.is_mining:
            self.is_mining = True
        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} started mining")
        self.env.process(self.mining_loop())

    def stop_mining(self):
        """Stop the mining process for this node."""
        self.is_mining = False
        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} stopped mining")

    def mining_loop(self):
        """Loop that continuously attempts to mine blocks while is_mining is True."""
        while self.is_mining:
            yield self.env.process(self.mine_block())
            yield self.env.timeout(random.uniform(0.1, 0.5))  # Randomized delay before next mining attempt

# ============================
# BASIC NODE CLASS
# ============================
class BasicNode(NodeBase):
    """A basic node implementation that follows the consensus protocol and mines blocks."""
    
    pass  # All behavior is defined in NodeBase; extendable for custom nodes