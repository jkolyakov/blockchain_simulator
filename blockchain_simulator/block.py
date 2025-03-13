from abc import ABC, abstractmethod

class BlockBase(ABC):
    """Abstract base class for defining a custom block structure."""
    
    def __init__(self, block_id, parents, miner_id, timestamp):
        self.block_id = block_id
        self.parents = parents if isinstance(parents, list) else [parents]  # Supports DAG & Chain
        self.miner_id = miner_id
        self.children = []
        self.timestamp = timestamp  # Block creation time

    @abstractmethod
    def update_weight(self):
        """Abstract method to update block weight based on consensus rules."""
        pass

class BasicBlock(BlockBase):
    """A simple block structure with basic weight calculation."""
    
    def __init__(self, block_id, parents, miner_id, timestamp):
        super().__init__(block_id, parents, miner_id, timestamp)
        self.weight = 1  # Default weight

    def update_weight(self):
        """Updates weight based on number of children."""
        self.weight = 1 + sum(child.weight for child in self.children)