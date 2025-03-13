from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

# ============================
# BLOCK ABSTRACT CLASS
# ============================

class BlockBase(ABC):
    """Abstract base class for defining a custom block structure."""
    
    def __init__(self, block_id: int, parent: Optional['BlockBase'], miner_id: int, timestamp: float):
        self.block_id: int = block_id
        self.parent: 'BlockBase' = parent  # Supports DAG & Chain
        self.miner_id: int = miner_id
        self.children: List['BlockBase'] = []
        self.timestamp: float = timestamp  # Block creation time
        self.weight = 1  # Default weight

    @abstractmethod
    def update_weight(self) -> None:
        """Abstract method to update block weight based on consensus rules."""
        pass

# ============================
# BLOCK IMPLEMENTATION
# ============================

class BasicBlock(BlockBase):
    """A simple block structure with basic weight calculation."""
    
    def __init__(self, block_id: int, parent: Optional['BlockBase'], miner_id: int, timestamp: float):
        super().__init__(block_id, parent, miner_id, timestamp)
        self.weight: int = 1  # Default weight

    def update_weight(self) -> None:
        """Updates weight based on number of children."""
        self.weight = 1 + sum(child.weight for child in self.children)