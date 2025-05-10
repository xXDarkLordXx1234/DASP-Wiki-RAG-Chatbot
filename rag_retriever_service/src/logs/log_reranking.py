import json
import os
from typing import Any

def save_in_json(json_file_name: str, chunks_before_reranking: Any, chunks_after_reranking: Any, query: str, sources: Any, filled_prompt: str, elapsed_time: float) -> None:
    """
    Save the re-ranking log in a JSON file.

    Args:
        json_file_name (str): The path to the JSON file.
        chunks_before_reranking (Any): The chunks before re-ranking.
        chunks_after_reranking (Any): The chunks after re-ranking.
        query (str): The query string.
        sources (Any): The source information.
        filled_prompt (str): The final prompt.
        elapsed_time (float): The time taken for re-ranking.
    """
    data = {
        "chunks_before_reranking": chunks_before_reranking,
        "chunks_after_reranking": chunks_after_reranking,
        "query": query,
        "sources": sources,
        "filled_prompt": filled_prompt,
        "elapsed_time": elapsed_time
    }

    if os.path.exists(json_file_name):
        with open(json_file_name, 'r') as file:
            try:
                existing_data = json.load(file)
                if not isinstance(existing_data, list):
                    existing_data = []
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    existing_data.append(data)
    with open(json_file_name, 'w') as file:
        json.dump(existing_data, file, indent=4)