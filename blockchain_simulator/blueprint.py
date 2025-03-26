from abc import ABC, abstractmethod
from typing import List, Type, Dict, Set, Optional, Generator
import simpy, random

# Griffin
class BlockBase(ABC):
    def __init__(self):
        self.block_id: int
        self.parent_id: int
        self.children_ids: Set[int]
        self.miner_id: int
        self.timestamp: float
        
    @staticmethod
    @abstractmethod
    def create_block(parent: 'BlockBase', time_stamp: float, miner: 'NodeBase')->Generator[None, None, 'BlockBase']:
        """Creates a new block based on the defined block type. Mines if it needs to and only returns upon completion."""
        raise NotImplementedError("create_block method is not implemented")
    
    @staticmethod
    @abstractmethod
    def create_genesis_block()->'BlockBase':
        """Creates a genesis block based on the defined block type."""
        raise NotImplementedError("create_genesis_block method is not implemented")
    
    @abstractmethod
    def clone(self) -> 'BlockBase':
        """Clone the block. Should be overridden by subclasses to copy specific attributes. Meant for sending copy of blocks to other nodes instead of the original block."""
        raise NotImplementedError("clone method is not implemented")
    
    @abstractmethod
    def verify_block(self, owner: 'NodeBase') -> bool:
        """ Abstract method to verify block validity"""
        raise NotImplementedError("verify_block method is not implemented")
    
    def get_block_id(self) -> int:
        """Returns the block id"""
        return self.block_id
    
    def get_parent_id(self) -> int:
        """Returns the parent block id"""
        return self.parent_id
    
    def get_children_ids(self) -> List[int]:
        """Returns the children block ids"""
        return self.children_ids
    
    def add_child(self, child_id: int) -> None:
        """Adds a child block. Makes sure no duplicate children"""
        self.children_ids.add(child_id)

    def set_parent(self, parent_id: int) -> None:
        """Sets the parent block"""
        self.parent_id = parent_id
    
    def __repr__(self) -> str:
        """Returns the string representation of the block"""
        return f"Block(id={self.block_id}, miner={self.miner_id}, parent={self.parent_id})"

# Jacob
class BlockchainBase(ABC):
    def __init__(self, block_class: Type[BlockBase]):
        """" Class for defining a blockchain.
        Needs to create a genesis block and a way of storing all the blocks in the chain.
        """
        self.genesis: BlockBase = block_class.create_genesis_block() # Create the genesis block
        self.blocks: Dict[int, BlockBase] = {} # Maps block_id to Block object
        self.blocks[self.genesis.get_block_id()] = self.genesis # Add genesis block to the blockchain
        self.head = self.genesis # The head of the blockchain
        self.block_class: Type[BlockBase] = block_class # The class of the blocks in the blockchain
    
    @abstractmethod
    def add_block(self, block: BlockBase, node: 'NodeBase') -> bool:
        """Adds a block to the blockchain.
        :args:
        block: The block to add.
        node: The node adding the block that owns this blockchain instance."""
        raise NotImplementedError("add_block method is not implemented")
    
    def get_block(self, block_id: int) -> Optional[BlockBase]:
        """Get a block by its ID."""
        return self.blocks.get(block_id)
    
    def contains_block(self, block_id: int) -> bool:
        """Check if the blockchain contains a block with the given ID."""
        return block_id in self.blocks
    
    @abstractmethod
    def authorize_block(self, block: BlockBase, node: 'NodeBase') -> bool:
        """Authorizes a block to be added to the blockchain.
        :args:
        block: The block to authorize.
        node: The node authorizing the block."""
        raise NotImplementedError("authorize_block method is not implemented")
    
    def get_current_head(self) -> BlockBase:
        """Updates and returns the current head of the blockchain."""
        return self.head
    
    def update_head(self, new_head: BlockBase) -> None:
        """Updates the head of the blockchain."""
        self.head = new_head
    
    def get_genesis(self) -> BlockBase:
        """Returns the genesis block of the blockchain."""
        return self.genesis
    
    def __repr__(self) -> str:
        """Returns the string representation of the blockchain"""
        return f"Blockchain(blocks={len(self.blocks)}, head={self.head.get_block_id()}, genesis={self.genesis.get_block_id}, block_class={self.block_class.__name__})"

