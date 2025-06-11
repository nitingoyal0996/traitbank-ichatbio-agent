from collections.abc import AsyncGenerator
from typing import Optional, Dict, Any, List, Tuple
from urllib.parse import quote

import httpx

TRAITBANK_BASE_URL = "https://traitbank-reconnect.hcmr.gr"

class TraitBankTools:
    """
    A collection of tools to interact with the TraitBank API.
    These methods primarily handle the HTTP requests and return raw data or raise exceptions.
    """


    @staticmethod
    def _generate_uri(url: str, query_params: Dict[str, str]) -> str:
        """Generate complete URI with query parameters."""
        if query_params:
            param_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
            return f"{url}?{param_string}"
        return url


    @staticmethod
    def _get_query_params(data_type: str) -> Dict[str, str]:
        """Get query parameters based on the data type (taxon or trait)."""
        params: Dict[str, str] = {
            "verbose": "1",  # Always get verbose data
            "assoc": "1"     # Always get associative format (dict)
        }
        if data_type == "taxon":
            params["exact"] = "1"  # Use exact match only for taxon searches
        return params


    async def fetch_taxon_data_by_name(
        self, taxon_name: str
    ) -> Tuple[Optional[Dict[Any, Any]], str]:
        """
        Fetch taxon data from the TraitBank API by taxon name.
        Returns a tuple of (response_json_dict, request_uri).
        Raises httpx.HTTPStatusError for API errors.
        Returns (None, request_uri) if response body is not valid JSON (should be rare with raise_for_status).
        """
        encoded_query = quote(taxon_name)
        url = f"{TRAITBANK_BASE_URL}/taxon/{encoded_query}/"
        query_params = self._get_query_params(data_type="taxon")
        uri = self._generate_uri(url, query_params)

        async with httpx.AsyncClient() as client:
            response = await client.get(uri)
            response.raise_for_status()  # Raises HTTPStatusError for 4xx/5xx responses
            try:
                # Ensure response is not empty before trying to parse JSON
                if not response.content:
                    return None, uri
                response_data = response.json()
                return response_data, uri
            except Exception: # Catch JSONDecodeError or other parsing issues
                # This case should be less common if raise_for_status() passed and content-type is correct
                return None, uri


    async def fetch_trait_data_by_ids(
        self, taxon_ids_query: str # Expects a comma-separated string of IDs
    ) -> Tuple[Optional[Dict[Any, Any]], str]:
        """
        Fetch trait data from the TraitBank API by taxon ID(s).
        Returns a tuple of (response_json_dict, request_uri).
        Raises httpx.HTTPStatusError for API errors.
        Returns (None, request_uri) if response body is not valid JSON.
        """
        url = f"{TRAITBANK_BASE_URL}/traits/{taxon_ids_query}/"
        query_params = self._get_query_params(data_type="trait")
        uri = self._generate_uri(url, query_params)

        async with httpx.AsyncClient() as client:
            response = await client.get(uri)
            response.raise_for_status()
            try:
                if not response.content:
                    return None, uri
                response_data = response.json()
                return response_data, uri
            except Exception:
                return None, uri
