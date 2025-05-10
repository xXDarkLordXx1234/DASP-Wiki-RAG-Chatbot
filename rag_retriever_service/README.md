# RAG-Retriever Service

The **RAG-Retriever Service** is a FastAPI-based microservice that retrieves relevant document chunks from a vector store index based on a user query. It supports:

- **User group filtering** via Keycloak JWT authentication (when enabled)
- **Re-ranking** of retrieved chunks using a cross-encoder model
- Streaming progress and final results via **Server-Sent Events (SSE)**
- Construction of a prompt using a Jinja2 template for use in retrieval-augmented generation (RAG) systems

---

## Installation & Setup

### Prerequisites

Ensure you have **Python 3.7** (or higher) installed. The service relies on the following libraries:

- **FastAPI** (for the web service)
- **Uvicorn** (to run the FastAPI application)
- **python-dotenv** (to load environment variables from a `.env` file)
- **chromadb** (for connecting to a ChromaDB instance)
- **llama_index** (providing `VectorStoreIndex`, `ChromaVectorStore`, and `StorageContext`)
- **sentence-transformers** (for the cross-encoder model)
- **Jinja2** (for prompt templating)
- **requests** (for HTTP requests when fetching JWKS)
- **PyJWT** (for JWT token decoding and verification)
- **PyYAML** (for parsing YAML configuration)
- **pytest** (for running the tests)

### Running with Docker

By default, this service starts automatically as a separate Docker container when using `docker-compose`, so no manual action is required. 

However, if you need to run it locally, follow the steps outlined below:

### Installation Steps for local testing

1. **Clone the repository:**

   git clone <repository_url>
   cd <repository_directory>

2. **Create and activate a virtual environment:**

   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate

3. **Install required packages:**

   pip install -r <repository_directory>/requirements.txt

4. **Start the Indexing-Service:**

   Make sure the indexing service is running, as this service depends on it. For more 
   details on starting it, refer to the  README of the indexing service.

5. **Running FastAPI with Hypercorn**

   hypercorn <repository_directory>.core.src.app:app

## Configuration & Environment Variables

The service uses a combination of a YAML configuration file (`src/config.yml`) and environment variables. Environment variables take precedence over the YAML settings. You can set these in a `.env` file or directly in your deployment environment.

### Key Environment Variables

| Variable Name                   | Description                                             | Example / Default Value |
|----------------------------------|---------------------------------------------------------|-------------------------|
| **CHROMA_DB_HOST**               | Hostname for the ChromaDB server.                      | As set in `config.yml` (e.g., `chroma-db`) |
| **CHROMA_DB_PORT**               | Port for the ChromaDB server.                          | `8000` |
| **SIMILARITY_TOP_K**             | Number of top chunks to retrieve.                      | `15` (as defined in `config.yml`) |
| **CROSS_ENCODER_MODEL**          | Name of the cross-encoder model used for re-ranking.   | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| **USE_KEYCLOAK_AUTH**            | Enable Keycloak-based JWT authentication.              | `true` / `false` |
| **JWKS_URL**                     | URL to fetch JWKS for verifying JWT tokens.           | `https://auth.ukp.informatik.tu-darmstadt.de/realms/UKP/protocol/openid-connect/certs` |
| **METADATA_ALLOW_FILTER_KEY**    | Metadata key for allowed groups filtering.             | `allow_view` |
| **METADATA_DENY_FILTER_KEY**     | Metadata key for denied groups filtering.              | `deny_view` |
| **LOG_RERANKING**                | Enable saving logs of the re-ranking process.         | `true` / `false` |
| **LOG_RERANKING_OUTPUT_FILE**    | Path for re-ranking logs.                             | `reranking_log.json` |


### YAML Configuration File

The (`src/config.yml`) file contains default values for several configuration keys. For example:

#### Chroma DB
- **CHROMA_DB_HOST**: `chroma-db`
- **CHROMA_DB_PORT**: `8000`

#### Similarity Search
- **SIMILARITY_TOP_K**: `15`

#### Cross Encoder Model
- **CROSS_ENCODER_MODEL**: `"cross-encoder/ms-marco-MiniLM-L-6-v2"`
- **LOG_RERANKING**: `false`
- **LOG_RERANKING_OUTPUT_FILE**: `"reranking_log.json"`

#### Authentication
- **USE_KEYCLOAK_AUTH**: `false`
- **JWKS_URL**: `"https://auth.ukp.informatik.tu-darmstadt.de/realms/UKP/protocol/openid-connect/certs"`

#### Metadata Filters
- **METADATA_DENY_FILTER_KEY**: `"deny_view"`
- **METADATA_ALLOW_FILTER_KEY**: `"allow_view"`

### Loading Variables from the index-service

The following variables are automatically loaded from the index service, so you don’t need to manage them manually.

| Variable Name                    | Description                                          |
|----------------------------------|------------------------------------------------------|
| **CHROMA_DB_COLLECTION_NAME**    | Name of the ChromaDB collection used by the service. |
| **HUGGING_FACE_EMBEDDING_MODEL** | Name of the Hugging Face embedding model.            |

## API Documentation

### GET /retrieve_chunks

#### Description
Retrieves relevant chunks from the vector store based on the supplied query, optionally filtering based on the user’s allowed groups (if JWT authentication is enabled) and re-ranking the results.

#### Query Parameters

- **query** (`string`, required): The search query.
- **jwt_token** (`string`, required): JWT token for user authentication.
- **similarity_top_k** (`integer`, optional): Number of top chunks to retrieve. Defaults to the configured value if not provided.

#### Response
The endpoint returns a streaming response (SSE) with status updates. The final event yields a JSON object with the following keys:

- **rag_prompt** (`string`): The prompt generated by rendering the Jinja2 template with the retrieved and re-ranked chunks.
- **sources** (`array` of objects): A list of retrieved chunks. Each object contains:
  - **context** (`string`): The content of the retrieved chunk.
  - **path** (`string`): The path (or identifier) of the chunk.
  - **chunk_header** (`string`): The chunk header of the retrieved chunk.

- **status** (`string`): Indicates the overall status (e.g., `"success"` or `"failed"`).

If no relevant chunks are found, the service returns a message indicating that no results were available.

## Testing

The project includes tests located in the `tests` directory. The tests cover:

- **FastAPI endpoint behavior**: [`tests/test_app.py`](tests/test_app.py)
- **Metadata filtering logic**: [`tests/test_handle_metadata_filtering.py`](tests/test_handle_metadata_filtering.py)
- **Utility functions for data conversion and user group mapping**: [`tests/test_utils.py`](tests/test_utils.py)

### Running Tests

From the project root, run:

pytest

## Common Issues & Troubleshooting

### JWT Verification & User Filtering

- If `USE_KEYCLOAK_AUTH` is set to `"true"` but the token is invalid or does not contain a `groups` field, the service will yield an `"Invalid User"` message.
- Verify that the `JWKS_URL` and related Keycloak settings are correct in your environment variables or `config.yml`.

### No Chunks Retrieved

- If the retrieval step returns no chunks, ensure that the underlying vector store (ChromaDB) is populated with documents and that your query matches the available content.

### Re-ranking Logging

- If `LOG_RERANKING` is enabled, confirm that the file specified by `LOG_RERANKING_OUTPUT_FILE` is writable by the service.

### Template Issues

- The prompt template used for generating the final RAG prompt is loaded from `rag_prompt_template.txt`. Make sure this file is present and correctly formatted.