import json
import requests
from typing import Optional, Dict, Any
from .exceptions import APIError
from .manager_call import ManagerCall
from .config import address_book_endpoint
from .utils import checksum_addresses_in_json
class Client:
    def __init__(self, api_key: str, base_url: str = "https://api.nucleusearn.io/merkle/"):
        """
        Initialize the SDK client.
        
        Args:
            api_key: Your API key
            base_url: Base URL for the API (defaults to production)
        """
        self.api_key = api_key


        self.base_url = base_url
        self.session = requests.Session()
        self._setup_session()

        res = requests.get(address_book_endpoint)
        self.address_book= checksum_addresses_in_json(json.loads(res.text))

    def _setup_session(self):
        """Configure the HTTP session with default headers."""
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "YourCompanySDK/1.0.0"
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
            message = json.loads(e.response.text)['message']
            if(message != "" and message != None):
                raise APIError(message, status_code=e.response.status_code)
            else:
                raise APIError(str(e), status_code=e.response.status_code)

    def create_manager_call(self, network_string: str, symbol: str, root: str) -> ManagerCall:
        return ManagerCall(network_string, symbol, root, self)
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a GET request."""
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make a POST request."""
        return self._request("POST", endpoint, json=data)