import json
import requests
from typing import Optional, Dict, Any
from .exceptions import APIError
from .calldata_queue import CalldataQueue
from .config import address_book_endpoint, DEFAULT_BASE_URL
from .utils import checksum_addresses_in_json
from importlib.metadata import version
class Client:
    def __init__(self, nucleus_api_key: str, base_url: str = DEFAULT_BASE_URL):
        """
        Initialize the SDK client.
        
        Args:
            api_key: Your API key
            base_url: Base URL for the API (defaults to production)
        """
        self.nucleus_api_key = nucleus_api_key


        self.base_url = base_url
        self.session = requests.Session()
        self._setup_session()

        res = requests.get(address_book_endpoint)
        self.address_book= checksum_addresses_in_json(json.loads(res.text))

    def _setup_session(self):
        """Configure the HTTP session with default headers."""
        try:
            sdk_version = version("nucleus_sdk_python")
        except:
            sdk_version = "unknown"
            
        self.session.headers.update({
            "x-api-key": f"{self.nucleus_api_key}",
            "Content-Type": "application/json",
            "User-Agent": f"NucleusManagerSDKPython/{sdk_version}"
        })

    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Internal method to make HTTP requests.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/users")
            **kwargs: Additional request parameters
            
        Returns:
            Parsed JSON response
            
        Raises:
            APIError: If the request fails
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            message = json.loads(e.response.text).get("message")
            if message:
                raise APIError(message, status_code=e.response.status_code)
            else:
                raise APIError(str(e), status_code=e.response.status_code)

    def create_calldata_queue(self, chain_id: int, strategist_address: str, rpc_url: str, symbol: str) -> CalldataQueue:
        return CalldataQueue(chain_id, strategist_address, rpc_url, symbol, self)
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request."""
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a POST request."""
        return self._request("POST", endpoint, json=data)