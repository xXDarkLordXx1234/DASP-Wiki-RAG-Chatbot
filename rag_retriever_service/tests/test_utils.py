import os
import yaml
import pytest
import sys

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)


from rag_retriever_service.src.utils.utils import (
    convert_list_to_float,
    map_usergroups_from_keycloak_to_usergroups_of_dasp_wikirag,
    perform_standard_mapping
)

def test_convert_list_to_float():
    """
    Test that only convertible elements are converted to floats.
    """
    input_list = ["1", 2, "abc", 3.4, None, "5.6"]
    # Expected conversion: "1" -> 1.0, 2 -> 2.0, 3.4 remains, "5.6" -> 5.6.
    expected_output = [1.0, 2.0, 3.4, 5.6]
    assert convert_list_to_float(input_list) == expected_output


def test_map_usergroups_file_not_exist(monkeypatch):
    """
    Test that if the mapping file does not exist, the original values are returned.
    """
    test_values = ["/DMHWebGroup", "/WikiAdmin"]
    non_existent_file = "nonexistent_mapping.yml"
    
    # Monkeypatch os.path.exists so that it returns False for our test file.
    monkeypatch.setattr(os.path, "exists", lambda path: False if path == non_existent_file else os.path.exists(path))
    
    result = map_usergroups_from_keycloak_to_usergroups_of_dasp_wikirag(test_values, mapping_file=non_existent_file)
    assert result == test_values


def test_map_usergroups_empty_mapping_file(tmp_path):
    """
    Test that if the mapping file is empty, standard mapping is applied to each value.
    """
    # Create an empty mapping file.
    mapping_file = tmp_path / "empty_mapping.yml"
    mapping_file.write_text("")  # Write an empty file.
    
    test_values = ["/DMHWebGroup", "/DigitalMentalHealth"]
    # With empty mapping, each value should be transformed using perform_standard_mapping.
    expected = [perform_standard_mapping(v) for v in test_values]
    
    result = map_usergroups_from_keycloak_to_usergroups_of_dasp_wikirag(test_values, mapping_file=str(mapping_file))
    assert result == expected


def test_map_usergroups_invalid_mapping_file(tmp_path):
    """
    Test that if the YAML in the mapping file is invalid, the original values are returned.
    """
    mapping_file = tmp_path / "invalid_mapping.yml"
    mapping_file.write_text(":::: invalid YAML :::")  # Write invalid YAML.
    
    test_values = ["/DMHWebGroup", "/WikiAdmin"]
    # When parsing fails, the function returns the original values.
    result = map_usergroups_from_keycloak_to_usergroups_of_dasp_wikirag(test_values, mapping_file=str(mapping_file))
    assert result == test_values


def test_map_usergroups_valid_mapping_file(tmp_path):
    """
    Test that when a valid mapping file is provided, the mappings are applied.
    """
    mapping_file = tmp_path / "valid_mapping.yml"
    # Create a valid YAML mapping file.
    mapping_content = {
        "mappings": {
            "/DMHWebGroup": "Group1",
            "/DigitalMentalHealth": "Group2"
        }
    }
    mapping_file.write_text(yaml.dump(mapping_content))
    
    test_values = ["/DMHWebGroup", "/WikiAdmin", "/DigitalMentalHealth"]
    # Expected:
    #   - /DMHWebGroup maps to "Group1"
    #   - /DigitalMentalHealth maps to "Group2"
    #   - /WikiAdmin is not in the mapping so standard mapping applies: "Main.WikiAdmin"
    expected = ["Group1", perform_standard_mapping("/WikiAdmin"), "Group2"]
    
    result = map_usergroups_from_keycloak_to_usergroups_of_dasp_wikirag(test_values, mapping_file=str(mapping_file))
    assert result == expected
