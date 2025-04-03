from blockchain_simulator.blueprint import BlockchainBase, BlockBase, NodeBase, ConsensusProtocolBase, BroadcastProtocolBase, BlockchainSimulatorBase, NetworkTopologyBase
from typing import List, Type, Dict, Set, Optional
import simpy, random, subprocess, math
from tqdm import tqdm

#from blockchain_simulator.manim_animator import AnimationLogger
from blockchain_simulator.examples.blockchain_simulator.manim_animator import AnimationLogger

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
                 drop_rate: int = 0,
                 set_bandwidth: bool = False,
                 bandwidth: int = 1_000_000, # 1 Gbps
                 packet_size: int = 1500, # 1 KB
                 block_size: int = 1_000_000, # 1 MB
                 ):
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
        self.network_topology: NetworkTopologyBase = network_topology_class(self.min_delay, self.max_delay, self.nodes)
        self.animator = AnimationLogger()
        self.input_pipe: Dict[int, simpy.Store] = {}
        self.request_backtrack: Dict[tuple[int, int], int] = {}  # (block_id, current_node) -> previous_node
        self.bandwidth: simpy.Resource = simpy.Resource(self.env, capacity=bandwidth)
        self.packet_size: int = packet_size
        self.block_size: int = block_size
        self.set_bandwidth: bool = set_bandwidth

        assert self.packet_size < bandwidth, "Packet size must be less than bandwidth"
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
    

    def find_main_chain(self,node) -> set:
        """Finds the main chain by backtracking from the current head."""
        main_chain = set()
        block = node.blockchain.head
        while block:
            main_chain.add(block.block_id)
            # return main_chain
            # block = block.get_parent()  # Move up the chain
            block = node.blockchain.get_block(block.get_parent_id())  # Move up the chain

        return main_chain
    

    def _measure_convergence(self) -> float:
        """Measure the percentage of nodes that agree on the same chain."""
        heads = {}
        # Count occurrences of each head block
        for node in self.nodes:
            head_id = node.blockchain.get_current_head().block_id
            if head_id in heads:
                heads[head_id] += 1
            else:
                heads[head_id] = 1
        
        # Find the most common head
        if not heads:
            return 0.0
            
        most_common_head, count = max(heads.items(), key=lambda x: x[1])
        
        # Calculate the percentage of nodes with this head
        return most_common_head, count / len(self.nodes) * 100
    

    

    def collect_metrics(self):
        """Collect metrics from the simulation."""
        total_orphans = 0
        for node in self.nodes:
            main_chain = self.find_main_chain(node)
            block_list = node.blockchain.blocks

            for block_id in block_list:
                if block_id not in main_chain:
                    total_orphans += 1
        # Combine simulator and protocol metrics
        metrics = {
            "num_nodes": self.num_nodes,
            "mining_difficulty": self.mining_difficulty,
            "drop_rate": self.drop_rate,
            "consensus_interval": self.consensus_interval,
            "network_topology": self.network_topology.__class__.__name__,
            "chain_length": {node.get_node_id(): node.blockchain.get_chain_length() for node in self.nodes},
            "longest_chain_length": max(node.blockchain.get_chain_length() for node in self.nodes),
            "total_blocks_mined": sum(node.num_mined_blocks for node in self.nodes),
            "fork resolutions": sum(node.consensus.metrics["fork_resolutions"] for node in self.nodes),
            "average_fork_resolutions": sum(node.consensus.metrics["fork_resolutions"] for node in self.nodes) / self.num_nodes,
            "throughput (blocks/s)": (sum(node.blockchain.get_chain_length() for node in self.nodes) / self.num_nodes) / self.env.now,
            "network_topology": self.network_topology.__class__.__name__,
            "orphaned_blocks": total_orphans,
            "convergence": self._measure_convergence(),
        }
        return metrics

    def display_metrics(self):
        """Display collected metrics in a readable format."""
        metrics = self.collect_metrics()
        print("\n📈 Simulation Metrics:")
        print(f"Simulation Duration: {self.env.now:.2f} seconds")
        print(f"Number of Nodes: {metrics['num_nodes']}")
        print(f"Mining Difficulty: {metrics['mining_difficulty']}")
        print(f"Network Topology: {metrics['network_topology']}")
        print(f"Drop Rate: {metrics['drop_rate']}%")
        print(f"Consensus Interval: {metrics['consensus_interval']} seconds")
        average_chain_length = sum(metrics['chain_length'].values()) / metrics['num_nodes']
        print(f"Average Length: {average_chain_length:.2f} blocks")
        print(f"Total Blocks Mined: {metrics['total_blocks_mined']}")
        print(f"Orphaned Blocks: {metrics['orphaned_blocks']}")
        print(f"Fork Resolutions: {metrics['fork resolutions']}")
        print(f"Average Fork Resolutions: {metrics['average_fork_resolutions']}")
        print(f"Throughput (blocks/s): {metrics['throughput (blocks/s)']:.2f} blocks/s")
        print(f"Convergence: {metrics['convergence'][1]:.2f}% of nodes agreeing on the same chain")
        print(f"😊😊😊😊😊😊😊😊😊😊😊😊😊😊😊😊")

        
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
        print("\n✅ Simulation complete!!")
        self.display_metrics()
        
        if self.render_animation:
            self.animator.set_num_nodes(self.num_nodes)
            self.animator.set_peers({n.node_id: [p.node_id for p in n.peers] for n in self.nodes})
            manim_file = "./blockchain_simulator/manim_animator.py"
            scene_class = "BlockchainAnimation"
            self.animator.save("animation_events.json")
            # run the subprocess to render the animation
            subprocess.run(["manim", "-pql", manim_file, scene_class, "-o", "network_activity.mp4"])        

    
    def send_block_to_node(self, sender: NodeBase, recipient: NodeBase, block: BlockBase):
        if not self.set_bandwidth:
            yield self.env.timeout(self.network_topology.get_delay_between_nodes(sender, recipient))
            yield self.input_pipe[recipient.get_node_id()].put((block, sender))
            return

        for _ in range(math.ceil(self.block_size / self.packet_size)):
            with self.bandwidth.request() as req:
                yield req
                # Log if bandwidth was contended for debugging purposes
                if self.bandwidth.count >= self.bandwidth.capacity:
                    print(f"\033[91m[Bandwidth Wait] Node {sender.node_id} waited for bandwidth at time {self.env.now}\033[0m")

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