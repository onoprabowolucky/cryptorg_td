# cryptorg_td: Cross-Chain Bridge Event Listener Simulation

This repository contains a Python script that simulates the core logic of an event listener for a cross-chain bridge. This component is crucial for the interoperability of decentralized applications, allowing for the transfer of assets or data between different blockchains.

This script is designed as an architectural blueprint, demonstrating best practices such as modular design, asynchronous processing, state management, and robust error handling.

---

## Concept

A cross-chain bridge allows users to "move" assets from a source chain (e.g., Ethereum) to a destination chain (e.g., Polygon). The typical mechanism is **Lock & Mint**:

1.  **Lock**: A user sends tokens to a smart contract on the source chain. The contract locks these tokens and emits an event (e.g., `Lock`) containing details of the transaction (recipient, amount, destination chain, nonce).
2.  **Listen**: A network of off-chain listeners (or oracles) constantly monitors the source chain for these `Lock` events.
3.  **Verify**: The listeners wait for a certain number of block confirmations to ensure the lock transaction is final and not part of a chain reorganization.
4.  **Mint**: After verification, a listener (or a consensus of listeners) submits a transaction to a corresponding contract on the destination chain. This transaction authorizes the minting of a "wrapped" or synthetic equivalent of the locked token and sends it to the specified recipient.

This script simulates the **Listen**, **Verify**, and **Mint** steps of this process.

---

## Code Architecture

The script is built using a modular, class-based architecture to separate concerns, making it easier to understand, maintain, and extend.

```
+-----------------------+
|      main.py          |
| (Orchestrator/Runner) |
+-----------+-----------+
            |
            v
+-----------------------+
|     EventListener     |
| (The Core Engine)     |
+-----------+-----------+
      |           |           |
      |           |           v
      |           |   +-------------------------------+
      |           |   | DestinationTransactionProcessor |
      |           |   | (Handles minting on dest chain) |
      |           |   +-------------------------------+
      |           v
      |   +-------------------------+
      |   |  BridgeContractHandler  |
      |   | (Parses contract events)|
      |   +-------------------------+
      v
+-------------------------------+
|   MockBlockchainNodeConnector |
|  (Simulates RPC connection)   |
+-------------------------------+

```

### Core Components

*   **`MockBlockchainNodeConnector`**: Simulates a connection to a source chain's RPC node (like Infura or Alchemy). Instead of making real network calls, it generates a stream of mock blocks and `Lock` event logs. This allows the script to run standalone without dependencies on a live network or API keys.

*   **`BridgeContractHandler`**: This class is responsible for all logic related to the bridge's smart contract. Its primary function is to take raw log data (as provided by the node connector) and parse it into a structured, understandable format. In a real application, it would use the contract's ABI (Application Binary Interface) for accurate decoding.

*   **`DestinationTransactionProcessor`**: Manages the lifecycle of transactions on the destination chain. It receives parsed event data, queues it for processing, and simulates the act of signing and sending a `mint` transaction. It includes logic to prevent duplicate processing using a nonce tracker.

*   **`EventListener`**: The central orchestrator. It contains the main event loop that:
    1.  Loads its last known state (the last block it processed).
    2.  Uses the `MockBlockchainNodeConnector` to poll for new blocks on the source chain.
    3.  Waits for a configurable number of confirmations.
    4.  Fetches logs for the specified block range.
    5.  Uses the `BridgeContractHandler` to parse any relevant `Lock` events.
    6.  Passes the parsed events to the `DestinationTransactionProcessor` to be queued for minting.
    7.  Saves its new state (the latest block processed) to a file to ensure persistence across restarts.

### Key Features

*   **Asynchronous:** Built with `asyncio` to efficiently handle I/O-bound tasks like polling for blocks and processing transactions without blocking.
*   **Stateful:** Persists the last processed block number to a `bridge_listener_state.json` file, allowing the listener to be stopped and restarted without reprocessing old events.
*   **Robust:** Includes comprehensive logging, error handling for simulated network issues, and a graceful shutdown mechanism.
*   **Configurable:** Key parameters like contract addresses, polling intervals, and confirmation counts are defined in a central `CONFIG` dictionary for easy modification.

