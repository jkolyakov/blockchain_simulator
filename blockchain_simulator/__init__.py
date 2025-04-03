from blockchain_simulator.block import  PoWBlock
from blockchain_simulator.blockchain import Blockchain
from blockchain_simulator.node import Node
from blockchain_simulator.simulator import BlockchainSimulator
from blockchain_simulator.consensus import GHOSTProtocol
from blockchain_simulator.network_topology import SimpleRandomTopology, StarTopology, FullyConnectedTopology, RingTopology
from blockchain_simulator.broadcast import GossipProtocol


from importlib.metadata import version, PackageNotFoundError
from blockchain_simulator._metadata import (
    __author__,
    __email__,
    __license__,
    __url__,
    __description__,
)

try:
    __version__ = version("blockchain_simulator")  
except PackageNotFoundError:
    __version__ = "unknown"