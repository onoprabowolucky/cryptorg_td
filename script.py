import asyncio
import json
import logging
import random
import time
from typing import Dict, Any, List, Optional, TypedDict

# --- Configuration ---
# In a real-world application, this would be loaded from a config file (e.g., YAML, TOML) or environment variables.
CONFIG = {
    "source_chain": {
        "name": "Ethereum-Goerli",
        "rpc_url": "https://goerli.infura.io/v3/YOUR_INFURA_KEY", # Simulated
        "bridge_contract_address": "0xAb5801a7D398351b8bE11C439e05C5B3259aeC9B", # Simulated with a known address for structure
        "start_block": 1000,
        "confirmation_blocks": 6
    },
    "destination_chain": {
        "name": "Polygon-Mumbai",
        "rpc_url": "https://rpc-mumbai.maticvigil.com", # Simulated
        "token_contract_address": "0x4599a09855353D8197925F444857C5B639B5A5C7" # Simulated
    },
    "listener": {
        "poll_interval_seconds": 5,
        "state_file": "bridge_listener_state.json"
    }
}

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("CrossChainBridgeListener")

# --- Type Definitions for Clarity ---
class LogEntry(TypedDict):
    address: str
    topics: List[str]
    data: str
    blockNumber: int

class Block(TypedDict):
    number: int
    timestamp: int
    transactions: List[Any] # In a real scenario, this would be a list of transaction objects

class ParsedLockEvent(TypedDict):
    source_token: str
    destination_chain_id: int
    recipient_address: str
    amount: int
    nonce: int
    block_number: int

# --- Simulated Components ---

class MockBlockchainNodeConnector:
    """
    Simulates a connection to a blockchain node (like Geth or Infura via Web3.py).
    It generates mock blocks and logs to simulate chain activity without real network calls.
    """
    def __init__(self, chain_name: str, rpc_url: str):
        self.chain_name = chain_name
        self.rpc_url = rpc_url
        self._current_block = CONFIG['source_chain']['start_block']
        logger.info(f"[{self.chain_name}] MockConnector initialized for {self.rpc_url}")

        # This is the event signature for: Lock(address,uint256,address,uint256,uint256)
        # A real application would use web3.keccak(text="Lock(...)")
        self.lock_event_signature_hash = "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"

    async def get_latest_block_number(self) -> int:
        """Simulates fetching the latest block number from the node."""
        await asyncio.sleep(0.1) # Simulate network latency
        # In a real simulation, block number should increase over time.
        self._current_block += random.randint(0, 2) # Chain progresses randomly
        logger.debug(f"[{self.chain_name}] Fetched latest block number: {self._current_block}")
        return self._current_block

    async def get_logs(self, from_block: int, to_block: int, address: str) -> List[LogEntry]:
        """Simulates fetching event logs for a given contract address and block range."""
        await asyncio.sleep(0.5) # Simulate heavier network latency for log fetching
        logs = []
        logger.debug(f"[{self.chain_name}] Fetching logs from block {from_block} to {to_block} for address {address}")
        
        # Let's simulate a lock event occurring randomly
        if random.random() < 0.5: # 50% chance of an event in this block range
            event_block = random.randint(from_block, to_block)
            mock_log = self._generate_mock_lock_event_log(event_block)
            
            # Ensure the log is from the correct contract
            if mock_log['address'].lower() == address.lower():
                logs.append(mock_log)
                logger.info(f"[{self.chain_name}] Simulated a new Lock event in block {event_block}")
        
        return logs

    def _generate_mock_lock_event_log(self, block_number: int) -> LogEntry:
        """
        Generates a raw log entry that mimics what an RPC node would return for a Lock event.
        The data field is a hex-encoded string of the event parameters.
        """
        # Mock data for the event: Lock(address, uint256, address, uint256, uint256)
        # source_token, destination_chain_id, recipient_address, amount, nonce
        source_token = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2" # WETH
        destination_chain_id = 80001 # Mumbai
        recipient_address = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"
        amount = random.randint(100, 5000) * 10**18 # Simulate 100-5000 tokens
        nonce = int(time.time() * 1000) + random.randint(0, 1000)

        # In a real application, this encoding would be done with a library like web3.py
        # Here we just put placeholder hex values
        data_payload = (
            source_token.replace('0x', '').zfill(64) + # address
            hex(destination_chain_id)[2:].zfill(64) +   # uint256
            recipient_address.replace('0x', '').zfill(64) + # address
            hex(amount)[2:].zfill(64) +                 # uint256
            hex(nonce)[2:].zfill(64)                    # uint256
        )

        return {
            "address": CONFIG['source_chain']['bridge_contract_address'],
            "topics": [self.lock_event_signature_hash], # First topic is always the event signature hash
            "data": "0x" + data_payload,
            "blockNumber": block_number
        }

