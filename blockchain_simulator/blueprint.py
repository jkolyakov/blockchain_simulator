from abc import ABC, abstractmethod
from typing import List, Type, Dict, Set, Optional
import simpy

#Griffin
class BlockBase(ABC):
    @abstractmethod
    @staticmethod
    def create_block(self, parent: 'BlockBase', time_stamp: float, miner: 'NodeBase')->'BlockBase':
        """Creates a new block based on the defined block type."""
        pass
    
    @abstractmethod
    @staticmethod
    def create_genesis_block(self)->'BlockBase':
        """Creates a genesis block based on the defined block type."""
        pass
    
    @abstractmethod
    def clone(self) -> 'BlockBase':
        """Clone the block. Should be overridden by subclasses to copy specific attributes. Meant for sending copy of blocks to other nodes instead of the original block."""
        pass
    
    @abstractmethod
    def verify_block(self, owner: 'NodeBase') -> bool:
        """ Abstract method to verify block validity"""
        pass
    
    @abstractmethod
    def get_block_id(self) -> int:
        """Returns the block id"""
        pass
    
    @abstractmethod
    def get_parent_id(self) -> int:
        """Returns the parent block id"""
        pass
    
    @abstractmethod
    def get_children_ids(self) -> List[int]:
        """Returns the children block ids"""
        pass
    
    @abstractmethod
    def add_child(self, child_id: int) -> None:
        """Adds a child block"""
        pass

    @abstractmethod
    def set_parent(self, parent_id: int) -> None:
        """Sets the parent block"""
        pass
    
    @abstractmethod
    def __repr__(self) -> str:
        """Returns the string representation of the block"""
        pass

# Jacob
class BlockchainBase(ABC):
    def __init__(self, block_class: Type[BlockBase], mining_difficulty: int):
        """" Abstract class for defining a blockchain.
        Needs to create a genesis block and a way of storing all the blocks in the chain.
        """
        pass
    
    @abstractmethod
    def add_block(self, block: BlockBase, node: 'NodeBase') -> bool:
        """Adds a block to the blockchain.
        :args:
        block: The block to add.
        node: The node adding the block that owns this blockchain instance."""
        pass
    
    @abstractmethod
    def get_block(self, block_id: int) -> Optional[BlockBase]:
        """Get a block by its ID."""
        pass
    
    @abstractmethod
    def contains_block(self, block_id: int) -> bool:
        """Check if the blockchain contains a block with the given ID."""
        pass
    
    @abstractmethod
    def authorize_block(self, block: BlockBase, node: 'NodeBase') -> bool:
        """Authorizes a block to be added to the blockchain.
        :args:
        block: The block to authorize.
        node: The node authorizing the block."""
        pass
    
    @abstractmethod
    def __repr__(self) -> str:
        """Returns the string representation of the blockchain"""
        pass

# Griffin
class ConsensusProtocolBase(ABC):
    @abstractmethod
    def execute_consensus(self, node: 'NodeBase') -> None:
        """Executes a step in the consensus protocol on a node."""
        pass
    
    @abstractmethod
    def propose_block(self, node: 'NodeBase', block: BlockBase) -> None:
        """Proposes a block to the consensus protocol of a specific node."""
        pass
    pass

# Siddarth
class BroadcastProtocolBase(ABC):
    def __init__(self):
        """Initializes the broadcast protocol."""
        pass
    
    @abstractmethod
    def broadcast_block(self, sender: 'NodeBase', block: BlockBase) -> None:
        """Broadcasts a block to all peers."""
        pass
    
    @abstractmethod
    def receive_block(self, recipient: 'NodeBase', block: BlockBase) -> None:
        """Receives a block from a peer."""
        pass

