import pytest
from pydantic import ValidationError, BaseModel, field_validator
from typing import List, Optional, Union

from src.models.taxons import TaxonDataRequest, TaxonData
from src.models.traits import TraitDataRequest, TraitData

class TestTaxonDataRequest:
    def test_valid_request(self):
        request = TaxonDataRequest(
            query="Anadara",
            exact=True,
            verbose=True,
            assoc=False
        )
        assert request.query == "Anadara"
        assert request.exact is True

    def test_default_values(self):
        request = TaxonDataRequest(query="Anadara")
        assert request.exact is True
        assert request.verbose is False
        assert request.assoc is False

    def test_invalid_empty_query(self):
        with pytest.raises(ValidationError):
            TaxonDataRequest(query="")

class TestTraitDataRequest:
    def test_string_query(self):
        request = TraitDataRequest(query="94,95")
        assert request.query == "94,95"

    def test_list_query(self):
        request = TraitDataRequest(query=[94, 95])
        assert request.query == [94, 95]

    def test_mixed_list_query(self):
        request = TraitDataRequest(query=["94", 95])
        assert request.query == ["94", 95]
