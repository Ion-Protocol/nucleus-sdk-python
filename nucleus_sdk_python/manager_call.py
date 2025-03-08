from typing import List, Dict, Any, TYPE_CHECKING
from .exceptions import *
from .utils import encode_with_signature
import json

if TYPE_CHECKING:
    from nucleus_sdk_python.client import Client

class ManagerCall:
    def __init__(self, network_string: str, symbol: str, root: str, client: 'Client'):
        """
        Initialize a ManagerCall instance.
        
        Args:
            client: The SDK client for executing calls
        """
        self.client = client
        try:
            self.manager_address = client.address_book[network_string]["nucleus"][symbol]["manager"]
        except KeyError as e:
            raise InvalidInputsError(f"Could not find manager address for network '{network_string}' and symbol '{symbol}'. Please check the network and symbol are valid.")

        try:
            self.chain_id = client.address_book[network_string]["id"]
        except KeyError as e:
            raise InvalidInputsError(f"Could not find chain id for network '{network_string}'. Please check the network is valid.")
        
        self.root = root
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
        print("args", args)
        return encode_with_signature("manageVaultWithMerkleVerification(bytes32[][],address[],address[],bytes[],uint256[])", args)

    def execute(self, w3, acc) -> Any:
        """
        Execute the queued calls.
        
        Returns:
            Result of the execution
        """
        if not self.calls:
            raise ValueError("No calls to execute")
            
        calldata = self.get_calldata()

        transaction = {
            'from': acc.address,
            'to': self.manager_address,
            'value': 0,
            'nonce': w3.eth.get_transaction_count(acc.address),
            'data': calldata,
            'gas': w3.eth.estimate_gas({
                'from': acc.address,
                'to': self.manager_address,
                'data': calldata
            }),
            'gasPrice': w3.eth.gas_price,
            'chainId': self.chain_id
        }

        signed_txn = acc.sign_transaction(transaction)
        receipt = w3.eth.send_raw_transaction(signed_txn.raw_transaction)

        return receipt

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