---

## How it Works

1.  **Initialization**: On startup, the `EventListener` is created. It loads its state from `bridge_listener_state.json`. If the file doesn't exist, it starts from a default block number defined in the configuration.

2.  **Background Processing**: The `DestinationTransactionProcessor` starts a background worker task that waits for minting jobs to appear in its queue.

3.  **Main Loop**: The `EventListener` enters its main loop:
    a. It asks the `MockBlockchainNodeConnector` for the latest block number on the source chain.
    b. It calculates a target block to scan up to, ensuring a safety margin for block confirmations (`latest_block - confirmation_blocks`).
    c. If there are new blocks to scan, it requests all event logs from the bridge contract address within that block range.
    d. The `MockBlockchainNodeConnector` randomly generates `Lock` events to simulate user activity.
    e. For each log found, the `EventListener` uses the `BridgeContractHandler` to parse the raw hex data into a meaningful object (amount, recipient, etc.).
    f. If parsing is successful, the parsed event is handed to the `DestinationTransactionProcessor`, which adds it to its queue.
    g. The `EventListener` updates its `last_processed_block` state and saves it to the JSON file.
    h. The loop waits for a configured polling interval before starting over.

4.  **Transaction Execution**: Concurrently, the `DestinationTransactionProcessor`'s worker picks up jobs from its queue, simulates sending a transaction to the destination chain, waits for simulated confirmation, and logs the result.

---

## Usage Example

### Prerequisites

*   Python 3.8+

### Installation

No external libraries are required to run this simulation. All necessary modules are part of the Python standard library.

### Running the Script

To start the event listener simulation, simply run the script from your terminal:

```bash
python script.py
```

You will see log output detailing the listener's operations.

### Expected Output

The output will show the listener polling for blocks, finding and parsing events, and processing them on the destination chain.

```
2023-10-27 10:30:00 - CrossChainBridgeListener - INFO - --- Cross-Chain Bridge Event Listener Starting ---
2023-10-27 10:30:00 - CrossChainBridgeListener - INFO - Successfully loaded state from bridge_listener_state.json. Last processed block: 1050
2023-10-27 10:30:00 - CrossChainBridgeListener - INFO - [Ethereum-Goerli] MockConnector initialized for https://goerli.infura.io/v3/YOUR_INFURA_KEY
2023-10-27 10:30:00 - CrossChainBridgeListener - INFO - BridgeContractHandler initialized for contract: 0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B
2023-10-27 10:30:00 - CrossChainBridgeListener - INFO - [Polygon-Mumbai] DestinationTransactionProcessor is ready.
2023-10-27 10:30:00 - CrossChainBridgeListener - INFO - Scanning blocks from 1051 to 1052...
2023-10-27 10:30:01 - CrossChainBridgeListener - INFO - [Ethereum-Goerli] Simulated a new Lock event in block 1051
2023-10-27 10:30:01 - CrossChainBridgeListener - INFO - Successfully parsed Lock event at block 1051 (Nonce: 1698399001123)
2023-10-27 10:30:01 - CrossChainBridgeListener - INFO - [Polygon-Mumbai] Queued mint transaction for recipient 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 with amount 2345.0
2023-10-27 10:30:01 - CrossChainBridgeListener - INFO - [Polygon-Mumbai] Processing mint for nonce 1698399001123. Simulating signing and sending...
...
2023-10-27 10:30:05 - CrossChainBridgeListener - INFO - Scanning blocks from 1053 to 1055...
2023-10-27 10:30:06 - CrossChainBridgeListener - INFO - [Polygon-Mumbai] Transaction sent. Hash: 0x[...]
...
2023-10-27 10:30:09 - CrossChainBridgeListener - INFO - [Polygon-Mumbai] Transaction CONFIRMED for nonce 1698399001123. Mint successful.
```

To stop the script, press `Ctrl+C`. The application will perform a graceful shutdown, saving its final state before exiting.