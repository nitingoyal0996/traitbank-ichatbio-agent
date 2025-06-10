from typing import List, Dict, Optional, Union
from pydantic import BaseModel, RootModel, Field, field_validator

class TaxonDataRequest(BaseModel):
    """
    Request model for the TraitBank Taxon API.
    
    This API searches for taxa in the TraitBank database and returns internal 
    matching taxon identifiers which can then be used to query for traits.
    
    Response Structure:
    - When verbose=False: Returns minimal taxon data (taxonID, taxon name only)
    - When verbose=True: Returns complete taxon data including taxonomic hierarchy
    - When assoc=False: Returns a list of taxon records
    - When assoc=True: Returns a dictionary with taxon IDs as keys
    
    Example Usage:
        request = TaxonDataRequest(
            query="Anadara",
            exact=False,
            verbose=True,
            assoc=True
        )
    """
    query: str = Field(
        ..., 
        description="Taxon name to search for. Spaces must be URL-encoded. Search is case-insensitive.",
        example="Anadara kagoshimensis"
    )
    exact: Optional[bool] = Field(
        True, 
        description="When True, returns only exact matches. When False, returns all taxa beginning with the query string.",
        example=False
    )
    verbose: Optional[bool] = Field(
        False, 
        description="When True, returns detailed taxonomic information. When False, returns minimal data (ID and name only).",
        example=True
    )
    assoc: Optional[bool] = Field(
        False, 
        description="When True, returns data as a dictionary with taxon IDs as keys. When False, returns a list.",
        example=True
    )


    @field_validator('query')
    @classmethod
    def validate_query_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        return v


class TaxonData(BaseModel):
    """
    Complete taxon record with full taxonomic information.
    
    This model represents the comprehensive taxon data returned when `verbose=True`.
    Contains taxonomic hierarchy, validity status, and source information.
    """
    taxonID: Optional[Union[str, int]] = Field(
        None, 
        description="Unique internal identifier for the taxon in the TraitBank database",
        example="94"
    )
    taxon: Optional[str] = Field(
        None, 
        description="Scientific name of the taxon as recorded in the database",
        example="Anadara kagoshimensis"
    )
    author: Optional[str] = Field(
        None, 
        description="Taxonomic authority (author and year) for the taxon name",
        example="(Tokunaga, 1906)"
    )
    rank: Optional[str] = Field(
        None, 
        description="Taxonomic rank of the taxon (e.g., Species, Genus, Family)",
        example="Species"
    )
    validID: Optional[Union[str, int]] = Field(
        None, 
        description="Internal ID of the currently accepted valid taxon. Equals taxonID if this taxon is accepted",
        example="94"
    )
    valid_taxon: Optional[str] = Field(
        None, 
        description="Currently accepted scientific name. Equals 'taxon' field if this taxon is accepted",
        example="Anadara kagoshimensis"
    )
    valid_author: Optional[str] = Field(
        None, 
        description="Taxonomic authority for the currently accepted name. Equals 'author' field if this taxon is accepted",
        example="(Tokunaga, 1906)"
    )
    status: Optional[str] = Field(
        None, 
        description="Taxonomic status indicating validity (e.g., 'accepted', 'synonym', 'invalid')",
        example="accepted"
    )
    source_of_synonymy: Optional[Union[str, bool]] = Field(
        None, 
        description="Literature reference supporting synonymy status. False if no synonymy information available",
        example=False
    )


class TaxonDataMinimal(BaseModel):
    """
    Minimal taxon record containing only essential identifiers.
    
    This model represents the basic taxon data returned when `verbose=False`.
    Suitable for lightweight operations where only identification is needed.
    """
    taxonID: Optional[Union[str, int]] = Field(
        None, 
        description="Unique internal identifier for the taxon in the TraitBank database",
        example="94"
    )
    taxon: Optional[str] = Field(
        None, 
        description="Scientific name of the taxon as recorded in the database",
        example="Anadara kagoshimensis"
    )


class TaxonDataResponse(RootModel):
    """
    Response model for the TraitBank Taxon API.
    
    This model handles all possible response formats based on the combination
    of 'verbose' and 'assoc' parameters in the request:
    
    Response Formats:
    1. assoc=True, verbose=True: Dict[taxonID, TaxonDataVerbose]
       - Dictionary mapping taxon IDs to complete taxon records
    
    2. assoc=False, verbose=True: List[TaxonDataVerbose] 
       - List of complete taxon records
    
    3. assoc=False, verbose=False: List[TaxonDataMinimal]
       - List of minimal taxon records (ID and name only)
    
    Note: The combination assoc=True + verbose=False is not supported by the API.
    
    Example Response (assoc=True, verbose=True):
        {
            "94": {
                "taxonID": "94",
                "taxon": "Anadara kagoshimensis",
                "author": "(Tokunaga, 1906)",
                "rank": "Species",
                "status": "accepted"
            }
        }
    """
    root: Union[
        Dict[Union[str, int], TaxonData],   # assoc=1, verbose=1
        List[TaxonData],                    # assoc=0, verbose=1
        List[TaxonDataMinimal]              # assoc=0, verbose=0
    ]
