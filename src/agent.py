from collections.abc import AsyncGenerator
from typing import Optional
from urllib.parse import quote

import httpx
from ichatbio.agent import IChatBioAgent
from ichatbio.types import (
    AgentCard,
    AgentEntrypoint,
    ArtifactMessage,
    Message,
    ProcessMessage,
    TextMessage,
)
from pydantic import BaseModel, ValidationError
from typing_extensions import override

from .models import (
    TaxonDataRequest,
    TaxonDataResponse,
    TraitDataRequest,
    TraitDataResponse,
)

# Base URL for the TraitBank API
TRAITBANK_BASE_URL = "https://traitbank-reconnect.hcmr.gr"


trait_bank_agent_card = AgentCard(
    name="Trait Bank Agent",
    description="""Retrieves taxon IDs and Taxon Trait information with Taxon ID from the Trait Bank API.
    Trait Bank API URL: https://traitbank-reconnect.hcmr.gr/""",
    icon=None,
    entrypoints=[
        AgentEntrypoint(
            id="get_taxon_id",
            description="Fetch Taxon IDs based on given Taxon-Name.",
            parameters=TaxonDataRequest,
        ),
        AgentEntrypoint(
            id="get_trait_data",
            description="Fetch Trait Data for a given Taxon ID.",
            parameters=TraitDataRequest,
        ),
    ],
)


