from __future__ import annotations
import logging
import random
import simpy
from abc import ABC, abstractmethod
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from blockchain_simulator.block import BlockBase
    from blockchain_simulator.blockchain import BlockchainBase
    from blockchain_simulator.consensus import ConsensusProtocol
    from blockchain_simulator.simulator import BlockchainSimulator

# ============================
# ABSTRACT NODE CLASS
# ============================

# TODO: Call step() when node joins the network
# TODO: Update select_best_block to get the block with the highest weight (or latest block) to be the parent of a new mined block
# TODO: New function will actually call the consensus protocol
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
        self.head = blockchain.genesis
        self.proposed_blocks: set['BlockBase'] = set()  # Stores when blocks were received

    def add_peer(self, peer: 'NodeBase'):
        """Connects this node to a peer."""
        if peer not in self.peers:
            self.peers.append(peer)
            
    def remove_peer(self, peer: 'NodeBase'):
        """Disconnects this node from a peer."""
        if peer in self.peers:
            self.peers.remove(peer)
    
    # TODO: Have the simulator call this method on all nodes to start consensus after consensus_after_delay timesteps
    def consensus_step(self):
        """Executes the consensus protocol."""
        self.consensus_protocol.execute_consensus(self)

    def receive_consensus_block(self, block: 'BlockBase', delay: float, sender_id: int):
        """
        Processes an incoming consensus-finalized block and updates the chain if necessary.

        :param block: The finalized block chosen by consensus.
        :param delay: Network delay before processing the block.
        :param sender_id: The ID of the node that sent the block.
        """
        yield self.env.timeout(delay)

        # If block already exists in the blockchain, ignore it
        if block.block_id in self.blockchain.blocks:
            return  

        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} received finalized block {block.block_id} from Node {sender_id}")

        # Let the consensus protocol decide how to handle it (chain switching, etc.)
        self.consensus_protocol.accept_consensus_block(self, block)
        
        # IMPORTANT: Recompute the best chain after receiving a consensus block
        self.head = self.consensus_protocol.select_best_block(self.blockchain)

    @abstractmethod
    def mine_block(self):
        """Abstract method for mining a block."""
        pass

    @abstractmethod
    def broadcast_block(self, block: 'BlockBase'):
        """Abstract method for broadcasting a block to peers."""
        pass

    @abstractmethod
    def receive_block(self, block: 'BlockBase', delay: float, sender_id: int):
        """Abstract method for processing an incoming block."""
        pass
    
    @abstractmethod
    def step(self):
        """Abstract method for executing a timestep in the simulation."""
        pass

# ============================
# BASIC NODE CLASS
# ============================

class BasicNode(NodeBase):
    """A basic node implementation that follows the consensus protocol and mines blocks."""

    def mine_block(self):
        """Mines a new block and broadcasts it."""
        # TODO: Randomize to see if a block is mined at all
        
        # set new_block_id to a randomized 256bit hash
        new_block_id = hash((self.node_id, self.env.now, random.getrandbits(256)))
        
        # Ensures the head is the best block before mining a new block
        self.head = self.consensus_protocol.select_best_block()
        
        new_block = self.blockchain.block_class(
            block_id=new_block_id,
            parent=self.head,
            miner_id=self.node_id,
            timestamp=self.env.now
        )
        
        logging.info(f"Time {self.env.now:.2f}: Node {self.node_id} mined block {new_block_id}")
        self.network.metrics["total_blocks_mined"] += 1
        self.proposed_blocks.add(new_block) # Add the block to its own proposed blocks
        self.broadcast_block(new_block)

    def broadcast_block(self, block: 'BlockBase') -> None:
        """Broadcasts a block to all connected peers with a random network delay."""
        # The above property would depend on the exact consensus protocol we are talking about right? For ex, in Algorand, the block is broadcasted multiple times.
        for peer in self.peers:
            delay = random.uniform(1, self.network.max_delay) #TODO: make this a parameter for different tolerances
            self.env.process(peer.receive_block(block, delay, self.node_id))

    def receive_block(self, block: 'BlockBase', delay: float, sender_id: int):
        """Processes an incoming block after a delay."""
        yield self.env.timeout(delay)        
        
        if delay > self.network.consensus_after_delay:
            return
        
        # Log block propagation time
        if block.block_id not in self.proposed_blocks:
            self.proposed_blocks.add(block)
            self.network.metrics["block_propagation_times"].append(self.env.now - block.timestamp)
            self.broadcast_block(block)
            
    def step(self):
        """Executes a timestep in the simulation.
        Called when node is joined to network
        runs continousto broadcast all proposed nodes 
        and decide if consensus is needed
        """
        
        if self.env.now % self.network.consensus_after_delay == 0:
            self.consensus_step()
            
        self.mine_block()
        
        # Propogate all the proposed blocks this node has seen to its peers
        for block in self.proposed_blocks:
            self.broadcast_block(block)
            
        yield self.env.timeout(1)
        self.step()
        