# Griffin
class ConsensusProtocolBase(ABC):
    @abstractmethod
    def execute_consensus(self, node: 'NodeBase') -> None:
        """Executes a step in the consensus protocol on a node."""
        raise NotImplementedError("execute_consensus method is not implemented")
    
    @abstractmethod
    def propose_block(self, node: 'NodeBase', block: BlockBase) -> None:
        """Proposes a block to the consensus protocol of a specific node."""
        raise NotImplementedError("propose_block method is not implemented")
    
    @abstractmethod
    def update_main_chain(self, blockchain: 'BlockchainBase') -> None:
        """Updates the main chain of a node by calling the update_head method of the blockchain and starting from the get_genesis method."""
        raise NotImplementedError("update_main_chain method is not implemented")

# Siddarth
class BroadcastProtocolBase(ABC):
    @abstractmethod
    def __init__(self):
        """Initializes the broadcast protocol."""
        raise NotImplementedError("BroadcastProtocolBase class is not implemented")
    
    @abstractmethod
    def broadcast_block(self, sender: 'NodeBase', block: BlockBase) -> None:
        """Broadcasts a block to all peers."""
        raise NotImplementedError("broadcast_block method is not implemented")
    
    @abstractmethod
    def receive_block(self, recipient: 'NodeBase', block: BlockBase) -> None:
        """Receives a block from a peer."""
        raise NotImplementedError("receive_block method is not implemented")

