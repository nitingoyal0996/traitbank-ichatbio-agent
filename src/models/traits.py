from typing import Dict, List, Optional, Union
from pydantic import BaseModel, RootModel, Field

class TraitDataRequest(BaseModel):
    """
    Request model for the TraitBank Traits API.
    
    This API retrieves trait information for one or more taxon identifiers.
    Returns comprehensive biological trait data including categories, values,
    and supporting literature references.
    
    Response Structure:
    - When verbose=False: Returns minimal trait data (trait, category, value only)
    - When verbose=True: Returns complete trait data including references and metadata
    - When assoc=False: Returns a list of trait records for each taxon
    - When assoc=True: Returns a dictionary with taxon IDs as keys
    
    Example Usage:
        request = TraitDataRequest(
            query="94,95",
            verbose=True,
            assoc=True
        )
        
        # Alternative with list input
        request = TraitDataRequest(
            query=[94, 95],
            verbose=True,
            assoc=True
        )
    """
    query: Union[str, List[Union[str, int]]] = Field(
        ..., 
        description="One or more taxon identifiers. Can be comma-separated string or list of IDs. Up to 10 IDs allowed.",
        example="94,95"
    )
    verbose: Optional[bool] = Field(
        True, 
        description="When True, returns comprehensive trait data with references and metadata. When False, returns minimal trait information.",
        example=True
    )
    assoc: Optional[bool] = Field(
        True, 
        description="When True, returns data as a dictionary with taxon IDs as keys. When False, returns a list of trait records.",
        example=True
    )

class TraitData(BaseModel):
    """
    Complete trait record with full taxonomic and reference information.
    
    This model represents the comprehensive trait data returned when verbose=True.
    Contains taxonomic details, trait information, literature references, and
    data provenance metadata for full scientific traceability.
    """
    # Taxonomic Information
    taxon: Optional[str] = Field(
        None, 
        description="Scientific name of the taxon for which the trait information was recorded",
        example="Anadara kagoshimensis"
    )
    author: Optional[str] = Field(
        None, 
        description="Taxonomic authority (author and year) of the taxon",
        example="(Tokunaga, 1906)"
    )
    rank: Optional[str] = Field(
        None, 
        description="Taxonomic rank of the taxon (e.g., Species, Genus, Family)",
        example="Species"
    )
    valid_taxon: Optional[str] = Field(
        None, 
        description="Currently accepted scientific name according to the database",
        example="Anadara kagoshimensis"
    )
    valid_author: Optional[str] = Field(
        None, 
        description="Taxonomic authority for the currently accepted name",
        example="(Tokunaga, 1906)"
    )
    taxonomic_status: Optional[str] = Field(
        None, 
        description="Taxonomic status of the name (e.g., 'valid', 'synonym', 'invalid')",
        example="valid"
    )
    source_of_synonymy: Optional[Union[str, bool]] = Field(
        None, 
        description="Literature reference supporting synonymy status. False if no synonymy information available",
        example=False
    )
    parent: Optional[str] = Field(
        None, 
        description="Direct parent taxon in the taxonomic classification",
        example="Anadara"
    )
    
    # Trait Information
    trait: Optional[str] = Field(
        None, 
        description="Name of the biological trait category",
        example="Body Size"
    )
    category: Optional[str] = Field(
        None, 
        description="Specific sub-category or value within the trait",
        example="small-medium"
    )
    category_abbreviation: Optional[str] = Field(
        None, 
        description="Abbreviated code for the trait category, useful for data analysis",
        example="BS2"
    )
    traitvalue: Optional[Union[str, int]] = Field(
        None, 
        description="Affinity score (0-3): 0=no affinity, 1=low affinity, 2=high affinity with alternatives, 3=exclusive affinity",
        example="3"
    )
    
    # Reference and Provenance
    reference: Optional[str] = Field(
        None, 
        description="Full literature citation supporting the trait assignment",
        example="Sahin, C., Emiral, H., et al. (2009) The benthic exotic species of the Black Sea..."
    )
    doi: Optional[Union[str, bool]] = Field(
        None, 
        description="Digital Object Identifier (DOI) of the reference. False if not available",
        example="10.1017/S0025315414002045"
    )
    
    # Data Entry Metadata
    value_creator: Optional[str] = Field(
        None, 
        description="Person who assigned the trait value to the taxon",
        example="Stefania Klayn"
    )
    value_creation_date: Optional[str] = Field(
        None, 
        description="Date and time when the trait assignment was entered into the database",
        example="2019-06-30 12:11:14"
    )
    value_modified_by: Optional[str] = Field(
        None, 
        description="Person who last modified the trait value. Empty if no modifications made",
        example="Stefania Klayn"
    )
    value_modification_date: Optional[str] = Field(
        None, 
        description="Date and time of last modification. Equals creation date if never modified",
        example="2019-06-30 12:11:14"
    )
    
    # Text Evidence
    text_excerpt: Optional[str] = Field(
        None, 
        description="Direct quotation from the literature source supporting the trait assignment",
        example="Mean length and weight values of blood-cockle..."
    )
    text_excerpt_creator: Optional[Union[str, bool]] = Field(
        None, 
        description="Person who entered the text excerpt. False if no excerpt provided",
        example="Stefania Klayn"
    )
    text_excerpt_creation_date: Optional[Union[str, bool]] = Field(
        None, 
        description="Date and time when the text excerpt was entered. False if no excerpt provided",
        example="2019-06-30 12:13:09"
    )
    text_excerpt_modified_by: Optional[Union[str, bool]] = Field(
        None, 
        description="Person who last modified the text excerpt. False if no modifications or no excerpt",
        example="Stefania Klayn"
    )
    text_excerpt_modification_date: Optional[Union[str, bool]] = Field(
        None, 
        description="Date and time of last excerpt modification. False if no modifications or no excerpt",
        example="2019-06-30 12:13:09"
    )

