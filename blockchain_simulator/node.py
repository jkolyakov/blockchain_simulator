from __future__ import annotations
import logging
import random
import time

import simpy
import asyncio
from abc import ABC, abstractmethod
from typing import List, TYPE_CHECKING, Dict

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
                 consensus_protocol: 'ConsensusProtocol', blockchain: 'BlockchainBase'):
        self.env = env
        self.node_id = node_id
        self.network = network
        self.peers: List['NodeBase'] = []
        self.consensus_protocol = consensus_protocol
        self.blockchain = blockchain
        self.block_queue: List['BlockBase'] = []  # Stores when blocks were received
        self.active = True
        self.last_consensus_time = 0
        self.mining_difficulty = 4 # Default difficulty for PoW


        random.seed(node_id)
        self.private_key = random.random()

        self.mining_time: int = 10                               #mining_time stores the time after which mining process for a new block starts
        #TODO: discuss if we want to 
        self.is_mining: bool = False                              #is_mining = False -> the node is not mining blocks currently.
        asyncio.run(self.async_mining())

    def add_to_blockqueue(self, block: 'BlockBase'):
        """Add block to its queue of blocks"""
        self.block_queue.append(block)

    def remove_from_blockqueue(self, block_id: int):
        """Remove block_id from the queue of blocks"""
        for block in self.block_queue:
            if block.block_id == block_id:
                self.block_queue.remove(block)

    def get_from_blockqueue(self):
        if not self.block_queue:
            raise Exception("Block queue is empty")
        return self.block_queue.pop(0)

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
        # self.head = self.consensus_protocol.select_best_block(self.blockchain)
        # if self.head.block_id not in self.blockchain.blocks.keys():
        #     logging.warning(f"Time {self.env.now:.2f}: Node {self.node_id} head block not in blockchain")
        new_block = self.blockchain.create_block(self.blockchain.head, self.node_id, self.env.now)
        yield self.env.process(new_block.mine(self, self.mining_difficulty))
        # Allows for simulation to stop mining
        #TODO: check yield vs await
        if not self.is_mining:
            logging.warning(f"Time {self.env.now:.2f}: Node {self.node_id} stopped mining")
            return        
        # Ensure the block meets PoW validity before adding it. This validity is checked when the consensus protocol is executed, not when mining.
        # if not self.blockchain.add_block(new_block, self):
        #     logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} failed mining block {new_block.block_id}")
        #     return
        # Increment the total blocks mined
        self.network.metrics["total_blocks_mined"] += 1
        self.network.metrics["blocks_by_node"][self.node_id] += 1
        
        self.add_to_blockqueue(new_block)


    async def receive_broadcast_message(self, broadcast_message: ConsensusBroadcast) -> bool:
        """This function should be triggered whenever this node receives a broadcast message. This function performs computation on the received message and returns true of the computation is successful"""

        if broadcast_message.data['consensus_type'] == ConsensusProtocol.CONSENSUS_TYPE['final']:
            return self.blockchain.receive_final_consensus_block(broadcast_message)
            

    def step(self):
        """Executes a timestep in the simulation."""
        if not self.active:
            return

        if self.env.now >= self.last_consensus_time + self.network.consensus_interval:
            logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} executing consensus")
            if len(self.block_queue) > 0:
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
    def mine_block(self):
        # TODO: Randomize to see if a block is mined at all
        """Mines a new block and broadcasts it."""
        # set new_block_id to a randomized 256bit hash
        
        
        new_block_id = hash((self.node_id, self.env.now, random.getrandbits(256)))
        # Ensures the head is the best block before mining a new block. Update: head is a property of the blockchain owned by this node. It is assumed that head stores the head of main chain at all times.
        new_block = self.blockchain.block_class( block_id=new_block_id, timestamp=self.env.now, parent=self.blockchain.head, miner_id=self.node_id)
        
        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} mined block {new_block_id}")
        self.network.metrics["total_blocks_mined"] += 1
        self.add_proposed_block(new_block) # Add the block to its own proposed blocks
    def broadcast_block(self, block: 'BlockBase') -> None:
        # The above property would depend on the exact consensus protocol we are talking about right? For ex, in Algorand, the block is broadcasted multiple times.
        """Broadcasts a block to all connected peers with a random network delay."""
        for peer in self.peers:
            delay = random.uniform(1, self.network.max_delay) #TODO: make this a parameter for different tolerances
            self.env.process(peer.receive_block(block, delay, self.node_id))

    def receive_block(self, block: 'BlockBase', delay: float, sender_id: int):
        """Processes an incoming block after a delay."""
        if delay > self.network.consensus_after_delay:
            yield self.env.timeout(delay)        
        
            return
        
        if block.block_id not in self.block_queue:
        # Log block propagation time
            self.block_queue.add(block)
            self.broadcast_block(block)
            self.network.metrics["block_propagation_times"].append(self.env.now - block.timestamp)