from abc import ABC, abstractmethod

class BlockchainBase(ABC):
    """Abstract class for defining custom blockchain implementations."""
    
    def __init__(self, block_class):
        self.blocks = {}  # Maps block_id to Block object
        self.block_class = block_class
        self.genesis = self.create_genesis_block()

    @abstractmethod
    def create_genesis_block(self):
        """Creates the genesis block."""
        pass

    @abstractmethod
    def add_block(self, block, node):
        """Adds a block to the blockchain."""
        pass

class BasicBlockchain(BlockchainBase):
    """Basic blockchain implementation."""

    def __init__(self, block_class):
        super().__init__(block_class)

    def create_genesis_block(self):
        """Creates a genesis block."""
        genesis = self.block_class(block_id=0, parents=None, miner_id=-1, timestamp=0)
        self.blocks[0] = genesis
        return genesis

    def add_block(self, block, node):
        """Adds a block and updates the weight."""
        self.blocks[block.block_id] = block
        for parent in block.parents:
            if parent:
                parent.children.append(block)
                parent.update_weight()