class TraitDataMinimal(BaseModel):
    """
    Minimal trait record containing only essential trait information.
    
    This model represents the basic trait data returned when verbose=False.
    Suitable for lightweight operations where only core trait information is needed
    without taxonomic details or reference metadata.
    """
    trait: Optional[str] = Field(
        None, 
        description="Name of the biological trait category",
        example="Body Size"
    )
    category: Optional[str] = Field(
        None, 
        description="Specific sub-category or value within the trait",
        example="small-medium"
    )
    traitvalue: Optional[Union[str, int]] = Field(
        None, 
        description="Affinity score (0-3): 0=no affinity, 1=low affinity, 2=high affinity with alternatives, 3=exclusive affinity",
        example="3"
    )

class TraitDataResponse(RootModel):
    """
    Response model for the TraitBank Traits API.
    
    This model handles all possible response formats based on the combination
    of 'verbose' and 'assoc' parameters in the request:
    
    Response Formats:
    1. assoc=True, verbose=True: Dict[taxonID, List[TraitData]]
       - Dictionary mapping taxon IDs to lists of complete trait records
    
    2. assoc=False, verbose=True: List[List[TraitData]]
       - List of lists, where each inner list contains complete trait records for one taxon
    
    3. assoc=False, verbose=False: List[List[TraitDataMinimal]]
       - List of lists, where each inner list contains minimal trait records for one taxon
    
    Note: The combination assoc=True + verbose=False is supported and returns
    Dict[taxonID, List[TraitDataMinimal]].
    
    Example Response (assoc=True, verbose=True):
        {
            "94": [
                {
                    "taxon": "Anadara kagoshimensis",
                    "trait": "Body Size",
                    "category": "small-medium",
                    "traitvalue": "3",
                    "reference": "Sahin, C., et al. (2009)...",
                    "value_creator": "Stefania Klayn"
                }
            ]
        }
    
    Example Response (assoc=False, verbose=False):
        [
            [
                {
                    "trait": "Body Size",
                    "category": "small-medium", 
                    "traitvalue": "3"
                }
            ]
        ]
    """
    root: Union[
        Dict[Union[str, int], List[TraitData]],         # assoc=1, verbose=1
        Dict[Union[str, int], List[TraitDataMinimal]],  # assoc=1, verbose=0
        List[List[TraitData]],                          # assoc=0, verbose=1
        List[List[TraitDataMinimal]]                    # assoc=0, verbose=0
    ]
