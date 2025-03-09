from typing import List, Dict, Any, TYPE_CHECKING
from .exceptions import *
from .utils import encode_with_signature
import json
from web3 import Web3

if TYPE_CHECKING:
    from nucleus_sdk_python.client import Client

class CalldataQueue:
    def __init__(self, chain_id: int, strategist_address: str, rpc_url: str, symbol: str, client: 'Client'):
        """
        Initialize a CalldataQueue instance.
        
        Args:
            client: The SDK client for executing calls
        """
        # TODO: Read this from the address book as the ChainID
        network_string = str(chain_id)
        
        self.client = client
        try:
            self.manager_address = client.address_book[network_string]["nucleus"][symbol]["manager"]
        except KeyError as e:
            raise InvalidInputsError(f"Could not find manager address for network '{network_string}' and symbol '{symbol}'. Please check the network and symbol are valid.")
        
        self.chain_id = chain_id
        self.rpc_url = rpc_url
        self.strategist_address = strategist_address

        # Get root from manager contract
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        try:
            w3.eth.get_block('latest')
        except Exception as e:
            raise InvalidInputsError(f"Could not connect to RPC URL '{rpc_url}'. Please check the RPC URL is valid and accessible.")
            
        manager_contract = w3.eth.contract(
            address=self.manager_address,
            abi=[{
                "inputs": [{"type": "address", "name": "strategist"}],
                "name": "manageRoot",
                "outputs": [{"type": "bytes32"}],
                "stateMutability": "view",
                "type": "function"
            }]
        )
        self.root = manager_contract.functions.manageRoot(strategist_address).call().hex()

        if self.root[0:2] != "0x":
            self.root = "0x" + self.root

        if self.root == "0x0000000000000000000000000000000000000000000000000000000000000000":
            raise InvalidInputsError(f"Could not find root for strategist '{strategist_address}'. Please check the strategist address is valid.")
        
        self.calls: List[Dict[str, Any]] = []

    def add_call(self, target_address: str, function_signature: str, args: List[any], value: int) -> None:
        """
        Add a call to the queue.
        
        Args:
            target_address: The address of the target contract
            function_signature: The function signature to call
            args: The arguments to pass to the function
            value: The value to send with the call
        """
        data = encode_with_signature(function_signature, args)
        self.calls.append({
            "target_address": target_address,
            "data": data,
            "value": value,
            "args": args,
            "function_signature": function_signature,
            "proof_data": [],
            "decoder_and_sanitizer": ""
        })

    def get_calldata(self) -> List[Dict[str, Any]]:
        """
        Get the formatted calldata using batched proofs and decoders.
        
        Returns:
            The encoded calldata (with batched proofs, decoders, targets, data, and values)
        """
        # Build an array of leaves for every call
        leaves = []
        for call in self.calls:
            # Recalculate calldata as a hex string (consistent with _get_proof_and_decoder)
            encoded_calldata = encode_with_signature(call["function_signature"], call["args"])
            encoded_calldata_hex = "0x" + encoded_calldata.hex()
            leaf = {
                "target": call["target_address"],
                "calldata": encoded_calldata_hex,
                "value": call["value"]
            }
            leaves.append(leaf)
        
        # Get batch proofs and decoders from the nucleus API
        batch_results = self._get_batch_proofs_and_decoders(leaves)
        
        targets = []
        data = []
        values = []

        # Convert hex string proofs to bytes
        batch_results["proofs"] = [
            [bytes.fromhex(proof[2:]) for proof in proof_set]
            for proof_set in batch_results["proofs"]
        ]

        for idx, call in enumerate(self.calls):
            targets.append(call["target_address"])
            data.append(call["data"])
            values.append(call["value"])
        
        args = [batch_results["proofs"], batch_results["decoderAndSanitizerAddress"], targets, data, values]
        return encode_with_signature("manageVaultWithMerkleVerification(bytes32[][],address[],address[],bytes[],uint256[])", args)

    def execute(self, w3, acc) -> Any:
        """
        Execute the queued calls.
        
        Returns:
            Result of the execution
        """
        if not self.calls:
            raise ValueError("No calls to execute")
        
        if self.strategist_address != acc.address:
            raise ValueError("Strategist address does not match the account address")

        calldata = self.get_calldata()
        tx = {
            "to": self.manager_address,
            "from": acc.address,
            "data": calldata,
            "value": 0
        }
        return w3.eth.send_transaction(tx)

    def _get_batch_proofs_and_decoders(self, leaves: List[Dict[str, Any]]) -> Dict[str, List[Any]]:
        """
        Gets multiple proofs and decoders from the nucleus API by posting an array of leaves.
        
        Args:
            leaves: Array of leaf dictionaries. Each leaf should include:
                    - "target": The target contract address
                    - "calldata": The encoded calldata (as a hex string, starting with "0x")
                    - "value": The value to send with the call
                    - "chain": The chain ID (this could be added automatically via self.chain_id if desired)
                    
        Returns:
           A dictionary with a list for proofs and decoderAndSanitizerAddresses
        """
        # Post the array of leaves to the batch endpoint.
        response = self.client.post("multiproofs/" + self.root, data={"chain": self.chain_id, "calls": leaves})
        print("response: ", response)
        assert len(response["proofs"]) == len(response["decoderAndSanitizerAddress"])

        return response

    def _get_proof_and_decoder(self, target, signature, args, value):
        """
        Gets the proof from the nucleus api from the root
        """

        calldata = encode_with_signature(signature, args)
        calldata = "0x"+calldata.hex()
        leaf = {
            "target": target,
            "calldata": calldata,
            "value": value,
            "chain": self.chain_id
        }

        data = self.client.post("proofs/"+self.root, data=leaf)

        new_proof = []
        try:
            for hash in data['proof']:
                new_proof.append(bytes.fromhex(hash[2:]))
        except KeyError as e:
            raise ProtocolError(f"Error decoding proof from the API.")
        
        data['proof'] = new_proof

        return data