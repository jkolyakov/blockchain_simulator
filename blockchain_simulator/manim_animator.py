from manim import *
from typing import List, Dict, Tuple, Any
import json
import numpy as np
from tqdm import tqdm


class AnimationLogger:
    def __init__(self):
        self.events: List[Tuple[float, str]] = []
        self.num_nodes: int = 0
        self.peers: Dict[int, List[int]] = {}

    def log_event(self, message: str, timestamp: float):
        self.events.append((timestamp, message))

    def set_num_nodes(self, num_nodes: int):
        self.num_nodes = num_nodes

    def set_peers(self, peers: Dict[int, List[int]]):
        self.peers = peers

    def save(self, filepath: str = "animation_events.json"):
        with open(filepath, "w") as f:
            json.dump({
                "num_nodes": self.num_nodes,
                "events": self.events,
                "peers": self.peers,
            }, f, indent=2)

# ======================
# Node + Edge Classes
# ======================

class BlockchainNode:
    def __init__(self, node_id: int, position: np.ndarray):
        # Initialize position, circle, and label for the node
        self.id = node_id
        self.position = position
        self.circle = Circle(radius=0.4, color=WHITE, fill_opacity=0.3).shift(position)
        self.label = Text(f"{node_id}", font_size=24).move_to(self.position)

    def get_objects(self) -> List[Mobject]:
        # Return node visuals (circle + label)
        return [self.circle, self.label]

    def pulse(self, color=YELLOW) -> Animation:
        # Return a pulsing animation (e.g., mining or adding)
        return Succession(
            AnimationGroup(self.circle.animate.set_fill(color, 1).scale(1.2)),
            AnimationGroup(self.circle.animate.set_fill(WHITE, 0.3).scale(1)),
            run_time=1
        )

class BlockchainEdge:
    def __init__(self, start_node: BlockchainNode, end_node: BlockchainNode):
        # Initialize an edge (line) between two nodes
        self.start_node = start_node
        self.end_node = end_node
        self.line = Line(start_node.position, end_node.position, stroke_opacity=0.3)
        pass

    def get_object(self) -> Mobject:
        # Return the line object for rendering
        return self.line


# ======================
# Network Visualizer
# ======================

class BlockchainVisualizer:
    def __init__(self):
        # Store nodes and edges
        self.nodes: Dict[int, BlockchainNode] = {}
        self.edges: Dict[Tuple[int, int], BlockchainEdge] = {}
        pass

    def build_network(self, num_nodes: int, peers: Dict[int, List[int]], radius: float = 3):
        # Create BlockchainNode and BlockchainEdge objects based on topology
        for i in range(num_nodes):
            angle = i * 2 * np.pi / num_nodes
            position = radius * np.array([np.cos(angle), np.sin(angle), 0]) + DOWN * 0.5
            self.nodes[i] = BlockchainNode(i, position)
        
        # Create edges based on peer connections
        for node_id_str, connected_nodes in peers.items():
            node_id = int(node_id_str)
            for connected_node in connected_nodes:
                # Create a unique identifier for the edge
                edge_id = tuple(sorted([node_id, connected_node]))
                if edge_id not in self.edges:
                    self.edges[edge_id] = BlockchainEdge(
                        self.nodes[node_id], 
                        self.nodes[connected_node]
                    )
        pass

    def get_all_objects(self) -> List[Mobject]:
        # Return all visual components (nodes and edges)
        objects = []
        for edge in self.edges.values():
            objects.append(edge.get_object())
        for node in self.nodes.values():
            objects.extend(node.get_objects())
        return objects
        pass


# ======================
# Animation Controller
# ======================

