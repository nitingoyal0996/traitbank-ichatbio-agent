from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class TraitBankRequest(BaseModel):
    """
    Request model for TraitBank data retrieval.
    Provide either a taxon name to search for taxon information,
    or a taxon ID (or comma-separated IDs) to retrieve trait data.
    If both name and id are provided, name will be prioritized.
    """

    name: Optional[str] = Field(
        default=None,
        description="Taxon name to search for (e.g., 'Homo sapiens'). Prioritized if both name and id are given.",
        examples=["Homo sapiens", "Anadara"],
    )
    id: Optional[str] = Field(
        default=None,
        description="Taxon ID or comma-separated taxon IDs (e.g., '12345', '94,95'). Used if name is not provided.",
        examples=["12345", "94,95"],
    )

    @model_validator(mode="before")
    @classmethod
    def check_and_prioritize_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            name = data.get("name")
            taxon_id = data.get("id")

            if name and taxon_id:
                # If both name and id are present, prioritize name by nullifying id.
                data["id"] = None
            elif not name and not taxon_id:
                raise ValueError('Either "name" or "id" must be provided.')
        return data
