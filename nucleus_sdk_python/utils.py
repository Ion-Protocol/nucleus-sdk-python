from eth_utils import keccak
from eth_abi import encode
from web3 import Web3

def parse_argument_types(signature: str):
    """
    Parses the argument types from a Solidity function signature, including nested structs.
    (Chat GPT generated)
    :param signature: The function signature, e.g., "doSomething((address,uint256),uint256)"
    :return: List of argument types, e.g., ['(address,uint256)', 'uint256']
    """
    # Extract the part inside parentheses
    args_str = signature[signature.index('(') + 1: signature.rindex(')')]

    # Recursive helper function to split types, respecting nested parentheses
    def split_types(s):
        types = []
        current = ""
        depth = 0

        for char in s:
            if char == "," and depth == 0:  # Split at top-level commas
                types.append(current.strip())
                current = ""
            else:
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1
                current += char

        if current:  # Append the last type
            types.append(current.strip())

        return types

    # Split top-level argument types
    return split_types(args_str)

def encode_with_signature(signature: str, args: list):
    """
    Encodes data according to a Solidity function signature, including nested structs.
    (Chat GPT Generated)

    :param signature: Function signature, e.g., "doSomething((address,uint256))"
    :param args: Arguments to encode, including structs as tuples.
    :return: ABI-encoded bytes with the function selector.
    """
    # Compute the function selector
    function_selector = keccak(text=signature)[:4]
    # Parse argument types
    arg_types = parse_argument_types(signature)
    # ABI-encode the arguments
    encoded_args = encode(arg_types, args)
    # Combine the function selector and encoded arguments
    return function_selector + encoded_args

def checksum_addresses_in_json(data):
    """
    Recursively traverses a JSON object and converts all Ethereum addresses to checksum format.

    :param data: The JSON object (dict or list)
    :return: The JSON object with addresses in checksum format
    """
    if isinstance(data, dict):
        return {key: checksum_addresses_in_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [checksum_addresses_in_json(item) for item in data]
    elif isinstance(data, str):
        # Check if the string is a valid Ethereum address
        if Web3.is_address(data):
            return Web3.to_checksum_address(data)
    return data
