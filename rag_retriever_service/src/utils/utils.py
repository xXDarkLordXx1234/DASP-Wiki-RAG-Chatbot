import yaml
import os
from typing import Any, List

def convert_list_to_float(input_list: List[Any]) -> List[float]:
    """
    Converts all elements of a list to floats.
    
    Args:
        input_list (List[Any]): A list of elements to be converted.
    
    Returns:
        List[float]: A list containing the converted floats.
    """
    float_list: List[float] = []
    for element in input_list:
        try:
            float_list.append(float(element))
        except (ValueError, TypeError):
            continue
    return float_list

def map_usergroups_from_keycloak_to_usergroups_of_dasp_wikirag(values: List[str], mapping_file: str = "usergroups_mapping.yml") -> List[str]:
    """
    Maps an array of values to new values based on a YAML mapping file.
    If the mapping file is empty or does not exist, returns the original values
    with a standard mapping applied.
    
    Args:
        values (List[str]): List of input values.
        mapping_file (str): Path to the YAML file with mappings.
    
    Returns:
        List[str]: List of mapped values.
    """
    mappings = {}
    if not os.path.exists(mapping_file):
        print(f"Mapping file '{mapping_file}' does not exist. Returning original values.")
        return values

    try:
        with open(mapping_file, "r") as file:
            mappings = yaml.safe_load(file)
            if not mappings or not isinstance(mappings.get("mappings", {}), dict):
                print(f"Mapping file '{mapping_file}' is empty or invalid. Performing standard mapping.")
                return [perform_standard_mapping(v) for v in values]
            mappings = mappings.get("mappings", {})
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file: {e}. Returning original values.")
        return values
    
    return [mappings.get(value, perform_standard_mapping(value)) for value in values]

def perform_standard_mapping(item: str) -> str:
    """
    Transforms a given string from the format /ukp-tuda-researcher 
    to Main.ukp-tuda-researcher.
    
    Args:
        item (str): Input string.
    
    Returns:
        str: Transformed string.
    """
    if item.startswith("/"):
        return "Main." + item[1:]
    return item