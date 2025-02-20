# =======================================
# Nucleus SDK Python Uniswap Swap Example
# =======================================

# Import the Nucleus SDK Python Client
from nucleus_sdk_python.client import Client
import os
from dotenv import load_dotenv
import time
from eth_abi.packed import encode_packed
from web3 import Web3

load_dotenv()

def main():
    # You will need an API key to use the Nucleus API. 
    # This example assumes you have an API key in your .env file.
    api_key = os.environ["API_KEY"]

    # Initialize the Nucleus SDK Python Client using the API key
    client = Client(api_key)

    # Define the root for your manager call object.
    # Each strategist will have a root that is published onchain and limits what calls can be made.
    tETH_root = "0x4c145ea35f5f556531c45ca38f25b0829e58a7c9cb406046dffc48076b29edb5"
    strategist_address = "0x0000000000417626Ef34D62C4DC189b021603f2F"
    
    # Define the network string you will conduct your manager call on.
    network_string = "eth"
    # Define the boring vault symbol you will conduct your manager call on.
    symbol = "nTBILL"

    # Create the calldata queue object.
    calldata_queue = client.create_calldata_queue(root=tETH_root, network_string=network_string, symbol=symbol)

    # Each client comes with a built in address book.
    # The address book is a dictionary that maps network strings to protocols to a list of addresses.
    address_book = client.address_book
    USDC = address_book[network_string]["token"]["USDC"]
    wM = address_book[network_string]["token"]["wM"]
    print("USDC address on network", USDC)
    print("Boring Vault address on network", address_book[network_string]["nucleus"][symbol]["boring_vault"])

    # Add the first call to the calldata queue object.
    calldata_queue.add_call(
        USDC,                               # target address
        "approve(address,uint256)",          # function signature
        [address_book[network_string]["uniswap"]["ROUTER"], int(1e6)],  # function arguments array
        0                                    # native value
    )

    # The following is the ExactInputParams struct which is the parameter for a uniswap v3 ExactInput call.
    #  struct ExactInputParams {
    #     bytes path;
    #     address recipient;
    #     uint256 deadline;
    #     uint256 amountIn;
    #     uint256 amountOutMinimum;
    # }

    # The following is how you would create this for use in a manager call.
    # first off the path is the encoded bytes of the from token, pool fee, and to token
    fee = int(100)
    path = encode_packed(["address", "uint24", "address"], [USDC, fee, wM])
    exact_input_params = [
        path,
        address_book[network_string]["nucleus"][symbol]["boring_vault"], 
        int(time.time() + 3600),                                # sets deadline to 1 hour from now
        int(1e6),
        int(0.5e6)
    ]

    # Now construct the calldata queue by adding another call.
    calldata_queue.add_call(
        address_book[network_string]["uniswap"]["ROUTER"],
        "exactInput((bytes,address,uint256,uint256,uint256))",
        [exact_input_params],  # Note this is an array of an array
        0
    )

    # Now we can get the calldata in bytes.
    print("Manager Contract: ", address_book[network_string]["nucleus"][symbol]["manager"])
    print("Calldata after adding approve call:\n", calldata_queue.get_calldata().hex())

    # Or if you'd like the execute the manager call directly you can do so using a web3.py provider and account:
    w3 = Web3(Web3.HTTPProvider(os.environ["RPC_URL"]))
    acc = w3.eth.account.from_key(os.environ["PRIVATE_KEY"])

    # receipt = calldata_queue.execute(w3, acc)
    # print("Receipt: ", receipt)

if __name__ == "__main__":
    main() 