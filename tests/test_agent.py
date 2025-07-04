import pytest
from ichatbio.agent_response import (ArtifactResponse, DirectResponse,
                                        ProcessLogResponse, ResponseChannel,
                                        ResponseContext, ResponseMessage)

from src.agent import TraitBankAgent, TraitBankRequest

TEST_CONTEXT_ID = "617727d1-4ce8-4902-884c-db786854b51c"


class InMemoryResponseChannel(ResponseChannel):
    def __init__(self, message_buffer: list):
        self.message_buffer = message_buffer

    async def submit(self, message: ResponseMessage, context_id: str):
        self.message_buffer.append(message)


@pytest.fixture(scope="function")
def messages() -> list[ResponseMessage]:
    return []


@pytest.fixture(scope="function")
def context(messages) -> ResponseContext:
    return ResponseContext(InMemoryResponseChannel(messages), TEST_CONTEXT_ID)


async def get_all_agent_messages(params_dict, context, messages):
    agent = TraitBankAgent()
    params_model = TraitBankRequest(**params_dict)
    await agent.run(
        context, request="pytest_query", entrypoint="get_data", params=params_model
    )
    return messages


@pytest.mark.asyncio
async def test_agent_taxon_name_to_taxon_api_404_error(context, messages):
    params = {"name": "Anadara kagoshimensis"}
    msgs = await get_all_agent_messages(params, context, messages)
    assert msgs, "Agent should yield messages"
    text_msgs = [m for m in msgs if isinstance(m, DirectResponse)]
    assert any(
        "API error fetching taxon data" in m.text and "404" in m.text for m in text_msgs
    ), "Expected a DirectResponse indicating a 404 API error for taxon search"


@pytest.mark.asyncio
async def test_agent_valid_taxon_id_fetches_traits(context, messages):
    params = {"id": "94"}
    msgs = await get_all_agent_messages(params, context, messages)
    assert msgs, "Agent should yield messages"
    assert any(
        isinstance(m, ArtifactResponse)
        and m.metadata
        and m.metadata.get("trait_count", 0) > 0
        for m in msgs
    ), "Expected an ArtifactResponse with trait data"
    process_logs = [m for m in msgs if isinstance(m, ProcessLogResponse)]
    assert any(
        "Completed trait data retrieval" in m.text for m in process_logs
    ), "Expected a ProcessLogResponse indicating completion of trait data retrieval"


@pytest.mark.asyncio
async def test_agent_multiple_valid_taxon_ids_fetches_traits(context, messages):
    """
    Tests agent successfully fetching trait data for multiple valid taxon IDs.
    """
    params = {"id": "94,95"}  # 95 might not return data, but 94 should
    messages = await get_all_agent_messages(params, context, messages)
    assert messages, "Agent should yield messages"
    assert any(
        isinstance(msg, ArtifactResponse) and msg.metadata and "trait_count" in msg.metadata
        for msg in messages
    ), "Expected an ArtifactResponse for traits"
    # We expect trait_count > 0 if any ID returns data. Based on output, ID 94 has 40 traits.
    assert any(
        isinstance(msg, ArtifactResponse)
        and msg.metadata
        and msg.metadata.get("trait_count", 0) > 0
        for msg in messages
    ), "Expected trait_count > 0 in artifact metadata"


@pytest.mark.asyncio
async def test_agent_non_existent_taxon_name(context, messages):
    """
    Tests agent handling of a non-existent taxon name.
    """
    params = {"name": "NonExistentTaxonName123"}
    messages = await get_all_agent_messages(params, context, messages)

    assert messages, "Agent should yield messages"
    text_messages = [msg for msg in messages if isinstance(msg, DirectResponse)]
    assert any(
        "API error fetching taxon data" in msg.text and "404" in msg.text for msg in text_messages
    ), "Expected a DirectResponse indicating a 404 API error for taxon search"


@pytest.mark.asyncio
async def test_agent_non_existent_taxon_id(context, messages):
    """
    Tests agent handling of a non-existent taxon ID for traits.
    """
    params = {"id": "000000"}
    messages = await get_all_agent_messages(params, context, messages)

    assert messages, "Agent should yield messages"
    text_messages = [msg for msg in messages if isinstance(msg, DirectResponse)]
    assert any(
        "API error fetching trait data" in msg.text and "404" in msg.text for msg in text_messages
    ), "Expected a DirectResponse indicating a 404 API error for trait search"


@pytest.mark.asyncio
async def test_agent_name_priority_taxon_ok_trait_error(context, messages):
    """
    Tests agent prioritizing name, taxon search succeeds, but subsequent trait search fails.
    """
    params = {
        "name": "Anadara",
        "id": "12345",
    }  # 'Anadara' resolves to '93', traits for '93' 404
    messages = await get_all_agent_messages(params, context, messages)

    assert messages, "Agent should yield messages"

    # Check for successful taxon artifact
    taxon_artifacts = [
        msg
        for msg in messages
        if isinstance(msg, ArtifactResponse) and msg.metadata is not None and "taxon_name_query" in msg.metadata
    ]
    assert any(
        msg.metadata.get("retrieved_taxon_ids") == ["93"] for msg in taxon_artifacts
    ), "Expected ArtifactResponse for taxon 'Anadara' resolving to ID '93'"

    # Check for trait fetch error message
    text_messages = [msg for msg in messages if isinstance(msg, DirectResponse)]
    assert any(
        "API error fetching trait data for ID(s) '93'" in msg.text and "404" in msg.text
        for msg in text_messages
    ), "Expected a DirectResponse indicating a 404 API error for trait search for ID '93'"


def test_agent_request_validation_fails_no_input():
    """
    Tests that TraitBankRequest raises ValueError if neither name nor id is provided.
    """
    with pytest.raises(ValueError, match='Either "name" or "id" must be provided.'):
        TraitBankRequest(**{})


@pytest.mark.asyncio
async def test_agent_handles_empty_id_string_gracefully(context, messages):
    """
    Tests agent handling of an empty string or only commas for taxon ID.
    """
    params = {"id": ",,"}
    messages = await get_all_agent_messages(params, context, messages)
    assert messages, "Agent should yield messages"
    text_messages = [msg for msg in messages if isinstance(msg, DirectResponse)]
    assert any(
        "No valid taxon IDs provided in input" in msg.text for msg in text_messages
    ), "Expected a DirectResponse indicating no valid taxon IDs were provided"
