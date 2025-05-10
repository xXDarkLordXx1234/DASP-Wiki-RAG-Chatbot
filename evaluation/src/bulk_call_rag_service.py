"""
bulk_call_rag_service_requests.py
---------------------------------
Example of calling a FastAPI SSE endpoint with multiple queries
sequentially using raw 'requests' streaming and manual SSE parsing.
"""
import requests
import json

# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------
BASE_URL = "http://localhost:8000/retrieve_chunks"

BASE_URL = "http://127.0.0.1:8000/retrieve_chunks"
JWT_TOKEN = "sdaffdafssadfasd"


import csv

# Path to your CSV file
file_path = "QA_Hiwi.csv"

# List to store extracted questions
questions = []

# Open and read the CSV file
with open(file_path, mode="r", encoding="utf-8") as file:
    reader = csv.reader(file)
    for row in reader:
        # Check if the row starts with "Q:" and append it to the list
        if row[0].startswith("Q:"):
            questions.append(row[0])

# Print the extracted questions
print(questions)


# Example queries you want to run in sequence
queries = [
    "What is the capital of France?",
    "Explain the benefits of Python over JavaScript for back-end development.",
    "What is quantum entanglement?"
]

queries = questions

# ------------------------------------------------------------------------------
# SSE Parsing Function
# ------------------------------------------------------------------------------
def get_sse_events_no_library(query: str, jwt_token: str):
    """
    Streams Server-Sent Events (SSE) manually using requests and yields the 'data:' lines.
    """
    params = {
        "query": query,
        "jwt_token": jwt_token
    }

    # Make a streaming GET request
    with requests.get(BASE_URL, params=params, stream=True) as resp:
        resp.raise_for_status()  # raise an error if status != 200

        # Read line by line
        for raw_line in resp.iter_lines(decode_unicode=True):
            if not raw_line:  # skip empty lines
                continue

            # SSE lines typically look like: "data: {...JSON...}"
            if raw_line.startswith("data:"):
                data_str = raw_line[len("data:"):].strip()
                yield data_str

# ------------------------------------------------------------------------------
# Main Execution
# ------------------------------------------------------------------------------
if __name__ == "__main__":
    for idx, query in enumerate(queries, start=1):
        print(f"===== Starting query #{idx}: {query} =====")

        # Stream SSE data for this query
        for raw_data in get_sse_events_no_library(query, JWT_TOKEN):
            try:
                payload = json.loads(raw_data)  # parse JSON
                print(f"SSE JSON payload: {payload}")

                # Check for a final status from the server
                status = payload.get("status")
                if status in ["success", "failed"]:
                    print(f"Final status for query '{query}': {status}")
                    break

            except json.JSONDecodeError:
                # If it's not valid JSON, just print the raw line
                print(f"SSE message: {raw_data}")

        print(f"===== Finished query #{idx}: {query} =====\n")