# Jacob    
class NodeBase(ABC):
    @abstractmethod
    def __init__(self,
                 env: simpy.Environment,
                 node_id: int,
                 consensus_protocol_class: Type[ConsensusProtocolBase],
                 blockchain_class: Type[BlockchainBase],
                 broadcast_protocol_class: Type[BroadcastProtocolBase],
                 network: 'BlockchainSimulatorBase',
                 mining_difficulty: int = 0,
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
        self.env = env
        self.node_id = node_id
        self.network = network
        self.consensus = consensus_protocol_class()
        self.blockchain = blockchain_class()
        self.broadcast_protocol = broadcast_protocol_class()
        self.mining_difficulty = mining_difficulty
        self.peers: Set['NodeBase'] = set()
        self.is_mining = False
        self.recent_senders: Set[tuple[int, int]] = set()  # Set of (block_id, sender_id) tuples for recent senders. Needs to be reset periodically
        self.pending_blocks: Dict[int, Set[BlockBase]] = {}
        self.proposed_blocks: set[BlockBase] = set() # Blocks that have been proposed by this node, either through mining or receiving
    
    def get_peers(self) -> Set['NodeBase']:
        """Returns the peers of the node."""
        return self.peers
    
    def add_peer(self, peer: 'NodeBase') -> None:
        """Adds a peer to the node."""
        self.peers.add(peer)
    
    @abstractmethod
    def mine_block(self) -> None:
        """Mines a new block and submits it according to the consensus protocol."""
        raise NotImplementedError("mine_block method is not implemented")
    
    def start_mining(self) -> None:
        """Starts the mining process for this node"""
        self.is_mining = True
        self.env.process(self.mining_loop())
    
    def stop_mining(self) -> None:
        """Stops the mining process for this node"""
        self.is_mining = False
    
    def mining_loop(self):
        """The mining loop for the node. Should call mine_block and then wait for a delay before mining again."""
        while self.is_mining:
            yield self.env.process(self.mine_block())
            yield self.env.timeout(random.uniform(0.1, 0.5))
            
    def get_proposed_blocks(self) -> Set[BlockBase]:
        """Returns the proposed blocks of the node."""
        return self.proposed_blocks

    def add_proposed_block(self, block: BlockBase) -> None:
        """Adds a block to the proposed blocks of the node."""
        self.proposed_blocks.add(block)
    
    @abstractmethod
    def step(self) -> None:
        """Simulates one time step of a node execution."""
        raise NotImplementedError("step method is not implemented")
    
    def get_node_id(self) -> int:
        """Returns the node ID."""
        return self.node_id
    
    def get_consensus_protocol(self) -> ConsensusProtocolBase:
        """Returns the consensus protocol of the node."""
        return self.consensus
    
    def add_to_pending(self, block: BlockBase) -> None:
        """Adds a block to the pending blocks of the node. Meant for when parent isn't on chain yet"""
        if block.get_parent_id() not in self.pending_blocks:
            self.pending_blocks[block.get_parent_id()] = set()
        self.pending_blocks[block.get_parent_id()].add(block)
    
    def get_pending_for_parent(self, parent_id: int) -> Set[BlockBase]:
        """Returns the pending blocks for a parent block."""
        return self.pending_blocks[parent_id]
    
    def get_env(self) -> simpy.Environment:
        """Returns the simulation environment."""
        return self.env
    
    def get_is_mining(self) -> bool:
        """Returns whether the node is mining."""
        return self.is_mining
    
    def get_mining_difficulty(self) -> int:
        """Returns the mining difficulty of the node."""
        return self.mining_difficulty
    
    def __repr__(self) -> str:
        """Returns the string representation of the node."""
        return f"Node(node_id={self.node_id}, peers={len(self.peers)}, blockchain={self.blockchain})"

# Siddarth
class NetworkTopologyBase(ABC):
    @abstractmethod
    def __init__(self, 
                 max_delay: float = 0.5,
                 min_delay: float = 0.1,
                 nodes: List[NodeBase] = [],
                 ):
        raise NotImplementedError("NetworkTopologyBase class is not implemented")
    
    @abstractmethod
    def create_network_topology(self, nodes: List[NodeBase]) -> None:
        """Creates the network topology. Adds peers to each node accordingly."""
        raise NotImplementedError("create_network_topology method is not implemented")
    
    @abstractmethod
    def get_delay_between_nodes(self, node1: NodeBase, node2: NodeBase) -> float:
        """Returns the delay between two nodes. Should be between min_delay and max_delay"""
        raise NotImplementedError("get_delay_between_nodes method is not implemented")

# Jacob
class BlockchainSimulatorBase(ABC):
    @abstractmethod
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
        raise NotImplementedError("BlockchainSimulatorBase class is not implemented")
    
    @abstractmethod
    def __create_network_topology(self, topology: NetworkTopologyBase) -> None:
        """Calls the create_network_topology method of the NetworkTopology object."""
        raise NotImplementedError("__create_network_topology method is not implemented")
    
    @abstractmethod
    def __create_nodes(self, consensus_protocol: ConsensusProtocolBase, blockchain: BlockchainBase, broadcast_protocol: BroadcastProtocolBase) -> None:
        """Creates the nodes in the network."""
        raise NotImplementedError("__create_nodes method is not implemented")
    
    @abstractmethod
    def start_mining(self, num_miners: int) -> None: #TODO: Do we want to allow selection of specific nodes to mine
        """Starts the mining process for all nodes."""
        raise NotImplementedError("start_mining method is not implemented")
    
    @abstractmethod
    def __stop_mining(self) -> None:
        """Loops through all the nodes and stops all of them from mining."""
        raise NotImplementedError("__stop_mining method is not implemented")
    
    @abstractmethod
    def run(self, duration: int = 100) -> None:
        """Runs the simulation for the given duration."""
        raise NotImplementedError("run method is not implemented")
    
    @abstractmethod
    def get_consensus_interval(self) -> float:
        """Returns how long to wait before running consensus again."""
        raise NotImplementedError("get_consensus_interval method is not implemented")
