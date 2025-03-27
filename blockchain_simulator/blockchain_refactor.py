from blockchain_simulator.blueprint import BlockchainBase, BlockBase, NodeBase
from typing import List, Type, Dict, Set, Optional

class Blockchain(BlockchainBase):
    def __init__(self, block_class: Type[BlockBase]):
        super().__init__(block_class)
        
    def add_block(self, block: BlockBase, node: NodeBase) -> bool:
        if not self.authorize_block(block, node):
            return False
        
        parent = self.get_block(block.get_parent_id())

        # Add the block to the local blockchain
        self.blocks[block.get_block_id()] = block
        parent.add_child(block.get_block_id())
        return True
    
    def authorize_block(self, block: BlockBase, node: NodeBase):
        if not self.contains_block(block.get_parent_id()) or not block.verify_block(node):
            return False
        return True
    
    def is_parent_missing(self, block: BlockBase):
        return not self.contains_block(block.get_parent_id())