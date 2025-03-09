import pytest
import os
from dotenv import load_dotenv
from web3 import Web3
from web3 import exceptions
from nucleus_sdk_python.client import Client
from nucleus_sdk_python.exceptions import *
from nucleus_sdk_python.config import DEFAULT_BASE_URL
import re

load_dotenv()
nucleus_api_key = os.environ["API_KEY"]

def get_valid_calldata_queue(client):
    rpc_url = os.environ["RPC_URL"]
    strategist_address = os.environ["STRATEGIST_ADDRESS"]
    chain_id = int(os.environ.get("CHAIN_ID", "1"))
    symbol = "tETH"
    return client.create_calldata_queue(chain_id, strategist_address, rpc_url, symbol)

def test_client_initialization():
    client = Client(nucleus_api_key=nucleus_api_key)
    assert client.nucleus_api_key== nucleus_api_key
    assert client.base_url == DEFAULT_BASE_URL

def test_calldata_queue():
    client = Client(nucleus_api_key=nucleus_api_key)
    calldata_queue = get_valid_calldata_queue(client)
    assert calldata_queue.root == "0x8e93234bde5b9e369fb07acdee1cf6e3033222c2a4a0178fac08a05ce190d6e6"
    assert calldata_queue.manager_address == "0xf875dEe4e500ab850369fa9c9F6a8296B912c598"
    assert calldata_queue.client == client

    calldata_queue.add_call("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "approve(address,uint256)", ["0xDB74dfDD3BB46bE8Ce6C33dC9D82777BCFc3dEd5", 140], 0)
    assert "calldata: ",calldata_queue.get_calldata().hex() == "244b0f6a00000000000000000000000000000000000000000000000000000000000000a0000000000000000000000000000000000000000000000000000000000000018000000000000000000000000000000000000000000000000000000000000001c0000000000000000000000000000000000000000000000000000000000000020000000000000000000000000000000000000000000000000000000000000002c0000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000004cc4aeb6035a8ad265b244a6abfc360c2d744d52abf9294eefab0cd727f4563245d87c7bdc9b6983be31688c73b643685bc69a65e0b95777ff9f0b39c006f2bb1c8735f529daecb3f8025db4275eefb1c54206bb88ed0c97f07211b049a08a68ed2cb562b5b8bf58af894cb8288dc47e470bd54f3a0d276a3ceabedf8a11fd023000000000000000000000000000000000000000000000000000000000000000100000000000000000000000033a4392c4264611c81dbfd7052ffb75d60dd46500000000000000000000000000000000000000000000000000000000000000001000000000000000000000000c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2000000000000000000000000000000000000000000000000000000000000000100000000000000000000000000000000000000000000000000000000000000200000000000000000000000000000000000000000000000000000000000000044095ea7b3000000000000000000000000db74dfdd3bb46be8ce6c33dc9d82777bcfc3ded5000000000000000000000000000000000000000000000000000000000000008c0000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000010000000000000000000000000000000000000000000000000000000000000000"

def test_execute():
    w3 = Web3(Web3.HTTPProvider(os.environ["RPC_URL"]))
    acc = w3.eth.account.from_key(os.environ["PRIVATE_KEY"])
    client = Client(nucleus_api_key=nucleus_api_key)
    calldata_queue = get_valid_calldata_queue(client)
    calldata_queue.add_call("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "approve(address,uint256)", ["0xDB74dfDD3BB46bE8Ce6C33dC9D82777BCFc3dEd5", 140], 0)
    receipt = calldata_queue.execute(w3, acc)

def test_execute_with_invalid_strategist_address():
    w3 = Web3(Web3.HTTPProvider(os.environ["RPC_URL"]))
    acc = w3.eth.account.from_key("0x0000000000000000000000000000000000000000000000000000000000000000")
    client = Client(nucleus_api_key=nucleus_api_key)
    calldata_queue = get_valid_calldata_queue(client)
    calldata_queue.add_call("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "approve(address,uint256)", ["0xDB74dfDD3BB46bE8Ce6C33dC9D82777BCFc3dEd5", 140], 0)
    with pytest.raises(ValueError, match="Strategist address does not match the account address"):
        calldata_queue.execute(w3, acc)

def test_invalid_nucleus_api_key():
    client = Client(nucleus_api_key="invalid_key")
    calldata_queue = get_valid_calldata_queue(client)
    calldata_queue.add_call("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "approve(address,uint256)", ["0xDB74dfDD3BB46bE8Ce6C33dC9D82777BCFc3dEd5", 140], 0)

    with pytest.raises(APIError, match="Forbidden"):
        calldata_queue.get_calldata()

def test_invalid_inputs():
    client = Client(nucleus_api_key=nucleus_api_key)

    with pytest.raises(InvalidInputsError):
        # Using an invalid strategist address
        invalid_strategist_address = "0x0000000000000000000000000000000000000000"
        calldata_queue = client.create_calldata_queue(1, invalid_strategist_address, os.environ["RPC_URL"], "tETH")
        calldata_queue.get_calldata()
    with pytest.raises(InvalidInputsError):
        # Using an invalid chain id
        calldata_queue = client.create_calldata_queue(0, os.environ["STRATEGIST_ADDRESS"], os.environ["RPC_URL"], "tETH")
        calldata_queue.get_calldata()
    with pytest.raises(InvalidInputsError):
        # Using an invalid rpc url
        invalid_rpc_url = "https://invalid.rpc.url"
        calldata_queue = client.create_calldata_queue(1, os.environ["STRATEGIST_ADDRESS"], invalid_rpc_url, "tETH")
        calldata_queue.get_calldata()
    with pytest.raises(InvalidInputsError):
        # Using an invalid symbol to trigger an InvalidInputsError
        calldata_queue = client.create_calldata_queue(1, os.environ["STRATEGIST_ADDRESS"], os.environ["RPC_URL"], "Not_a_symbol")
        calldata_queue.get_calldata()

def test_invalid_target():
    client = Client(nucleus_api_key=nucleus_api_key)
    calldata_queue = get_valid_calldata_queue(client)
    with pytest.raises(APIError, match="Target 0xd02aaa39b223fe8d0a0e5c4f27ead9083c756cc2 is not defined on this merkle root"):
        calldata_queue.add_call("0xd02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "approve(address,uint256)", ["0xDB74dfDD3BB46bE8Ce6C33dC9D82777BCFc3dEd5", 140], 0)
        calldata_queue.get_calldata()

def test_invalid_function_signature():
    client = Client(nucleus_api_key=nucleus_api_key)
    calldata_queue = get_valid_calldata_queue(client)
    with pytest.raises(APIError, match="Function selector: 0xbd0d639f does not exist for this target: 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2,\n        Selectors defined for this target are: 0x095ea7b3"):
        calldata_queue.add_call("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "foo(address,uint256)", ["0xDB74dfDD3BB46bE8Ce6C33dC9D82777BCFc3dEd5", 140], 0)
        calldata_queue.get_calldata()

def test_invalid_args():
    client = Client(nucleus_api_key=nucleus_api_key)
    calldata_queue = get_valid_calldata_queue(client)
    expected_error = 'Could not return proof, call parameters are incorrect\n \n          The allowed arguments for this target and function are: \n [["0xBA12222222228d8Ba445958a75a0704d566BF2C8",0],["0xC8Eb2Cf2f792F77AF0Cd9e203305a585E588179D",0],["0x1b81D678ffb9C0263b24A97847620C99d213eB14",0],["0x39F5b252dE249790fAEd0C2F05aBead56D2088e1",0],["0xDB74dfDD3BB46bE8Ce6C33dC9D82777BCFc3dEd5",0]]\n\n          The packedArgs for this target and function is: undefined'

    with pytest.raises(APIError, match=re.escape(expected_error)):
        # Add call with invalid address that's not in allowed arguments list
        calldata_queue.add_call(
            "0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2",  # WETH contract
            "approve(address,uint256)", 
            ["0x00000fDD3BB46bE8Ce6C33dC9D82777BCFc3dEd5", 140],  # Invalid address
            0  # No ETH value
        )
        calldata_queue.get_calldata()


def test_invalid_value():
    client = Client(nucleus_api_key=nucleus_api_key)
    calldata_queue = get_valid_calldata_queue(client)
    with pytest.raises(APIError, match="value mismatch, please verify that this function call can send value"):
        calldata_queue.add_call("0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2", "approve(address,uint256)", ["0xDB74dfDD3BB46bE8Ce6C33dC9D82777BCFc3dEd5", 140], 1)
        calldata_queue.get_calldata()
