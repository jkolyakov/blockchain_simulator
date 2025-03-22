from __future__ import annotations
import logging
import random
import simpy
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING, Type



if TYPE_CHECKING:
    from blockchain_simulator.block import BlockBase
    from blockchain_simulator.blockchain import BlockchainBase
    from blockchain_simulator.consensus import ConsensusProtocol
    from blockchain_simulator.simulator import BlockchainSimulator
    from blockchain_simulator.broadcastMessage import ConsensusBroadcast

# ============================
# ABSTRACT NODE CLASS
# ============================
class NodeBase(ABC):
    """Abstract base class for defining a blockchain node."""

    def __init__(self, env: simpy.Environment, node_id: int, network: 'BlockchainSimulator', 
                 consensus_impl: Type['ConsensusProtocol'], blockchain_impl: Type['BlockchainBase'], block_impl: Type['BlockBase']):
        self.env = env
        self.node_id = node_id
        self.network = network
        self.peers: List['NodeBase'] = []
        self.consensus_protocol = consensus_impl()
        self.blockchain = blockchain_impl(block_impl, self)
        self.block_queue: set['BlockBase'] = set()
        self.is_mining = True
        self.active = True
        self.mining_difficulty = 5 # Default difficulty for PoW
        self.env.process(self.step())  # Start consensus as a process

    def add_block_to_queue(self, block: 'BlockBase'):
        # print("add block to queue")
        """Adds a block to the queue """
        self.block_queue.add(block)

    def get_from_blockqueue(self) -> 'BlockBase':
        """Gets a block from the queue """
        if len(self.block_queue) > 0:
            # print("get block to queue")
            return self.block_queue.pop()
        return None
    
    def remove_from_blockqueue(self, block_id: int):
        """Removes a block from the queue """
        for block in self.block_queue:
            if block.block_id == block_id:
                self.block_queue.remove(block)
                return
        return None

    
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

        new_block = self.blockchain.create_block(self.blockchain.head, self.node_id, self.env.now)
        yield self.env.process(new_block.mine(self, self.mining_difficulty))
        
        # Allows for simulation to stop mining or block to be rejected
        if not self.is_mining or not self.blockchain.is_valid_block(new_block):
            return
        
        # Increment the total blocks mined
        self.network.metrics["total_blocks_mined"] += 1
        self.network.metrics["blocks_by_node"][self.node_id] += 1
        
        # Handle block proposal based on the consensus protocol
        self.add_block_to_queue(new_block)
        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} mined block {new_block.block_id}")
        yield self.env.timeout(0)  # Yield to make this a generator

    def receive_message(self, broadcast_message: 'ConsensusBroadcast'):
        """Processes an incoming block after a delay."""
        # yield self.env.timeout(delay)
        

        block = broadcast_message.data['block']
        # print(f"Node {self.node_id} Received block {block.block_id} from {broadcast_message.sender}")

        if block.block_id in self.blockchain.blocks:
            return  # Block already known, ignore it
        
        if self.node_id == 3:
            print(f"Node {self.node_id} Received block {block.block_id} with children {[x.block_id for x in block.children]}")
            
        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} received block {block.block_id} from Node {broadcast_message.sender}")
        # Handle block proposal based on the consensus protocol
        self.blockchain.receive_final_consensus_block(broadcast_message)

    def step(self):
        """Executes a timestep in the simulation."""
        # print(f"Steo function called by node {self.node_id}")
        logging.info(f"Node {self.node_id} started executing consensus with {len(self.block_queue)} blocks in queue and is_active={self.active}")
        if not self.active:
            return

        
        if len(self.block_queue) > 0:
            print(f"Node {self.node_id} started executing consensus")
            candidate_block = self.consensus_protocol.execute_consensus(self)
            self.blockchain.add_consensus_block_to_chain(candidate_block)
                
            
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

# ============================
# BASIC NODE CLASS
# ============================
class BasicNode(NodeBase):
    """A basic node implementation that follows the consensus protocol and mines blocks."""
    
    pass  # All behavior is defined in NodeBase; extendable for custom nodes