import hashlib
import json
import time
from typing import Dict
from ecdsa import SigningKey, VerifyingKey, NIST256p


class BroadcastMessage:
    def __init__(self, sender: int, data: Dict, private_key: SigningKey):
        """
        :param sender
        """
        self.sender = sender
        self.data = data
        self.timestamp = time.time()
        self.signature = self.sign_message(private_key)

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
