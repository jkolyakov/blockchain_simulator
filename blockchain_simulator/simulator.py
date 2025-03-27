import simpy, random, logging, numpy as np, pandas as pd, matplotlib.pyplot as plt, copy, subprocess, networkx as nx
import random
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from tqdm import tqdm
from typing import Type, Optional, List, Dict, Any, TYPE_CHECKING
if TYPE_CHECKING:
    from blockchain_simulator.node import NodeBase
    from blockchain_simulator.blockchain import BlockchainBase
    from blockchain_simulator.block import BlockBase
    from blockchain_simulator.consensus import ConsensusProtocol, GHOSTProtocol

from blockchain_simulator.broadcast import BroadcastProtocol, GossipProtocol
from blockchain_simulator.block import PoWBlock
from blockchain_simulator.node import BasicNode
from blockchain_simulator.validator import BlockchainValidator  # Import the validator
from blockchain_simulator.visualizer import BlockchainVisualizer
from blockchain_simulator.manim_animator import AnimationLogger
from collections import Counter


def duplicate_stats(lst):
    counts = Counter(lst)
    duplicates = {val: count for val, count in counts.items() if count > 1}
    num_unique_duplicates = len(duplicates)
    total_duplicate_items = sum(count - 1 for count in duplicates.values())
    
    return {
        "unique_duplicates": num_unique_duplicates,
        "total_duplicates": total_duplicate_items,
        "duplicates": duplicates
    }

# Configure logging
logging.basicConfig(filename="blockchain_simulation.log", level=logging.ERROR, format="%(asctime)s - %(message)s", filemode="w")