# --- Core Logic Classes ---

class BridgeContractHandler:
    """
    Handles interactions with the bridge smart contract. Primarily focuses on parsing event logs.
    """
    def __init__(self, contract_address: str):
        self.contract_address = contract_address
        # In a real application, you would load the contract ABI here.
        logger.info(f"BridgeContractHandler initialized for contract: {self.contract_address}")

    def parse_lock_event_from_log(self, log: LogEntry) -> Optional[ParsedLockEvent]:
        """
        Decodes the 'data' field of a raw log entry into a structured event object.
        This is a simplified parser. A real one would use the contract's ABI.
        """
        try:
            # The data field is a concatenation of 32-byte (64 hex chars) values for non-indexed arguments
            data = log['data'].replace('0x', '')
            if len(data) != 64 * 5: # 5 arguments * 64 hex chars each
                logger.warning(f"Invalid data length in log at block {log['blockNumber']}: {len(data)}")
                return None

            parsed_event = {
                "source_token": "0x" + data[0:64][-40:], # Address is last 20 bytes (40 hex)
                "destination_chain_id": int(data[64:128], 16),
                "recipient_address": "0x" + data[128:192][-40:],
                "amount": int(data[192:256], 16),
                "nonce": int(data[256:320], 16),
                "block_number": log['blockNumber']
            }
            logger.info(f"Successfully parsed Lock event at block {log['blockNumber']} (Nonce: {parsed_event['nonce']})")
            return parsed_event
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Failed to parse log at block {log['blockNumber']}. Error: {e}, Data: {log['data']}")
            return None

class DestinationTransactionProcessor:
    """
    Simulates the process of creating, signing, and sending a transaction on the destination chain.
    In a real scenario, this would involve a wallet with private keys, nonce management, and gas estimation.
    """
    def __init__(self, chain_name: str):
        self.chain_name = chain_name
        self._pending_transactions = asyncio.Queue()
        self._processed_nonces = set()
        logger.info(f"[{self.chain_name}] DestinationTransactionProcessor is ready.")

    async def submit_mint_transaction(self, event: ParsedLockEvent) -> None:
        """
        Adds a new mint transaction to the processing queue based on a parsed lock event.
        Checks for duplicate nonces to prevent re-entrancy or replay attacks.
        """
        if event['nonce'] in self._processed_nonces:
            logger.warning(f"[{self.chain_name}] Duplicate nonce detected: {event['nonce']}. Skipping transaction.")
            return
        
        await self._pending_transactions.put(event)
        self._processed_nonces.add(event['nonce'])
        logger.info(f"[{self.chain_name}] Queued mint transaction for recipient {event['recipient_address']} with amount {event['amount'] / 1e18}")

    async def process_queue(self) -> None:
        """A worker that continuously processes transactions from the queue."""
        while True:
            try:
                event_to_process = await self._pending_transactions.get()
                logger.info(f"[{self.chain_name}] Processing mint for nonce {event_to_process['nonce']}. Simulating signing and sending...")
                
                # Simulate transaction lifecycle: send -> confirm
                await asyncio.sleep(2) # Simulate network call and mining time

                tx_hash = f"0x{random.randbytes(32).hex()}"
                logger.info(f"[{self.chain_name}] Transaction sent. Hash: {tx_hash}")

                await asyncio.sleep(3) # Simulate confirmation time
                logger.info(f"[{self.chain_name}] Transaction CONFIRMED for nonce {event_to_process['nonce']}. Mint successful.")

                self._pending_transactions.task_done()
            except asyncio.CancelledError:
                logger.info(f"[{self.chain_name}] Transaction processor is shutting down.")
                break
            except Exception as e:
                logger.error(f"[{self.chain_name}] An unexpected error occurred in the transaction processor: {e}")
                # In a real system, you might requeue the transaction or move it to a dead-letter queue.


