from typing import Any
from typing import Dict as TypingDict
from typing import List as TypingList

import pytest
from ichatbio.types import (ArtifactMessage, Message, ProcessMessage,
                            TextMessage)

from src.agent import TraitBankAgent, TraitBankRequest


async def get_all_agent_messages(
    params_dict: TypingDict[str, Any],
) -> TypingList[Message]:
    """
    Runs the TraitBankAgent with the given request parameters and collects messages.
    """
    agent = TraitBankAgent()
    params_model = TraitBankRequest(**params_dict)
    messages_collected: TypingList[Message] = []
    async for message in agent.run(
        request="pytest_query", entrypoint="get_data", params=params_model
    ):
        messages_collected.append(message)
    return messages_collected


@pytest.mark.asyncio
async def test_agent_taxon_name_to_taxon_api_404_error():
    """
    Tests agent handling of a taxon name that results in a 404 from the taxon API.
    """
    params = {"name": "Anadara kagoshimensis"}
    messages = await get_all_agent_messages(params)

    assert messages, "Agent should yield messages"
    text_messages = [msg for msg in messages if isinstance(msg, TextMessage)]
    assert any(
        "API error fetching taxon data" in msg.text and "404" in msg.text
        for msg in text_messages
    ), "Expected a TextMessage indicating a 404 API error for taxon search"


@pytest.mark.asyncio
async def test_agent_valid_taxon_id_fetches_traits():
    """
    Tests agent successfully fetching trait data for a valid taxon ID.
    """
    params = {"id": "94"}  # Known to return trait data
    messages = await get_all_agent_messages(params)

    assert messages, "Agent should yield messages"
    assert any(
        isinstance(msg, ArtifactMessage) and msg.metadata.get("trait_count", 0) > 0
        for msg in messages
    ), "Expected an ArtifactMessage with trait data"

    process_messages = [msg for msg in messages if isinstance(msg, ProcessMessage)]
    assert any(
        "Completed trait data retrieval" in msg.description for msg in process_messages
    ), "Expected a ProcessMessage indicating completion of trait data retrieval"


@pytest.mark.asyncio
async def test_agent_multiple_valid_taxon_ids_fetches_traits():
    """
    Tests agent successfully fetching trait data for multiple valid taxon IDs.
    """
    params = {"id": "94,95"}  # 95 might not return data, but 94 should
    messages = await get_all_agent_messages(params)

    assert messages, "Agent should yield messages"
    # Check for an artifact that likely contains data for at least one ID
    assert any(
        isinstance(msg, ArtifactMessage) and "trait_count" in msg.metadata
        for msg in messages
    ), "Expected an ArtifactMessage for traits"
    # We expect trait_count > 0 if any ID returns data. Based on output, ID 94 has 40 traits.
    assert any(
        isinstance(msg, ArtifactMessage) and msg.metadata.get("trait_count", 0) > 0
        for msg in messages
    ), "Expected trait_count > 0 in artifact metadata"


@pytest.mark.asyncio
async def test_agent_non_existent_taxon_name():
    """
    Tests agent handling of a non-existent taxon name.
    """
    params = {"name": "NonExistentTaxonName123"}
    messages = await get_all_agent_messages(params)

    assert messages, "Agent should yield messages"
    text_messages = [msg for msg in messages if isinstance(msg, TextMessage)]
    assert any(
        "API error fetching taxon data" in msg.text and "404" in msg.text
        for msg in text_messages
    ), "Expected a TextMessage indicating a 404 API error for taxon search"


@pytest.mark.asyncio
async def test_agent_non_existent_taxon_id():
    """
    Tests agent handling of a non-existent taxon ID for traits.
    """
    params = {"id": "000000"}
    messages = await get_all_agent_messages(params)

    assert messages, "Agent should yield messages"
    text_messages = [msg for msg in messages if isinstance(msg, TextMessage)]
    assert any(
        "API error fetching trait data" in msg.text and "404" in msg.text
        for msg in text_messages
    ), "Expected a TextMessage indicating a 404 API error for trait search"


@pytest.mark.asyncio
async def test_agent_name_priority_taxon_ok_trait_error():
    """
    Tests agent prioritizing name, taxon search succeeds, but subsequent trait search fails.
    """
    params = {
        "name": "Anadara",
        "id": "12345",
    }  # 'Anadara' resolves to '93', traits for '93' 404
    messages = await get_all_agent_messages(params)

    assert messages, "Agent should yield messages"

    # Check for successful taxon artifact
    taxon_artifacts = [
        msg
        for msg in messages
        if isinstance(msg, ArtifactMessage) and "taxon_name_query" in msg.metadata
    ]
    assert any(
        msg.metadata.get("retrieved_taxon_ids") == ["93"] for msg in taxon_artifacts
    ), "Expected ArtifactMessage for taxon 'Anadara' resolving to ID '93'"

    # Check for trait fetch error message
    text_messages = [msg for msg in messages if isinstance(msg, TextMessage)]
    assert any(
        "API error fetching trait data for ID(s) '93'" in msg.text and "404" in msg.text
        for msg in text_messages
    ), "Expected a TextMessage indicating a 404 API error for trait search for ID '93'"


def test_agent_request_validation_fails_no_input():
    """
    Tests that TraitBankRequest raises ValueError if neither name nor id is provided.
    """
    with pytest.raises(ValueError, match='Either "name" or "id" must be provided.'):
        TraitBankRequest(**{})


@pytest.mark.asyncio
async def test_agent_handles_empty_id_string_gracefully():
    """
    Tests agent handling of an empty string or only commas for taxon ID.
    """
    params = {"id": ",,"}
    messages = await get_all_agent_messages(params)

    assert messages, "Agent should yield messages"
    text_messages = [msg for msg in messages if isinstance(msg, TextMessage)]
    assert any(
        "No valid taxon IDs provided in input" in msg.text for msg in text_messages
    ), "Expected a TextMessage indicating no valid taxon IDs were provided"
