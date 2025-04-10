# Blockchain Simulator
A python-based blockchain simulation framework for testing and analyzing different consensus protocols and network configurations.

## 🚀 Features

- Supports **Proof-of-Work (PoW)** and **Proof-of-Stake (PoS)** consensus mechanisms.   *(Extendable)*
- Supports **custom network topologies** (random, ring, star, fully connected). *(Extendable)*
- Implements **GHOST protocol**. *(Extendable)*
- Tracks **block propagation times**, **fork resolutions**, and **chain convergence**.
- Simulates **mining**, **block validation**, and **consensus execution**.
- Provides **visual blockchain trees** and **detailed metrics**.
  

## 📦 Installation

Via package

```bash
npm install blockchain-simulator
```

Via cloning the repo

## 📦 Installation

The recommended way to install ``blockchain_simulator`` is to grab the latest release from PyPI:

```
pip install blockchain_simulator
```

Building the latest nightly version of this repository is also possible. Ensure you have **Python 3.11+** installed. Then, clone this repository and install the required dependencies:

```sh
# Clone the repo
git clone https://github.com/your-repo/blockchain-simulator.git

# Enter the repo's root directory
cd blockchain-simulator

# Install required dependencies and packafge
pip install -r requirements.txt
pip install -e . 
```

## Usage

An example is provided in ``blockchain_simulator/examples/run_simulations.py``. Once the simulation completes, the stats for the simulated run are displayed and the animation rendering module will start. 