class EventListener:
    """
    The main orchestrator. It polls the source chain for new blocks, filters for relevant events,
    and passes them to the transaction processor.
    """
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.state_file = self.config['listener']['state_file']
        self.state = self._load_state()

        self.source_node = MockBlockchainNodeConnector(
            self.config['source_chain']['name'],
            self.config['source_chain']['rpc_url']
        )
        self.bridge_contract = BridgeContractHandler(
            self.config['source_chain']['bridge_contract_address']
        )
        self.tx_processor = DestinationTransactionProcessor(
            self.config['destination_chain']['name']
        )

    def _load_state(self) -> Dict[str, Any]:
        """Loads the last processed block number from a state file."""
        try:
            with open(self.state_file, 'r') as f:
                state = json.load(f)
                logger.info(f"Successfully loaded state from {self.state_file}. Last processed block: {state['last_processed_block']}")
                return state
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning(f"State file not found or invalid. Initializing with default start block.")
            return {"last_processed_block": self.config['source_chain']['start_block']}

    def _save_state(self) -> None:
        """Saves the current state (last processed block) to the file."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=4)
                logger.debug(f"State saved. Last processed block is now {self.state['last_processed_block']}")
        except IOError as e:
            logger.error(f"Could not save state to {self.state_file}. Error: {e}")

    async def run(self) -> None:
        """The main event loop for the listener."""
        logger.info("--- Cross-Chain Bridge Event Listener Starting ---")
        
        # Start the destination chain transaction processor as a background task
        processor_task = asyncio.create_task(self.tx_processor.process_queue())

        try:
            while True:
                try:
                    latest_block = await self.source_node.get_latest_block_number()
                    from_block = self.state['last_processed_block'] + 1
                    
                    # We wait for a few confirmations before processing a block
                    to_block = latest_block - self.config['source_chain']['confirmation_blocks']

                    if from_block > to_block:
                        logger.info(f"Waiting for new blocks to be confirmed... (Current: {latest_block}, Last Processed: {self.state['last_processed_block']})")
                        await asyncio.sleep(self.config['listener']['poll_interval_seconds'])
                        continue

                    logger.info(f"Scanning blocks from {from_block} to {to_block}...")

                    logs = await self.source_node.get_logs(
                        from_block=from_block,
                        to_block=to_block,
                        address=self.bridge_contract.contract_address
                    )

                    if not logs:
                        logger.debug("No relevant logs found in this range.")
                    
                    for log in logs:
                        parsed_event = self.bridge_contract.parse_lock_event_from_log(log)
                        if parsed_event:
                            await self.tx_processor.submit_mint_transaction(parsed_event)
                    
                    # Update state and save it
                    self.state['last_processed_block'] = to_block
                    self._save_state()

                except Exception as e:
                    logger.error(f"An error occurred in the main event loop: {e}", exc_info=True)
                    # In a production system, you might have more sophisticated backoff strategies.
                
                await asyncio.sleep(self.config['listener']['poll_interval_seconds'])
        
        except asyncio.CancelledError:
            logger.info("Listener shutdown signal received.")
        finally:
            logger.info("--- Shutting down listener and dependencies ---")
            processor_task.cancel()
            await processor_task # Wait for the task to acknowledge cancellation
            self._save_state() # Final state save
            logger.info("--- Listener has been shut down gracefully ---")


async def main():
    listener = EventListener(CONFIG)
    try:
        await listener.run()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, initiating graceful shutdown.")
    # The listener's run method handles the graceful shutdown on CancelledError

if __name__ == "__main__":
    asyncio.run(main())

# @-internal-utility-start
def get_config_value_7595(key: str):
    """Reads a value from a simple key-value config. Added on 2025-10-16 18:26:16"""
    with open('config.ini', 'r') as f:
        for line in f:
            if line.startswith(key):
                return line.split('=')[1].strip()
    return None
# @-internal-utility-end

