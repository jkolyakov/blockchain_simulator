from blockchain_simulator.blueprint import BlockchainBase, BlockBase, NodeBase, ConsensusProtocolBase, BroadcastProtocolBase, BlockchainSimulatorBase, NetworkTopologyBase
from typing import List, Type, Dict, Set, Optional
import simpy, random, subprocess
from tqdm import tqdm

from blockchain_simulator.manim_animator import AnimationLogger

class BlockchainSimulator(BlockchainSimulatorBase):
    def __init__(self, 
                 network_topology_class: Type[NetworkTopologyBase], 
                 consensus_protocol_class: Type[ConsensusProtocolBase], 
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
                 drop_rate: int = 0):
        self.network_topology: NetworkTopologyBase = network_topology_class()
        self.consensus_protocol_class: Type[ConsensusProtocolBase] = consensus_protocol_class
        self.blockchain_class: Type[BlockchainBase] = blockchain_class
        self.broadcast_protocol_class: Type[BroadcastProtocolBase] = broadcast_protocol_class
        self.node_class: Type[NodeBase] = node_class
        self.block_class: Type[BlockBase] = block_class
        self.num_nodes: int = num_nodes
        self.mining_difficulty: int = mining_difficulty
        self.render_animation: bool = render_animation
        self.min_delay: float = min_delay
        self.max_delay: float = max_delay
        self.consensus_interval: float = consensus_interval
        self.drop_rate: int = drop_rate
        self.env = simpy.Environment()
        self.nodes: List[NodeBase] = self._create_nodes(consensus_protocol_class, blockchain_class, broadcast_protocol_class)
        self._create_network_topology(self.network_topology)
        self.animator = AnimationLogger()
        self.input_pipe: Dict[int, simpy.Store] = {}
        self.request_backtrack: Dict[tuple[int, int], int] = {}  # (block_id, current_node) -> previous_node

        # Create message pipes for each node and start the message consumer
        for node in self.nodes:
            self.input_pipe[node.get_node_id()] = simpy.Store(self.env)
            self.env.process(self._message_consumer(self.env, node))
    
    
    def _create_nodes(self, consensus_protocol_class: Type[ConsensusProtocolBase], blockchain_class: Type[BlockchainBase], broadcast_protocol_class: Type[BroadcastProtocolBase]) -> List[NodeBase]:    
        return [self.node_class(self.env, i, self, consensus_protocol_class, blockchain_class, broadcast_protocol_class, self.block_class, self.mining_difficulty)
                for i in range(self.num_nodes)]   
    
    def _create_network_topology(self, topology: NetworkTopologyBase):
        topology.create_network_topology(self.nodes)
    
    def get_consensus_interval(self):
        return self.consensus_interval
    
    def start_mining(self, num_miners: int = 0):
        node_ids = random.sample(range(self.num_nodes), num_miners)
        [self.nodes[node_id].start_mining() for node_id in node_ids]
    
    def _stop_mining(self):
        [node.stop_mining() for node in self.nodes]
    
    def get_drop_rate(self):
        return self.drop_rate
        
    def run(self, duration: float = 100):
        print(f"🚀 Running blockchain simulation for {duration} seconds...\n")
        with tqdm(total=duration, desc="⏳ Simulation Progress", unit="s", ascii=" ▖▘▝▗▚▞█") as pbar:
            last_time = self.env.now 
            while self.env.now < duration:
                self.env.step()
                # Update pbar with the actual time that has passed
                time_advanced = self.env.now - last_time
                pbar.update(time_advanced)
                last_time = self.env.now  # Update last_time to current time
            self._stop_mining()
        self._print_simulation_results()
        
        if self.render_animation:
            self.animator.set_num_nodes(self.num_nodes)
            self.animator.set_peers({n.node_id: [p.node_id for p in n.peers] for n in self.nodes})
            manim_file = "./blockchain_simulator/manim_animator.py"
            scene_class = "BlockchainAnimation"
            self.animator.save("animation_events.json")
            # run the subprocess to render the animation
            subprocess.run(["manim", "-pql", manim_file, scene_class, "-o", "network_activity.mp4"])        

    
    def _print_simulation_results(self):
        print("\n📊 Simulation Results:")
        for node in self.nodes:
            print(node.blockchain)
    
    def send_block_to_node(self, sender: NodeBase, recipient: NodeBase, block: BlockBase):
            yield self.env.timeout(self.network_topology.get_delay_between_nodes(sender, recipient))
            yield self.input_pipe[recipient.get_node_id()].put((block, sender))
    
    def register_request_origin(self, block_id: int, current_node: NodeBase, origin_node: NodeBase):
        """Register the origin of the request for backtracking."""
        self.request_backtrack[(block_id, current_node.get_node_id())] = origin_node.get_node_id()
    
    def get_request_origin(self, block_id: int, current_node: NodeBase) -> Optional[NodeBase]:
        """Get the origin of the request for backtracking."""
        node_id = self.request_backtrack.get((block_id, current_node.get_node_id()), None)
        if node_id is not None:
            return self.nodes[node_id]
        return None
            
    def _message_consumer(self, env: simpy.Environment, node: NodeBase):
        while True:
            # Get block from the message from the input pipe
            block, sender = yield self.input_pipe[node.get_node_id()].get()
            
            # Process message from the other block
            node.broadcast_protocol.process_block(node, sender, block)
            yield env.timeout(0)