class BlockchainSimulator:
    """API for running blockchain network simulations with custom implementations."""

    def __init__(
        self,
        num_nodes: int = 10,
        avg_peers: int = 3,
        max_delay: float = 5.0,
        min_delay: float = 0.1,
        consensus_interval: float = 0.1,
        consensus_protocol: Optional[Type['ConsensusProtocol']] = 'GHOSTProtocol',
        blockchain_impl: Optional[Type['BlockchainBase']] = 'BlockchainBase',
        block_class: Optional[Type['BlockBase']] = 'PoWBlock',
        node_class: Type['NodeBase'] = 'BasicNode',
        network_topology: str = "random",
        stakes: Optional[Dict[int, float]] = None,
        drop_rate: int = 0,
        broadcast_protocol: Optional[Type['BroadcastProtocol']] = GossipProtocol,
        interactive_visualization: bool = False,
        num_visualization_nodes: int = 3,
        render_animation: bool = False,
    ):
        """
        Initializes the blockchain simulator.

        :param num_nodes: Number of nodes in the simulation
        :param avg_peers: Average number of peers per node
        :param max_delay: Maximum network delay in seconds
        :param min_delay: Minimum network delay in seconds
        :param consensus_interval: How often consensus is run (in simulation seconds)
        :param consensus_protocol: Consensus protocol class
        :param blockchain_impl: Blockchain implementation class
        :param block_class: Block class
        :param node_class: Node class (default: BasicNode)
        :param network_topology: Network topology type ("random", "ring", "star", "fully_connected")
        :param stakes: Dictionary mapping node_id to stake amount (for PoS protocols)
        """
        self.env: simpy.Environment = simpy.Environment()
        self.num_nodes: int = num_nodes
        self.max_delay: float = max_delay
        self.min_delay: float = min_delay
        self.consensus_interval: int = consensus_interval
        self.consensus_protocol: Optional['ConsensusProtocol'] = consensus_protocol() if consensus_protocol else None
        self.genesis_block: 'BlockBase' = block_class(parent=None, miner_id=-1, timestamp=0) if block_class else None
        self.network_topology: str = network_topology
        self.stakes: Dict[int, float] = stakes or {i: 1.0 for i in range(num_nodes)}
        self.drop_rate: int = drop_rate
        self.interactive_visualization: bool = interactive_visualization
        self.num_visualization_nodes: int = num_visualization_nodes
        self.animator: AnimationLogger = AnimationLogger()
        
        # Ensure proper delay matrix setup
        self.delay_matrix = self._generate_symmetric_delay_matrix()
        # Initialize metrics dictionary
        self.metrics: Dict[str, Any] = {
            "total_blocks_mined": 0,
            "blocks_by_node": {i: 0 for i in range(num_nodes)},
            "block_propagation_times": [],
            "consensus_executions": 0,
            "forks": 0,
            "broadcasts": 0,
            "chain_lengths": [],
            "fork_counts": [],
            "block_validation_results": [],
            "chain_convergence": [],
            "orphaned_blocks": [],
            "PoW_nonces": [],
            "dropped_blocks": 0,
        }
        
        # Create nodes
        self.nodes: List['NodeBase'] = [
            node_class(self.env, i, self, self.consensus_protocol, blockchain_impl(block_class, genesis_block=copy.deepcopy(self.genesis_block)), broadcast_protocol)
            for i in range(num_nodes)
        ]
        
        # Create network topology
        self._create_network_topology() # TODO: Make this extendable
        
        self._visualize_network_topology(self.nodes)
        
        # Initialize validator
        self.validator = BlockchainValidator(self)
        self.render_animation = render_animation
        
        # Set the animator properties
        self.animator.set_num_nodes(self.num_nodes)
        self.animator.set_peers({n.node_id: [p.node_id for p in n.peers] for n in self.nodes})
        
    
    def _generate_symmetric_delay_matrix(self) -> np.ndarray:
        """
        Generates a symmetric delay matrix ensuring network latency is bidirectional.
        
        :return: A symmetric matrix with delays between nodes.
        """
        return [[random.uniform(self.min_delay, self.max_delay) for _ in range(self.num_nodes)] 
            for _ in range(self.num_nodes)]
        
    def _visualize_network_topology(self, nodes: List['NodeBase']) -> None:
        """
        Visualizes the peer-to-peer network topology.

        :param nodes: List of Node objects (each must have a `node_id` and `peers` attribute)
        """
        G = nx.Graph()

        # Add nodes
        for node in nodes:
            G.add_node(node.node_id)

        # Add edges (peer connections)
        for node in nodes:
            for peer in node.peers:
                G.add_edge(node.node_id, peer.node_id)  # Undirected edge

        # Draw the network
        plt.figure(figsize=(10, 6))
        pos = nx.spring_layout(G, seed=42)  # Layout for better visualization
        nx.draw(G, pos, with_labels=True, node_size=800, node_color="lightblue", edge_color="gray", font_size=10)

        plt.title("Blockchain Network Topology")
        plt.show()

    def _create_network_topology(self):
        """Creates the network topology based on the specified type."""
        if self.network_topology == "random":
            self._create_random_topology()
        elif self.network_topology == "ring":
            self._create_ring_topology()
        elif self.network_topology == "star":
            self._create_star_topology()
        elif self.network_topology == "fully_connected":
            self._create_fully_connected_topology()
        else:
            raise ValueError(f"Unknown network topology: {self.network_topology}")

    def _create_random_topology(self):
        """Creates a random network topology where each node has a random number of peers."""
        for i, node in enumerate(self.nodes):
            # Determine number of peers for this node
            num_peers = min(random.randint(0, int(self.num_nodes/2)), self.num_nodes - 1)
            
            # Select random peers
            possible_peers = [n for n in self.nodes if n.node_id != i]
            selected_peers = random.sample(possible_peers, num_peers)
            
            # Connect peers bidirectionally
            for peer in selected_peers:
                node.add_peer(peer)
                peer.add_peer(node)

    def _create_ring_topology(self):
        """Creates a ring topology where each node is connected to its neighbors."""
        for i, node in enumerate(self.nodes):
            next_idx = (i + 1) % self.num_nodes
            prev_idx = (i - 1) % self.num_nodes
            
            node.add_peer(self.nodes[next_idx])
            node.add_peer(self.nodes[prev_idx])

    def _create_star_topology(self):
        """Creates a star topology with one central node connected to all others."""
        central_node = self.nodes[0]
        
        # Connect all nodes to the central node
        for i, node in enumerate(self.nodes):
            if i != 0:  # Skip the central node itself
                node.add_peer(central_node)
                central_node.add_peer(node)

    def _create_fully_connected_topology(self):
        """Creates a fully connected network where every node is connected to every other node."""
        for i, node in enumerate(self.nodes):
            for j, peer in enumerate(self.nodes):
                if i != j:  # Don't connect to self
                    node.add_peer(peer)

    def get_network_delay(self, from_node: 'BasicNode', to_node: 'BasicNode') -> float:
        """Get the network delay between two nodes."""
        return float(self.delay_matrix[from_node.node_id][to_node.node_id])  # Use list-of-lists indexing


    def start_mining(self, num_miners: Optional[int] = None) -> None:
        """
        Triggers mining for num_miners randomly selected nodes.

        :param num_miners: Total miners to be randomly selected. All nodes mine if None.
        """
        
        if num_miners is None:
            node_ids = list(range(self.num_nodes))
        else:
            assert num_miners <= self.num_nodes, "Number of miners cannot exceed the number of nodes"
            node_ids = random.sample(range(self.num_nodes), num_miners) 
        
        for node_id in node_ids:
            if 0 <= node_id < self.num_nodes:
                self.nodes[node_id].start_mining()
        
    def stop_mining(self, node_ids: Optional[List[int]] = None) -> None:
        """
        Stops mining at specified nodes or all nodes if not specified.

        :param node_ids: List of node IDs to stop mining, or None for all nodes.
        """
        if node_ids is None:
            node_ids = list(range(self.num_nodes))
        
        for node_id in node_ids:
            if 0 <= node_id < self.num_nodes:
                self.nodes[node_id].stop_mining()

    def run(self, duration: int = 100, collect_interval: int = 5) -> Dict[str, Any]:
        """
        Runs the simulation for a given duration and returns the metrics.

        :param duration: Duration of the simulation in seconds.
        :param collect_interval: Interval for collecting metrics.
        :return: Dictionary containing all collected metrics.
        """
        print(f"🚀 Running blockchain simulation for {duration} seconds...\n")
        
        # Setup metrics collection process
        self.env.process(self._collect_metrics(collect_interval))
        
        # Run the simulation
        # Create a progress bar
        with tqdm(total=duration, desc="⏳ Simulation Progress", unit="s", ascii=" ▖▘▝▗▚▞█") as pbar:
            last_time = self.env.now 
            while self.env.now < duration:
                self.env.step()          
                # Update pbar with the actual time that has passed
                time_advanced = self.env.now - last_time
                pbar.update(time_advanced)
                last_time = self.env.now  # Update last_time to current

            # Stop mining at all nodes
            for node in self.nodes:
                node.stop_mining()
            
        # Collect final metrics
        self._collect_final_metrics()
        
        # Display results
        self.display_metrics()
        
        # for node in self.nodes:
        #     print(f"Node {node.node_id} has {len(node.blockchain.blocks)} blocks")
        #     self._print_blockchain_tree(node)
        
        
        if self.render_animation:
            manim_file = "./blockchain_simulator/manim_animator.py"
            scene_class = "BlockchainAnimation"
            self.animator.save("animation_events.json")
            # run the subprocess to render the animation
            subprocess.run(["manim", "-pqh", manim_file, scene_class, "-o", "network_activity.mp4"])        
            
        # Validate the simulation
        validation_results = self.validate_simulation()
        
        # Visualize the blockchain tree for a random set of nodes based on 
        if self.interactive_visualization:
            sample_nodes = random.sample(self.nodes, min(self.num_nodes, self.num_visualization_nodes))
            for node in sample_nodes:
                visualizer = BlockchainVisualizer(node, output_path=f"visualizations/{node.node_id}_blockchain_interactive.html")
                visualizer.draw_interactive()
        
        # Return metrics for further analysis
        return {
            "metrics": self.metrics,
            "validation": validation_results
        }

    def _collect_metrics(self, interval: int):
        """
        Collects metrics at regular intervals during the simulation.

        :param interval: Interval in seconds between metrics collection.
        """
        while True:
            # Collect chain lengths
            chain_lengths = [node.consensus_protocol.chain_length(node) for node in self.nodes]
            self.metrics["chain_lengths"] = chain_lengths
            
            # Collect orphaned blocks
            orphaned_blocks = [self.consensus_protocol.count_orphaned_blocks(node) for node in self.nodes]
            self.metrics["orphaned_blocks"] = orphaned_blocks
            
            # Count forks
            self.metrics["fork_counts"].append(self._count_forks())
            
            # Wait for the next collection interval
            yield self.env.timeout(interval)

    def _collect_final_metrics(self):
        """Collects final metrics at the end of the simulation."""
        # Count orphaned blocks        
        for node in self.nodes:
            # Collect PoW nonces for PoW-based simulations
            if node.blockchain.blocks and isinstance(next(iter(node.blockchain.blocks.values())), PoWBlock):
                pow_nonces = [block.nonce for block in node.blockchain.blocks.values() if block.nonce is not None]
                average_nonce = sum(pow_nonces) / len(pow_nonces) if pow_nonces else 0
                self.metrics["PoW_nonces"].append(average_nonce)
        
        # Measure chain convergence (% of nodes that agree on the main chain)
        self.metrics["chain_convergence"].append(self._measure_convergence())

    def _print_blockchain_tree(self, node: Optional['NodeBase']):
        """Selects a random node and prints its blockchain in tree format."""
        if not self.nodes:
            print("No nodes in the network.")
            return

        # Randomly select a node
        # node = random.choice(self.nodes)
        if node is None:
            node = self.nodes[0]  # Select the first node for consistency
        print(f"\n📜 Blockchain Tree for Node {node.node_id}\n")
        print(f"\033[94m{'Blue is the main chain'}\033[0m")

        # Get all block_ids on the main chain
        main_chain_ids = set()
        current = node.blockchain.head
        while current:
            main_chain_ids.add(current.block_id)
            current = current.parent
            
        def print_tree(block: 'BlockBase', indent=0):
            """Recursive function to print the blockchain tree structure."""
            prefix = "    " * indent
            block_str = f"🔗 Block {block.block_id} (Miner: {block.miner_id}, Weight: {block.weight})"
            if block.block_id in main_chain_ids:
                block_str = f"\033[94m{block_str}\033[0m"  # Blue highlight
            print(prefix + block_str)
            for child in sorted(block.children, key=lambda b: b.block_id):
                print_tree(child, indent + 1)

        # Start printing from the genesis block
        print_tree(node.blockchain.genesis)

    def display_metrics(self) -> None:
        """
        Prints a summary of blockchain metrics after the simulation.
        """
        print("\n📊 Blockchain Simulation Summary")
        print("-" * 60)
        print(f"🔹 Total Blocks Mined: {self.metrics['total_blocks_mined']}")
        print(f"🔹 Blocks Mined by Node: ")
        for node_id, blocks_mined in self.metrics["blocks_by_node"].items():
            print(f"   Node {node_id}: {blocks_mined}")
        
        if self.metrics["block_propagation_times"]:
            avg_prop_time = sum(self.metrics["block_propagation_times"]) / len(self.metrics["block_propagation_times"])
            print(f"🔹 Average Block Propagation Time: {avg_prop_time:.2f} seconds")
        
        print(f"🔹 Consensus Executions: {self.metrics['consensus_executions']}")
        print(f"🔹 Fork Resolutions: {self.metrics['forks']}")
        print(f"🔹 Longest Chain Length: {max(self.metrics['chain_lengths'])}")
        
        # Calculate average number of orphaned blocks
        if self.metrics["orphaned_blocks"]:
            avg_orphaned = sum(self.metrics["orphaned_blocks"]) / len(self.metrics["orphaned_blocks"])
            print(f"🔹 Average Orphaned Blocks: {avg_orphaned:.2f}")
        
        # Calculate average chain length
        if self.metrics["chain_lengths"]:
            avg_chain_length = sum(self.metrics["chain_lengths"]) / len(self.metrics["chain_lengths"])
            print(f"🔹 Average Chain Length: {avg_chain_length:.2f}")
            # display each node's chain length and the head of each chain
            for node_id, chain_length in enumerate(self.metrics["chain_lengths"]):
                print(f"   Node {node_id}: {chain_length}. Head: {self.nodes[node_id].blockchain.head.block_id}")
        
        # Calculate average PoW nonce
        if self.metrics["PoW_nonces"]:
            avg_nonce = sum(self.metrics["PoW_nonces"]) / len(self.metrics["PoW_nonces"])
            print(f"🔹 Average PoW Nonce: {avg_nonce:.2f}")
            
        if self.metrics["dropped_blocks"]:
            avg_dropped = self.metrics["dropped_blocks"] / self.num_nodes
            print(f"🔹 Average dropped blocks: {avg_dropped:.2f}")
        
        if self.metrics["chain_convergence"]:
            head_id, convergence_percentage = self.metrics["chain_convergence"][0]
            print(f"🔹 Chain Convergence: {convergence_percentage:.2%} (Head: {head_id})")
        
        print("-" * 60)
        # self._print_blockchain_tree()   
                 
    def validate_simulation(self) -> Dict[str, Dict[str, Any]]:
        """
        Validates the simulation using the BlockchainValidator.
        
        :return: Dictionary containing validation results.
        """
        return self.validator.validate_all()
    
    def _count_forks(self) -> int:
        """
        Count the number of fork points in the blockchain.
        Uses the validator's method.
        
        :return: Number of forks.
        """
        return self.validator._count_forks()
    
    def _measure_convergence(self) -> float:
        """
        Measure the percentage of nodes that agree on the same chain.
        Uses the validator's method.
        
        :return: Convergence percentage (0.0-1.0).
        """
        return self.validator._measure_convergence()