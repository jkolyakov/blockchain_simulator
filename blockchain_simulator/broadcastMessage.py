import hashlib
import json
import time
from typing import Dict, List
from ecdsa import SigningKey, VerifyingKey, NIST256p


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
        self.signature = 123

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    def sign_message(self, private_key: SigningKey) -> str:
        message_hash = self.hash_message()
        signature = private_key.sign(message_hash.encode())
        return signature.hex()

    def hash_message(self) -> str:
        message_content = json.dumps({"sender": self.sender, "data": self.data, "timestamp": self.timestamp}, sort_keys=True)
        return hashlib.sha256(message_content.encode()).hexdigest()

    def to_dict(self) -> Dict:
        return {
            "sender": self.sender,
            "data": self.data,
            "timestamp": self.timestamp,
            "signature": self.signature
        }

    @staticmethod
    def verify_message(message: Dict, public_key: VerifyingKey) -> bool:
        try:
            message_hash = hashlib.sha256(
                json.dumps({"sender": message["sender"], "data": message["data"], "timestamp": message["timestamp"]}, sort_keys=True).encode()
            ).hexdigest()
            signature = bytes.fromhex(message["signature"])
            return public_key.verify(signature, message_hash.encode())
        except Exception as e:
            print(f"Verification failed: {e}")
            return False
        
    def send_message_to_peers(self,node):
        # print(f"Sending message to peers of {node.node_id}")
        for peer in node.peers:
            if peer.node_id not in self.nodes_visited:
                delay = node.network.get_network_delay(node, peer)
                print(f"Node {node.node_id} sending message {self.data['block'].block_id} to {peer.node_id} with delay {delay}")
                node.env.process(self.receive_message_from_peers(peer, delay))
                node.network.metrics["broadcasts"] += 1

    def receive_message_from_peers(self, node, delay):
        yield node.env.timeout(delay)
        self.nodes_visited.append(node.node_id)
        node.receive_message(self)
        self.send_message_to_peers(node)
        
class ConsensusBroadcast(BroadcastMessage):
    
    #TODO: Ensure that this class is extendable to more consensus types
    #TODO: Add functionality to drop packets with some probability.
    CONSENSUS_TYPE = {
        'final': 1,
        'tentative': 2,
        'inProgress': 3
    }
    
    def __init__(self, sender: int, data: Dict):
        super().__init__(sender,data)
