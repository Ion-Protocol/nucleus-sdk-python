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
        Get the formatted calldata.
        
        Returns:
            List of calls with their method and params
        """
        proofs = []
        decoders = []
        targets = []
        data = []
        values = []

        for call in self.calls:
            # Get proof data if not already present
            if call["proof_data"]:
                proof = call["proof_data"]
            else:
                proof = self._get_proof_and_decoder(
                    call["target_address"], 
                    call["function_signature"],
                    call["args"],
                    call["value"]
                )["proof"]
            proofs.append(proof)

            # Get decoder if not already present 
            if call["decoder_and_sanitizer"]:
                decoder = call["decoder_and_sanitizer"]
            else:
                decoder = self._get_proof_and_decoder(
                    call["target_address"],
                    call["function_signature"], 
                    call["args"],
                    call["value"]
                )["decoderAndSanitizerAddress"]
            decoders.append(decoder)

            # Add other call data
            targets.append(call["target_address"])
            data.append(call["data"])
            values.append(call["value"])

        args = [proofs, decoders, targets, data, values]
        
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
        tx = {
            "to": self.manager_address,
            "from": acc.address,
            "data": calldata,
            "value": 0
        }
        return w3.eth.send_transaction(tx)

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