from typing import Optional, Any, List, Dict
from typing_extensions import override

import httpx
from pydantic import BaseModel, ValidationError

from ichatbio.agent import IChatBioAgent
from ichatbio.agent_response import ResponseContext, IChatBioAgentProcess
from ichatbio.types import (
    AgentCard,
    AgentEntrypoint,
)

from .tools import TraitBankTools
from .models import TraitBankRequest, TaxonDataResponse, TraitDataResponse



trait_bank_agent_card = AgentCard(
    name="Trait Bank Agent",
    description="""Agent that retrieves trait data from the Trait Bank API.
    If a taxon name is provided, it first resolves taxon IDs, then fetches traits.
    If taxon ID(s) are provided, it directly fetches traits.
    Uses optimized settings: exact=True for taxon searches, verbose=True, assoc=True.
    Trait Bank API URL: https://traitbank-reconnect.hcmr.gr/""",
    icon=None,
    entrypoints=[
        AgentEntrypoint(
            id="get_data",
            description="Fetch trait data. Provide taxon name (to resolve IDs first) or direct taxon ID(s).",
            parameters=TraitBankRequest,
        ),
    ],
)


class TraitBankAgent(IChatBioAgent):
    def __init__(self):
        self.agent_card = trait_bank_agent_card
        self.tools = TraitBankTools()


    @override
    def get_agent_card(self) -> AgentCard:
        return self.agent_card


    @override
    async def run(
        self, context: ResponseContext, request: str, entrypoint: str, params: Optional[BaseModel]
    ):
        if entrypoint != "get_data":
            await context.reply(
                f"Unknown entrypoint: {entrypoint}"
            )
            return
        if not isinstance(params, TraitBankRequest):
            await context.reply(
                "Invalid parameters for get_data. Expected TraitBankRequest."
            )
            return


        async with context.begin_process(summary="TraitBank data retrieval") as process:
            process: IChatBioAgentProcess
            target_taxon_ids_str: Optional[str] = None
            # Used for final trait fetching messages
            query_identifier_for_traits: str = ""

            try:
                if params.name:
                    process_step_description_prefix = f"for name '{params.name}'"
                    await process.log(
                        "Taxon name provided",
                        data={"name": params.name}
                    )

                    raw_taxon_data: Optional[Dict[Any, Any]] = None
                    taxon_uri: Optional[str] = None
                    
                    error_message = ""
                    try:
                        raw_taxon_data, taxon_uri = await self.tools.fetch_taxon_data_by_name(params.name)
                    except httpx.HTTPStatusError as e:
                        error_message = f"API error fetching taxon data {process_step_description_prefix}: {e.response.status_code} {e.response.reason_phrase}. URL: {e.request.url}"
                    except httpx.RequestError as e:
                        error_message = f"Request error fetching taxon data {process_step_description_prefix}: {str(e)}. URL: {e.request.url}"
                    except Exception as e:
                        error_message = f"Error calling taxon data tool {process_step_description_prefix}: {str(e)}"

                    if error_message or raw_taxon_data is None:
                        if not error_message:
                            error_message = f"No data returned from taxon search API {process_step_description_prefix}."
                        await context.reply(error_message)
                        return
                    
                    validated_taxon_response: Optional[TaxonDataResponse] = None
                    taxon_data_root: Optional[Dict[str, Any]] = None
                    try:
                        validated_taxon_response = TaxonDataResponse.model_validate(raw_taxon_data)
                        taxon_data_root = validated_taxon_response.root
                        await process.log("Successfully validated API response for taxon data", data={"name": params.name})
                    except ValidationError as ve:
                        await context.reply(
                            f"Warning: Taxon API response validation failed {process_step_description_prefix}: {str(ve)}. Trait fetching cannot proceed."
                        )
                        return

                    taxon_count = self._count_taxon_records(taxon_data_root)
                    
                    found_taxon_ids: List[str] = []
                    if taxon_count > 0 and taxon_data_root:
                        found_taxon_ids = [str(tid).strip() for tid in taxon_data_root.keys() if str(tid).strip()]
                    
                    taxon_metadata = {
                        "taxon_name_query": params.name,
                        "query_params": self.tools._get_query_params(data_type="taxon"),
                        "result_count": taxon_count,
                        "validated": validated_taxon_response is not None,
                        "retrieved_taxon_ids": found_taxon_ids,
                        "taxon_data_root": taxon_data_root,
                    }
                    await process.create_artifact(
                        mimetype="application/json",
                        description=f"Taxon search results {process_step_description_prefix}",
                        uris=[taxon_uri] if taxon_uri else [],
                        metadata=taxon_metadata,
                    )
                    await process.log(self._generate_summary_text(taxon_data_root, taxon_count, params.name, "taxon"))

                    if not found_taxon_ids:
                        await context.reply(
                            f"No matching taxon IDs found {process_step_description_prefix}. Unable to proceed to fetch trait data."
                        )
                        return
                    # This will be used for trait messages
                    target_taxon_ids_str = ",".join(found_taxon_ids)
                    query_identifier_for_traits = target_taxon_ids_str

                    await process.log(
                        f"Successfully resolved taxon ID(s): {target_taxon_ids_str} {process_step_description_prefix}.",
                        data={"taxon_ids": found_taxon_ids}
                    )
                elif params.id:
                    valid_ids = [tid.strip() for tid in params.id.split(",") if tid.strip()]
                    if not valid_ids:
                        await context.reply(f"No valid taxon IDs provided in input: '{params.id}'.")
                        return
                    target_taxon_ids_str = ",".join(valid_ids)
                    query_identifier_for_traits = target_taxon_ids_str
                    await process.log(
                        f"Using provided taxon ID(s): {target_taxon_ids_str}.",
                        data={"taxon_ids": valid_ids}
                    )
                else:
                    await context.reply("Internal error: No taxon name or ID was specified after request validation.")
                    return

                # Fetch trait data if we have target_taxon_ids_str
                if not target_taxon_ids_str:
                    await context.reply(f"No target taxon IDs to fetch trait data for.")
                    return

                await process.log(
                    f"Fetching trait data for taxon ID(s): {query_identifier_for_traits}.",
                    data={"taxon_ids": query_identifier_for_traits}
                )
                
                raw_trait_data: Optional[Dict[Any, Any]] = None
                trait_uri: Optional[str] = None
                error_message = ""
                try:
                    raw_trait_data, trait_uri = await self.tools.fetch_trait_data_by_ids(target_taxon_ids_str)
                except httpx.HTTPStatusError as e:
                    error_message = (
                        f"API error fetching trait data for ID(s) '{query_identifier_for_traits}': "
                        f"{e.response.status_code} {e.response.reason_phrase}. URL: {e.request.url}"
                    )
                except httpx.RequestError as e:
                    error_message = (
                        f"Request error fetching trait data for ID(s) '{query_identifier_for_traits}': "
                        f"{str(e)}. URL: {e.request.url}"
                    )
                except Exception as e:
                    error_message = (
                        f"Error calling trait data tool for ID(s) '{query_identifier_for_traits}': {str(e)}"
                    )

                if error_message or raw_trait_data is None:
                    if not error_message:
                        error_message = f"No data returned from trait API for ID(s) '{query_identifier_for_traits}'."
                    await context.reply(error_message)
                    return

                validated_trait_response: Optional[TraitDataResponse] = None
                trait_data_root: Optional[Dict[str, List[Any]]] = None
                is_trait_data_validated = False

                try:
                    validated_trait_response = TraitDataResponse.model_validate(raw_trait_data)
                    trait_data_root = validated_trait_response.root
                    is_trait_data_validated = True
                    await process.log(
                        f"Successfully validated API response for trait data for ID(s) '{query_identifier_for_traits}'."
                    )
                except ValidationError as ve:
                    await context.reply(
                        f"Warning: Trait API response validation failed for ID(s) '{query_identifier_for_traits}': {str(ve)}. Proceeding with raw data."
                    )
                    trait_data_root = raw_trait_data
                    is_trait_data_validated = False

                if trait_data_root is None:
                    await context.reply(f"Trait data is unexpectedly None after validation attempt for ID(s) '{query_identifier_for_traits}'. Cannot proceed.")
                    return

                trait_count = self._count_trait_records(trait_data_root)
                # If trait_count is 0 and we have raw_trait_data, it means no traits were found
                if trait_count == 0 and not is_trait_data_validated:
                    await context.reply(f"No parsable trait records found in the raw (unvalidated) data for ID(s) '{query_identifier_for_traits}'.")

                trait_metadata = {
                    "taxon_ids_queried": query_identifier_for_traits.split(','),
                    "query_params": self.tools._get_query_params(data_type="trait"),
                    "trait_count": trait_count,
                    "validated": is_trait_data_validated,
                    "trait_data_root": trait_data_root,
                }
                await process.create_artifact(
                    mimetype="application/json",
                    description=f"Trait data for taxon ID(s): {query_identifier_for_traits}{'' if is_trait_data_validated else ' (validation failed, raw data)'}",
                    uris=[trait_uri] if trait_uri else [],
                    metadata=trait_metadata,
                )
                await process.log(self._generate_summary_text(trait_data_root, trait_count, query_identifier_for_traits, "trait"))
                await process.log(f"Completed trait data retrieval for ID(s): {query_identifier_for_traits}")

            except ValueError as ve:
                await context.reply(f"Invalid input parameters: {str(ve)}")
            except Exception as e:
                await context.reply(f"An unexpected error occurred in the agent: {str(e)}")


    # Helper methods for counting and summary, now in the agent
    def _count_taxon_records(self, taxon_data_root: Optional[Dict[str, Any]]) -> int:
        """Counts records from the .root of TaxonDataResponse."""
        if taxon_data_root is None or not isinstance(taxon_data_root, dict):
            return 0
        return len(taxon_data_root.keys())


    def _count_trait_records(self, trait_data_root: Optional[Dict[str, List[Any]]]) -> int:
        """Counts records from the .root of TraitDataResponse."""
        if trait_data_root is None or not isinstance(trait_data_root, dict):
            return 0
        total_traits = 0
        for traits_list in trait_data_root.values():
            if isinstance(traits_list, list):
                total_traits += len(traits_list)
        return total_traits


    def _generate_summary_text(
        self, data_root: Optional[Dict[Any, Any]], count: int, query_identifier: str, data_type: str
    ) -> str:
        """Generates summary text based on processed data root."""
        format_desc = "associative array (dictionary) with taxon IDs as keys"
        if count == 0:
            if data_type == "taxon":
                return f"No taxon records found for name '{query_identifier}'."
            else:
                return f"No trait records found for taxon ID(s): {query_identifier}."

        if data_type == "taxon":
            return f"Found {count} taxon record(s) for name '{query_identifier}'. Results returned as {format_desc}."
        else:
            num_taxa_with_traits = 0
            # data_root is the dict of taxon_id -> list_of_traits
            if isinstance(data_root, dict):
                num_taxa_with_traits = len(data_root.keys())
            
            if num_taxa_with_traits > 0:
                return f"Retrieved {count} trait record(s) across {num_taxa_with_traits} taxon/taxa for ID(s): {query_identifier}. Results returned as {format_desc}."
            else:
                return f"Retrieved {count} trait record(s) for taxon ID(s): {query_identifier}. Results returned as {format_desc}."