class BlockchainAnimation(Scene):
    def setup_from_json(self, json_path: str) -> Tuple[List[Tuple[float, str]], float, float]:
        # Load animation_events.json and extract:
        # - events: List of (timestamp, message)
        # - start_time and end_time
        # - build network and timeline
        with open(json_path, "r") as f:
            data = json.load(f)
            events = data["events"]
            num_nodes = data["num_nodes"]
            peers = data["peers"]
        
        self.visualizer = BlockchainVisualizer()
        self.node_blocks: Dict[Tuple[int, str], Mobject] = {}
        self.visualizer.build_network(num_nodes, peers)
        
        return events

    def parse_event(self, event_text: str) -> Tuple[str, Dict[str, Any]]:
        # Parse an event string into (event_type, parameters)
        # e.g., ("mined", {"node_id": 1, "block_id": "xyz"})
        if "mined block" in event_text:
            parts = event_text.split()
            node_id = int(parts[1])
            block_id = parts[-1]
            return "mined", {"node_id": node_id, "block_id": block_id}
            
        elif "added block" in event_text:
            parts = event_text.split()
            node_id = int(parts[1])
            block_id = event_text.split("Block(id=")[1].split(",")[0]
            return "added", {"node_id": node_id, "block_id": block_id}
            
        elif "broadcasting block" in event_text:
            parts = event_text.split()
            source_node = int(parts[1])
            targets_json = event_text.split("to ")[-1]
            targets = eval(targets_json)  # [(3, False, False), (4, True, True), ...] (node_id, dropped, duplicate)
            block_info = event_text.split("Block(")[1].split(")")[0]
            return "broadcast", {
                "source_node": source_node,
                "targets": targets,
                "block_info": block_info
            }
        
        # TODO: Parse and implement discarding duplicate blocks (e.g. already in blockchain upon receipt. It's already being logged)
        
        # Default case
        return "unknown", {"text": event_text}

    def create_mining_animation(self, params: Dict[str, Any]) -> Animation:
        # Return animation for mining (pulse + block pop-up)
        node_id = params["node_id"]
        block_id = params["block_id"]
        node = self.visualizer.nodes[node_id]
        
        # Block setup: start at center of node
        block = Square(side_length=0.25, color=YELLOW).move_to(node.position + UP * 0.6).set_opacity(0)
        block_text = Text(f"B{block_id[-4:]}", font_size=14).next_to(block, UP, buff=0.1).set_opacity(0)
        
        self.node_blocks[(node_id, block_id)] = block # Store block for future reference
        
        mining_animation = Succession(
            AnimationGroup(node.circle.animate.set_fill(BLUE, 1).scale(1.2), 
                           ApplyMethod(block.set_opacity, 1),
                           ApplyMethod(block_text.set_opacity, 1),
                           lag_ratio=0.5,
                           ),
            AnimationGroup(node.circle.animate.set_fill(WHITE, 0.3).scale(1), 
                           block.animate.shift(DOWN * 0.6),
                           block_text.animate.shift(DOWN * 0.6),
                           ),
        )
        return mining_animation, AnimationGroup(ApplyMethod(block.set_fill, block.get_color(), 0), ApplyMethod(block.set_opacity, 0.8))
    
    def create_block_added_animation(self, params: Dict[str, Any]) -> Animation:
        # Return animation for block being accepted into the chain
        node_id = params["node_id"]
        block_id = params["block_id"]
        node = self.visualizer.nodes[node_id]
        
        key = (node_id, block_id)
        if key not in self.node_blocks: # TODO: Need to handle getting parent blocks as well so that the block object will exist
            return None, None  # Or handle missing case
        
        block = self.node_blocks[key]
        
        adding_animation = Succession(
            AnimationGroup(node.circle.animate.set_fill(GREEN, 1).scale(1.2),
                           ApplyMethod(block.set_color, GREEN)),
            AnimationGroup(node.circle.animate.set_fill(WHITE, 0.3).scale(1), 
                           ShrinkToCenter(block), lag_ratio=0.5),
        run_time = 1)
        return adding_animation, None

    def create_broadcasting_animation(self, params: Dict[str, Any]) -> Animation:
        source_node = self.visualizer.nodes[params["source_node"]]
        block_id = params["block_info"].split(",")[0].split("=")[-1]
        anims = []

        for target_id, dropped, duplicate in params["targets"]:
            edge_key = tuple(sorted((source_node.id, target_id)))
            edge = self.visualizer.edges[edge_key].line
            
            target_node = self.visualizer.nodes[target_id]
            if dropped:
                color = RED
            elif duplicate:
                color = ORANGE
            else:
                color = YELLOW
            
            block = Square(0.2, color=color).move_to(source_node.position).set_opacity(0)
            message = Circle(radius=0.1, color=color).move_to(block.get_center()).set_opacity(0)
            block_text = Text(f"B{block_id[-4:]}", font_size=14).next_to(message, UP, buff=0.15).set_opacity(0)
            # Add an updater to keep opacity = 1 during movement
            def keep_visible(mobj: VMobject):
                mobj.set_opacity(1)
            message.add_updater(keep_visible)
            block_text.add_updater(keep_visible)
            if dropped:
                mid = (source_node.position + target_node.position) / 2
                anims.append(
                    Succession(
                        AnimationGroup(
                            ApplyMethod(block.set_opacity, 1),
                            ApplyMethod(block_text.set_opacity, 1),
                            ApplyMethod(message.set_opacity, 1),
                            edge.animate.set_stroke(color = RED_D, opacity=1.0, width=4),
                        ),
                        AnimationGroup(
                            ReplacementTransform(block, message),
                            ApplyMethod(block.set_opacity, 0),
                            run_time=1
                        ),
                        AnimationGroup(
                            message.animate.move_to(mid),
                            block_text.animate.move_to(mid + UP * 0.15),
                            run_time=3
                        ),
                        AnimationGroup(
                            ShrinkToCenter(message),
                            ShrinkToCenter(block_text),
                            # message.animate.move_to(mid + DOWN * 0.2),
                            # block_text.animate.move_to(mid + DOWN * 0.2 + 0.15 * UP),
                            run_time=1
                        ),
                        AnimationGroup(
                            FadeOut(message),
                            FadeOut(block_text),
                            edge.animate.set_stroke(color = WHITE, opacity=0.3, width=2),
                        )
                    )
                )
            elif duplicate:
                duplicate_block = Square(0.2, color=ORANGE).move_to(target_node.position).set_opacity(0)
                duplicate_block_text = Text(f"D", font_size=14).move_to(duplicate_block.get_center()).set_opacity(0)
                anims.append(Succession(
                        AnimationGroup(
                            ApplyMethod(block.set_opacity, 1),
                            ApplyMethod(block_text.set_opacity, 1),
                            ApplyMethod(message.set_opacity, 1),
                            edge.animate.set_stroke(color = ORANGE, opacity=1.0, width=4),
                        ),
                        AnimationGroup(
                            ReplacementTransform(block, message),
                            ApplyMethod(block.set_opacity, 0),
                            run_time=1
                        ),
                        AnimationGroup(
                            message.animate.move_to(target_node.position),
                            block_text.animate.move_to(target_node.position + UP * 0.15),
                            run_time=3
                        ),
                        AnimationGroup(
                            target_node.circle.animate.set_fill(RED_D, 1).scale(1.2),
                            ReplacementTransform(message, duplicate_block),
                            ApplyMethod(duplicate_block.set_opacity, 1),
                            ApplyMethod(duplicate_block_text.set_opacity, 1),
                            edge.animate.set_stroke(color = WHITE, opacity=0.3, width=2),
                        ),
                        AnimationGroup(
                            target_node.circle.animate.set_fill(WHITE, 0.3).scale(1),
                            duplicate_block.animate.move_to(target_node.position + DOWN),
                            duplicate_block_text.animate.move_to(duplicate_block.get_center() + DOWN),
                            block_text.animate.move_to(target_node.position + DOWN + 0.2 * UP),
                            run_time=1
                        ),
                        AnimationGroup(
                            FadeOut(duplicate_block),
                            FadeOut(duplicate_block_text),
                            FadeOut(block_text),
                        )
                    ))
            else:
                final_block = Square(0.2, color=YELLOW).move_to(target_node.position).set_opacity(0)
                self.node_blocks[(target_id, block_id)] = final_block # Store block for future reference
                anims.append(
                    Succession(
                        AnimationGroup(
                            ApplyMethod(block.set_opacity, 1),
                            ApplyMethod(block_text.set_opacity, 1),
                            ApplyMethod(message.set_opacity, 1),
                            edge.animate.set_stroke(color = BLUE_D, opacity=1.0, width=4),
                        ),
                        AnimationGroup(
                            ReplacementTransform(block, message),
                            ApplyMethod(block.set_opacity, 0),
                            run_time=1
                        ),
                        AnimationGroup(
                            message.animate.move_to(target_node.position),
                            block_text.animate.move_to(target_node.position + UP * 0.15),
                            run_time=3
                        ),
                        AnimationGroup(
                            ReplacementTransform(message, final_block),
                            ApplyMethod(final_block.set_opacity, 1),
                            ApplyMethod(block_text.set_opacity, 0),
                            ApplyMethod(message.set_opacity, 0),
                            edge.animate.set_stroke(color = WHITE, opacity=0.3, width=2),
                        )
                    )
                )
            # Remove updater after animation
            block.remove_updater(keep_visible)
            message.remove_updater(keep_visible)
            block_text.remove_updater(keep_visible)
        if len(anims) == 0:
            return None
        return AnimationGroup(*anims, lag_ratio=0)

    def construct(self, max_timestep=100):
        # Entry point:
        # - Load events
        # - Add visuals (nodes, edges, timeline)
        # - Play animations in order with delay/timeline update
        # max_timestep: maximum number of timesteps to animate
        events = self.setup_from_json("animation_events.json")
        title = Text("Blockchain Network Animation", font_size=36).to_edge(UP)
        self.add(title)
        for obj in self.visualizer.get_all_objects():
            self.add(obj)
            
        # Store all animations
        current_time = 0
        animations = []
        
        # Play animations based on events
        timestep_counter = 0
        for timestamp, event in tqdm(events):
            timestep_counter += 1
            print(timestamp, event)
            delay = timestamp - current_time
            if timestep_counter > max_timestep:
                break
            if delay > 0:
                # animations.append(Wait(delay))
                pass
                
            current_time = timestamp
            event_type, params = self.parse_event(event)
            if event_type == "mined":
                animation, cleanup = self.create_mining_animation(params)
                # Encapsulate add+animation into a sequence
                group = animation
                if cleanup is not None:
                    group = Succession(group, cleanup, run_time = 2)
            elif event_type == "added":
                animation, cleanup = self.create_block_added_animation(params)
                if animation is None:
                    continue
                group = animation
                if cleanup is not None:
                    group = Succession(animation, cleanup, run_time = 2)
            elif event_type == "broadcast":
                animation = self.create_broadcasting_animation(params)
                if animation is None:
                    continue
                group = animation
            else:
                continue
            animations.append(group)
        print(len(animations))
        self.play(Succession(*animations, run_time=120))