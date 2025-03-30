from blockchain_simulator.blueprint import BlockchainBase, BlockBase, NodeBase, ConsensusProtocolBase, BroadcastProtocolBase, BlockchainSimulatorBase
from typing import List, Type, Dict, Set, Optional, Any
import simpy

class Node(NodeBase):
    def __init__(self, env: simpy.Environment, node_id: int, network: 'BlockchainSimulatorBase', 
                 consensus_protocol_class: Type['ConsensusProtocolBase'], blockchain_class: Type['BlockchainBase'], broadcast_protocol_class: Type['BroadcastProtocolBase'],  block_class: Type['BlockBase'], mining_difficulty: int = 0):\
                 
        super().__init__(env, node_id, network, consensus_protocol_class, blockchain_class, broadcast_protocol_class, block_class, mining_difficulty)
        self.num_mined_blocks: int = 0

    def mine_block(self):
        self.consensus.update_main_chain(self.blockchain, self.node_id) # Update the main chain
        
        # Create a new block
        # Note: create_block returns a BlockBase which should work to assign new_block through the yield
        new_block: BlockBase = yield self.env.process(self.block_class.create_block(self.blockchain.get_current_head(), self.env.now, self)) 
        if not self.is_mining or not self.blockchain.authorize_block(new_block, self):
            return
        self.network.animator.log_event(f"Node {self.node_id} mined block {new_block.block_id}", timestamp=self.env.now)
        self.consensus.propose_block(self, new_block)
        self.num_mined_blocks += 1
    
    def step(self):
        self.consensus.execute_consensus(self)
        yield self.env.timeout(self.network.get_consensus_interval())
        self.env.process(self.step())
        
    def __repr__(self):
        return f"Node(node_id={self.node_id}, peers={len(self.peers)}, mining_difficulty={self.mining_difficulty}, blockchain={self.blockchain})"