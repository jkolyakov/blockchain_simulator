import networkx as nx
import plotly.graph_objects as go
from typing import Dict, Optional
from blockchain_simulator.block import BlockBase
from blockchain_simulator.node import NodeBase
import os
import math

MIN_NODE_SIZE = 1
MAX_NODE_SIZE = 40  # Adjust as needed

class BlockchainVisualizer:
    """Interactive Blockchain Visualization using Plotly & NetworkX"""

    def __init__(self, node: NodeBase, output_path: str = "blockchain_graph.html"):
        self.node = node  # The node whose blockchain will be visualized
        self.output_path = output_path  # Default output path for the exported file
        self._ensure_output_directory()
        
    def _ensure_output_directory(self):
        """Creates the directory for output_path if it doesn't exist."""
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        
    def build_graph(self) -> nx.DiGraph:
        """Creates a directed graph of the blockchain."""
        G = nx.DiGraph()
        blocks: Dict[int, BlockBase] = self.node.blockchain.blocks

        for block in blocks.values():
            G.add_node(block.block_id, miner=block.miner_id, weight=block.weight)
            if block.parent:
                G.add_edge(block.parent.block_id, block.block_id)

        return G

    def find_main_chain(self) -> set:
        """Finds the main chain by backtracking from the current head."""
        main_chain = set()
        block = self.node.blockchain.head
        while block:
            main_chain.add(block.block_id)
            block = block.parent  # Move up the chain
        return main_chain
    
    # Normalize block weight scaling using log (to prevent massive node size jumps)
    def scale_node_size(self, weight):
        return MIN_NODE_SIZE + (MAX_NODE_SIZE - MIN_NODE_SIZE) * (math.log1p(weight) / math.log1p(max(1, weight)))

    def hierarchy_pos(self, G: nx.DiGraph, root=None, width=1., vert_gap=0.2, xcenter=0.5, pos=None, level=0, parent=None):
        """Generates hierarchical positions for nodes in a directed graph.
           - Ensures children are in a straight row at each level.
           - Dynamically calculates spacing based on number of children.
        """
        if pos is None:
            pos = {root: (xcenter, 1)}
        else:
            pos[root] = (xcenter, 1 - level * vert_gap)

        children = list(G.successors(root))
        num_children = len(children)

        if not children:
            return pos
    
        # Dynamically calculate horizontal spacing
        x_spacing = width / max(1, num_children)  
        next_x = xcenter - (width / 2) + (x_spacing / 2)  

        for child in children:
            pos = self.hierarchy_pos(G, root=child, width=x_spacing, vert_gap=vert_gap, xcenter=next_x, pos=pos, level=level + 1, parent=root)
            next_x += x_spacing  

        return pos

    def draw_interactive(self):
        """Creates an interactive blockchain visualization using Plotly."""
        G = self.build_graph()
        main_chain = self.find_main_chain()
        root_block = self.node.blockchain.genesis.block_id  # Genesis as root
        pos = self.hierarchy_pos(G, root=root_block)

        # Extract min/max positions to expand axis range dynamically
        all_x, all_y = zip(*pos.values())
        x_range = (min(all_x) - 0.1, max(all_x) + 0.1)
        y_range = (min(all_y) - 0.1, max(all_y) + 0.1)
        
        # Separate edges into main chain and orphan edges
        main_edge_x, main_edge_y = [], []
        orphan_edge_x, orphan_edge_y = [], []

        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]

            if edge[0] in main_chain and edge[1] in main_chain:
                main_edge_x.extend([x0, x1, None])
                main_edge_y.extend([y0, y1, None])
            else:
                orphan_edge_x.extend([x0, x1, None])
                orphan_edge_y.extend([y0, y1, None])

        # Main chain edges trace
        main_edge_trace = go.Scatter(
            x=main_edge_x, y=main_edge_y,
            line=dict(width=1.5, color="blue"),
            hoverinfo="none",
            mode="lines",
            name="Main Chain Links"
        )

        # Orphan edges trace
        orphan_edge_trace = go.Scatter(
            x=orphan_edge_x, y=orphan_edge_y,
            line=dict(width=1.5, color="red"),
            hoverinfo="none",
            mode="lines",
            name="Orphan Links",
            visible=True
        )

        # Separate node data into main chain and orphan blocks
        main_x, main_y, orphan_x, orphan_y = [], [], [], []
        main_text, orphan_text = [], []
        main_size, orphan_size = [], []

        for node in G.nodes():
            x, y = pos[node]
            block = self.node.blockchain.blocks[node]

            if node in main_chain:
                main_x.append(x)
                main_y.append(y)
                main_text.append(f"Block ID: {block.block_id}<br>Miner: {block.miner_id}<br>Weight: {block.weight}")
                main_size.append(self.scale_node_size(block.weight))  # Size based on weight
            else:
                orphan_x.append(x)
                orphan_y.append(y)
                orphan_text.append(f"Block ID: {block.block_id}<br>Miner: {block.miner_id}<br>Weight: {block.weight}")
                orphan_size.append(self.scale_node_size(block.weight))

        # Main chain node trace (blue)
        main_chain_trace = go.Scatter(
            x=main_x, y=main_y,
            mode="markers",
            marker=dict(size=main_size, color="blue", line=dict(width=2, color="black")),
            text=main_text,
            hoverinfo="text",
            name="Main Chain Block"
        )

        # Orphan blocks trace (red)
        orphan_trace = go.Scatter(
            x=orphan_x, y=orphan_y,
            mode="markers",
            marker=dict(size=orphan_size, color="red", line=dict(width=2, color="black")),
            text=orphan_text,
            hoverinfo="text",
            name="Orphan Block",
            visible=True
        )

        # Create figure with updated legend
        fig = go.Figure(data=[main_edge_trace, orphan_edge_trace, main_chain_trace, orphan_trace])

        fig.update_layout(
            title=f"Blockchain Visualization - Node {self.node.node_id}",
            title_x=0.5,
            showlegend=True,
            width=1800,  # Increase width for horizontal scrolling
            height=1000,  # Increase height for vertical scrolling
            autosize=False,
            legend=dict(
                x=1.05,
                y=1.0,
                xanchor="left",
                yanchor="top",
                bgcolor="rgba(255,255,255,0.8)"
            ),
            hovermode="closest",
            margin=dict(b=50, l=50, r=250, t=50),
            xaxis=dict(
                showgrid=False, zeroline=False, showticklabels=False,
                range=x_range,  # Expand range
                fixedrange=True  # Enable zoom & scroll
            ),
            yaxis=dict(
                showgrid=False, zeroline=False, showticklabels=False,
                range=y_range,  # Expand range
                fixedrange=True  # Enable zoom & scroll
            ),
            dragmode=False  # Disable panning outside the box
        )


        # Save and display the interactive visualization
        fig.write_html(self.output_path)
        print(f"✅ Blockchain visualization saved: {self.output_path}")
        fig.show()