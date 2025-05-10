import os
import yaml
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)
load_dotenv()

def load_config(config_file: str = "config.yml") -> dict:
    """
    Load configuration from a YAML file.
    
    Args:
        config_file (str): Path to the YAML configuration file.
        
    Returns:
        dict: A dictionary containing the configuration.
    """
    try:
        with open(config_file, "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        logger.warning(f"Configuration file {config_file} not found. Continuing with environment variables only.")
        return {}

def get_config_value(key: str, default=None, config_file: str = "config.yml"):
    """
    Get a configuration value, prioritizing environment variables over the YAML file.
    
    Args:
        key (str): The key to look for.
        default: Default value to return if the key is not found.
        config_file (str): Path to the YAML configuration file.
        
    Returns:
        The value of the key if found, otherwise the default value.
    """
    env_value = os.getenv(key)
    if env_value is not None:
        return env_value

    config = load_config(config_file)
    return config.get(key, default)