class TraitBankAgent(IChatBioAgent):
    def __init__(self):
        self.agent_card = trait_bank_agent_card

    @override
    def get_agent_card(self) -> AgentCard:
        return self.agent_card

    @override
    async def run(
        self, request: str, entrypoint: str, params: Optional[BaseModel]
    ) -> AsyncGenerator[Message, None]:
        if entrypoint == "get_taxon_id":
            if not isinstance(params, TaxonDataRequest):
                yield TextMessage(
                    text="Invalid parameters for get_taxon_id. Expected TaxonDataRequest."
                )
                return

            async for message in self._fetch_taxon_ids(params):
                yield message

        elif entrypoint == "get_trait_data":
            if not isinstance(params, TraitDataRequest):
                yield TextMessage(
                    text="Invalid parameters for get_trait_data. Expected TraitDataRequest."
                )
                return

            async for message in self._fetch_trait_data(params):
                yield message

        else:
            yield TextMessage(text=f"Unknown entrypoint: {entrypoint}")


    def _generate_uri(self, url, query_params):
        if query_params:
            param_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
            uri = f"{url}?{param_string}"
        else:
            uri = url
        return uri


    def _configure_query_params(self, params):
        query_params = {}
        if params.exact is not None:
            query_params["exact"] = "1" if params.exact else "0"
        if params.verbose is not None:
            query_params["verbose"] = "1" if params.verbose else "0"
        if params.assoc is not None:
            query_params["assoc"] = "1" if params.assoc else "0"
        return query_params


    async def _fetch_taxon_ids(
        self, params: TaxonDataRequest
    ) -> AsyncGenerator[Message, None]:
        """
        Fetch taxon IDs from the TraitBank API and yield messages.
        """
        try:
            yield ProcessMessage(
                summary="Creating query URI",
                description=f"Creating TraitBank search query URI for taxon matching: **{params.query}**",
            )

            # Build the API URL
            encoded_query = quote(params.query)
            url = f"{TRAITBANK_BASE_URL}/taxon/{encoded_query}/"
            query_params = self._configure_query_params(params)
            uri = self._generate_uri(url, query_params)

            # Make the HTTP request
            async with httpx.AsyncClient() as client:
                yield ProcessMessage(
                    summary="Searching for taxon",
                    description=f"Searching TraitBank database for taxon matching: **{params.query}**",
                )

                response = await client.get(uri)
                response.raise_for_status()
                response_data = response.json()

                if response_data is None:
                    yield TextMessage(
                        text=f"No taxon data found for '{params.query}'. The taxon may not exist in the TraitBank database."
                    )
                    return

                try:
                    validated_response = TaxonDataResponse.model_validate(response_data)
                    yield ProcessMessage(
                        summary="Validating response",
                        description="Successfully validated API response structure",
                    )
                except ValidationError as ve:
                    yield TextMessage(
                        text=f"Warning: API response validation failed: {str(ve)}. Proceeding with raw data."
                    )
                    validated_response = None

                yield ProcessMessage(
                    summary="Generating artifact",
                    description=f"Generating artifact for taxon search results matching: **{uri}**",
                )

                final_data = (
                    validated_response.model_dump()
                    if validated_response
                    else response_data
                )

                taxon_count = self._count_taxon(final_data)

                yield ArtifactMessage(
                    mimetype="application/json",
                    description=f"Taxon search results for '{params.query}'",
                    uris=[quote(uri)],
                    metadata={
                        "query": params.query,
                        "query_params": query_params,
                        "result_count": taxon_count,
                    },
                )

                summary_message = self._generate_summary_message(
                    final_data, taxon_count, params.query, "taxon"
                )
                yield TextMessage(text=summary_message)

                yield ProcessMessage(
                    summary="Taxon search completed",
                    description=f"Completed search for taxon matching: **{params.query}**",
                )

        except httpx.HTTPError as e:
            yield TextMessage(
                text=f"Failed to fetch taxon data from TraitBank API: {str(e)}"
            )
        except Exception as e:
            yield TextMessage(text=f"Error processing taxon search: {str(e)}")

    async def _fetch_trait_data(
        self, params: TraitDataRequest
    ) -> AsyncGenerator[Message, None]:
        """
        Fetch trait data from the TraitBank API and yield messages.
        """
        try:
            # Handle both string and list query formats
            if isinstance(params.query, list):
                query_string = ",".join(str(id) for id in params.query)
                taxon_ids = params.query
            else:
                query_string = str(params.query)
                taxon_ids = query_string.split(",")

            yield ProcessMessage(
                summary="Creating query URI",
                description=f"Creating TraitBank trait query URI for taxon ID(s): **{query_string}**",
            )

            # Build the API URL
            url = f"{TRAITBANK_BASE_URL}/traits/{query_string}/"
            query_params = self._configure_query_params(params)
            uri = self._generate_uri(url, query_params)

            # Make the HTTP request
            async with httpx.AsyncClient() as client:
                yield ProcessMessage(
                    summary="Fetching trait data",
                    description=f"Retrieving trait information for taxon ID(s): **{query_string}**",
                )

                response = await client.get(uri)
                response.raise_for_status()
                response_data = response.json()

                # Validate response using Pydantic model
                try:
                    validated_response = TraitDataResponse.model_validate(response_data)
                    yield ProcessMessage(
                        summary="Validating response",
                        description="Successfully validated API response structure",
                    )
                except ValidationError as ve:
                    yield TextMessage(
                        text=f"Warning: API response validation failed: {str(ve)}. Proceeding with raw data."
                    )
                    validated_response = None

                yield ProcessMessage(
                    summary="Generating artifact",
                    description=f"Generating artifact for trait data results matching: **{uri}**",
                )

                # Use validated response if available, otherwise fall back to raw data
                final_data = (
                    validated_response.model_dump()
                    if validated_response
                    else response_data
                )

                # Count results
                trait_count = self._count_traits(final_data)

                yield ArtifactMessage(
                    mimetype="application/json",
                    description=f"Trait data for taxon ID(s): {query_string}",
                    uris=[quote(uri)],
                    metadata={
                        "taxon_ids": taxon_ids,
                        "query_params": query_params,
                        "trait_count": trait_count,
                        "validated": validated_response is not None,
                    },
                )

                # Generate summary message
                summary_message = self._generate_summary_message(
                    final_data, trait_count, query_string, "trait"
                )
                yield TextMessage(text=summary_message)

                yield ProcessMessage(
                    summary="Trait data fetch completed",
                    description=f"Completed trait data retrieval for taxon ID(s): **{query_string}**",
                )

        except httpx.HTTPError as e:
            yield TextMessage(
                text=f"Failed to fetch trait data from TraitBank API: {str(e)}"
            )
        except Exception as e:
            yield TextMessage(text=f"Error processing trait data request: {str(e)}")

    def _count_taxon(self, response_data) -> int:
        """
        Count the total number of taxon records in the response.
        Handles null, empty, and malformed data gracefully.
        """
        try:
            if response_data is None:
                return 0

            if isinstance(response_data, dict):
                # Associative format: count all taxon records
                return len(response_data.keys()) if response_data else 0
            elif isinstance(response_data, list):
                # List format: count items in list
                return len(response_data) if response_data else 0
            return 0
        except (TypeError, AttributeError):
            return 0

    def _count_traits(self, response_data) -> int:
        """
        Count the total number of trait records in the response.
        Handles null, empty, and malformed data gracefully.
        """
        try:
            if response_data is None:
                return 0

            if isinstance(response_data, dict):
                # Associative format: count all traits across all taxa
                total = 0
                for traits in response_data.values():
                    if traits is None:
                        continue
                    elif isinstance(traits, list):
                        total += len(traits)
                    else:
                        total += 1
                return total
            elif isinstance(response_data, list):
                if not response_data:
                    return 0
                # List format: could be list of lists or single list
                if response_data and isinstance(response_data[0], list):
                    # List of lists format
                    return sum(
                        len(trait_list) if trait_list is not None else 0
                        for trait_list in response_data
                    )
                else:
                    # Single list format
                    return len(response_data)
            return 0
        except (TypeError, AttributeError, IndexError):
            return 0

    def _generate_summary_message(
        self, final_data, count: int, query: str, data_type: str, is_dict: bool = None
    ) -> str:
        """
        Generate appropriate summary message based on data format and count.
        """
        if count == 0:
            if data_type == "taxon":
                return f"No taxon records found for '{query}'. The taxon may not exist in the TraitBank database."
            else:
                return f"No trait records found for taxon ID(s): {query}. The taxon may not have associated traits in the TraitBank database."

        # Determine format description
        if is_dict is None:
            is_dict = isinstance(final_data, dict)

        format_desc = "associative array with taxon IDs as keys" if is_dict else "list"

        if data_type == "taxon":
            return f"Found {count} taxon record(s) for '{query}'. Results returned as {format_desc}."
        else:
            return f"Retrieved {count} trait record(s) for taxon ID(s): {query}. Results returned as {format_desc}."