# Jacob    
class NodeBase(ABC):
    def __init__(self,
                 env: simpy.Environment,
                 node_id: int,
                 consensus_protocol_class: Type[ConsensusProtocolBase],
                 blockchain_class: Type[BlockchainBase],
                 broadcast_protocol_class: Type[BroadcastProtocolBase],
                 network: 'BlockchainSimulatorBase',
                 mining_difficulty: int = 5,
                 ):
        """" Abstract class for defining a node in the network.
        :args:
        env: The simulation environment.
        node_id: The ID of the node.
        consensus_protocol_class: The consensus protocol class to use for the node.
        blockchain_class: The blockchain class to use for the node.
        broadcast_protocol_class: The broadcast protocol class to use for the node.
        network: The network the node is a part of.
        mining_difficulty: The mining difficulty for the node.
        
        """
        pass
    
    @abstractmethod
    def get_peers(self) -> List['NodeBase']:
        """Returns the peers of the node."""
        pass
    
    @abstractmethod
    def add_peer(self, peer: 'NodeBase') -> None:
        """Adds a peer to the node."""
        pass
    
    @abstractmethod
    def mine_block(self) -> None:
        """Mines a new block and submits it according to the consensus protocol."""
        pass
    
    @abstractmethod
    def start_mining(self) -> None:
        """Starts the mining process for this node"""
        pass
    
    @abstractmethod
    def stop_mining(self) -> None:
        """Stops the mining process for this node"""
        pass
    
    @abstractmethod
    def mining_loop(self) -> None:
        """The mining loop for the node. Should call mine_block and then wait for a delay before mining again."""
        pass
    
    @abstractmethod
    def step(self) -> None:
        """Simulates one time step of a node execution."""
        pass

# Siddarth
class NetworkTopologyBase(ABC):
    def __init__(self, 
                 max_delay: float = 0.5,
                 min_delay: float = 0.1,
                 nodes: List[NodeBase] = [],
                 ):
        pass
    
    @abstractmethod
    def create_network_topology(self, nodes: List[NodeBase]) -> None:
        """Creates the network topology. Adds peers to each node accordingly."""
        pass
    
    @abstractmethod
    def get_delay_between_nodes(self, node1: NodeBase, node2: NodeBase) -> float:
        """Returns the delay between two nodes. Should be between min_delay and max_delay"""
        pass
    
# Jacob
class BlockchainSimulatorBase(ABC):
    def __init__(self, 
                 network_topology_class: Type[NetworkTopologyBase], 
                 consensus_protocol_class: Optional[Type[ConsensusProtocolBase]], 
                 blockchain_class: Type[BlockchainBase], 
                 broadcast_protocol_class: Type[BroadcastProtocolBase],
                 node_class: Type[NodeBase],
                 block_class: Type[BlockBase],
                 num_nodes: int,
                 mining_difficulty: int,
                 render_animation: bool = False,
                 min_delay: float = 0.1,
                 max_delay: float = 0.5,
                 consensus_interval: float = 0.1,
                 drop_rate: int = 0,
                 ):
        """ Initializes the blockchain simulator with the given parameters.
        :args:
        network_topology_class: The network topology class to use for the simulation.
        consensus_protocol_class: The consensus protocol class to use for the simulation.
        blockchain_class: The blockchain class to use for the simulation.
        broadcast_protocol_class: The broadcast protocol class to use for the simulation.
        node_class: The node class to use for the simulation.
        block_class: The block class to use for the simulation.
        num_nodes: The number of nodes in the network.
        mining_difficulty: int: The mining difficulty for the nodes.
        render_animation: bool: Whether to render the animation.
        min_delay: The minimum delay for message passing.
        max_delay: The maximum delay for message passing.
        consensus_interval: The interval for consensus execution.
        drop_rate: The drop rate for messages. 
        
        Note that this shold create a simpy.Environment object and store it in the self.env attribute.   
        """
        pass
    
    @abstractmethod
    def __create_network_topology(self, topology: NetworkTopologyBase) -> None:
        """Calls the create_network_topology method of the NetworkTopology object."""
        pass
    
    @abstractmethod
    def __create_nodes(self, consensus_protocol: ConsensusProtocolBase, blockchain: BlockchainBase, broadcast_protocol: BroadcastProtocolBase) -> None:
        """Creates the nodes in the network."""
        pass
    
    @abstractmethod
    def start_mining(self, num_miners: int) -> None: #TODO: Do we want to allow selection of specific nodes to mine
        """Starts the mining process for all nodes."""
        pass
    
    @abstractmethod
    def __stop_mining(self) -> None:
        """Loops through all the nodes and stops all of them from mining."""
        pass
    
    @abstractmethod
    def run(self, duration: int = 100) -> None:
        """Runs the simulation for the given duration."""
        pass
    
# Jacob but don't implement this class
class Metrics(ABC):
    def __init__(self):
        """Initializes the metrics collection object."""
        pass
    
    @abstractmethod
    def collect_metrics(self, node: NodeBase) -> None:
        """Collects metrics from the node."""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, float]:
        """Returns the metrics collected."""
        pass
    
    @abstractmethod
    def reset_metrics(self) -> None:
        """Resets the metrics collected."""
        pass

