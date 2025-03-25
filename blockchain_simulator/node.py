from __future__ import annotations
import logging
import random
import simpy
from abc import ABC, abstractmethod
from typing import List, Type, Dict, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from blockchain_simulator.block import BlockBase
    from blockchain_simulator.blockchain import BlockchainBase
    from blockchain_simulator.consensus import ConsensusProtocol
    from blockchain_simulator.simulator import BlockchainSimulator
    from blockchain_simulator.broadcast import BroadcastProtocol

# ============================
# ABSTRACT NODE CLASS
# ============================
class NodeBase(ABC):
    """Abstract base class for defining a blockchain node."""

    def __init__(self, env: simpy.Environment, node_id: int, network: 'BlockchainSimulator', 
                 consensus_protocol: 'ConsensusProtocol', blockchain: 'BlockchainBase', broadcast_protocol: Type['BroadcastProtocol']):
        self.env = env
        self.node_id = node_id
        self.network = network
        self.peers: List['NodeBase'] = []
        self.consensus_protocol = consensus_protocol
        self.blockchain = blockchain
        self.proposed_blocks: set['BlockBase'] = set()
        self.is_mining = True
        self.active = True
        self.mining_difficulty = 5 # Default difficulty for PoW
        self.env.process(self.step())  # Start consensus as a process
        # int is parent block_id, value is list of blocks waiting for that parent
        self.pending_blocks: Dict[int, List['BlockBase']] = {} # Blocks that are waiting on their parents to be added to the blockchain
        self.broadcast_protocol = broadcast_protocol(self)
        self.recent_senders: Set[tuple[int, int]] = set()  # Set of (block_id, sender_id) tuples for recent senders

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

    def mine_block(self):
        """Mines a new block and submits it according to the consensus protocol."""
        self.head = self.consensus_protocol.find_tip_of_main_chain(self.blockchain)
        assert(self.head is not None)
        
        new_block = self.blockchain.create_block(self.head, self.node_id, self.env.now)
        yield self.env.process(new_block.mine(self, self.mining_difficulty))

        # Allows for simulation to stop mining or block to be rejected
        if not self.is_mining or not self.blockchain.is_valid_block(new_block, self.mining_difficulty):
            return
        
        # Increment the total blocks mined
        self.network.metrics["total_blocks_mined"] += 1
        self.network.animator.log_event(f"Node {self.node_id} mined block {new_block.block_id}", timestamp=self.env.now)
        self.network.metrics["blocks_by_node"][self.node_id] += 1
        
        # Handle block proposal based on the consensus protocol
        self.consensus_protocol.propose_block(self, new_block)
        yield self.env.timeout(0)  # Yield to make this a generator

    def step(self):
        """Executes a timestep in the simulation."""
        if not self.active:
            return

        if len(self.proposed_blocks) > 0:
            self.consensus_protocol.execute_consensus(self)
            
        yield self.env.timeout(self.network.consensus_interval) # Wait for the next consensus interval
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

    def __repr__(self):
        return f"Node(node_id={self.node_id}, active={self.active}, mining={self.is_mining}, peers={len(self.peers)}, blockchain={self.blockchain}, consensus={self.consensus_protocol.__class__.__name__})"
    
# ============================
# BASIC NODE CLASS
# ============================
class BasicNode(NodeBase):
    """A basic node implementation that follows the consensus protocol and mines blocks."""
    
    pass  # All behavior is defined in NodeBase; extendable for custom nodes