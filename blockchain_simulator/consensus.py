from blockchain_simulator.blueprint import BlockchainBase, BlockBase, NodeBase, ConsensusProtocolBase, BroadcastProtocolBase, BlockchainSimulatorBase
from blockchain_simulator.block import PoWBlock
from typing import Set, List, Dict, Any

class GHOSTProtocol(ConsensusProtocolBase):        
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "fork_resolutions": 0,
        }

    def update_main_chain(self, blockchain: BlockchainBase, node_id: int):
        head = blockchain.get_genesis()
        previous_head = blockchain.get_current_head().block_id
        while len(head.get_children_ids()) > 0:
            children_ids: Set[PoWBlock] = head.get_children_ids()
            children: List[PoWBlock] = [blockchain.get_block(child_id) for child_id in children_ids]
            head = max(children, key=lambda b: (b.get_weight(), -b.get_block_id()))
        blockchain.update_head(head)
        if previous_head != blockchain.get_current_head().get_parent_id():
            self.metrics["fork_resolutions"] += 1
    
    def propose_block(self, node: NodeBase, block: PoWBlock):
        if node.blockchain.authorize_block(block, node):
            node.add_proposed_block(block)
            
    def execute_consensus(self, node: NodeBase):
        if len(node.get_proposed_blocks()) == 0:
            return
        
        for block in node.get_proposed_blocks():
            block_clone: PoWBlock = block.clone()
            if node.blockchain.add_block(block_clone, node):
                self._update_weights(block_clone, node)
                self.update_main_chain(node.blockchain, node.node_id)               
                self._process_pending_blocks(node, block.get_block_id())
                node.broadcast_protocol.broadcast_block(node, block)
        # Update the main chain
        node.get_proposed_blocks().clear()
    
    def _update_weights(self, block: PoWBlock, node: NodeBase):
        weight = 1
        children = block.get_children_ids()
        for child_id in children:
            child: PoWBlock = node.blockchain.get_block(child_id)
            assert(isinstance(child_id, int))
            weight += child.get_weight()
        block.set_weight(weight)
        
        if block.get_block_id() == node.blockchain.get_genesis().get_block_id(): # Genesis block
            return
        parent_id = block.get_parent_id()
        parent: PoWBlock = node.blockchain.get_block(parent_id)
        self._update_weights(parent, node)
                
    def _process_pending_blocks(self, node: NodeBase, parent_id: int):
        for block in node.get_pending_for_parent(parent_id):
            node.add_proposed_block(block)
        node.get_pending_for_parent(parent_id).clear()