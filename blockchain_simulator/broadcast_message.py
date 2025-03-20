import hashlib
import json
import time
from typing import Dict, List


class BroadcastMessage:
    def __init__(self, sender: int, data: Dict):
        """
        :param sender
        """
        self.sender = sender
        self.data = data
        self.nodes_visited: List[int] = []
        self.nodes_visited.append(sender)
        self.timestamp = time.time()

    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    def to_dict(self) -> Dict:
        return {
            "sender": self.sender,
            "data": self.data,
            "timestamp": self.timestamp,
        }
        
    async def send_message_to_peers(self, node):
        for peer in node.peers:
            if peer.node_id not in self.nodes_visited:
                delay = node.network.get_network_delay(node, peer)
                node.env.process(self.receive_message_from_peers(peer, delay))
                self.network.metrics["broadcasts"] += 1

    async def receive_message_from_peers(self, node, delay):
        await node.env.timeout(delay)
        self.nodes_visited.append(node.node_id)
        if node.receive_broadcast_message(self):
            self.send_message_to_peers(self,node)
        
class ConsensusBroadcast(BroadcastMessage):
    
    #TODO: Ensure that this class is extendable to more consensus types
    #TODO: Add functionality to drop packets with some probability.
    CONSENSUS_TYPE = {
        'final': 1,
        'tentative': 2,
        'inProgress': 3
    }

    def __init__(self, sender: int, data: Dict):
        super.__init__(sender,data)
