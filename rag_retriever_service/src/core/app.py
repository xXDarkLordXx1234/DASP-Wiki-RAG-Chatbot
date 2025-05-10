"""
Module: RAG-Retriever Service
Description:
    This module provides a FastAPI endpoint for retrieving relevant chunks 
    (documents) from a vector store index using a query. It supports filtering 
    via user group restrictions (Keycloak JWT), re-ranking the retrieved chunks 
    using a cross-encoder model, and returning the results via Server-Sent 
    Events (SSE).

Usage:
    1. Place your environment variables in a .env file or set them in your environment.
    2. Run this FastAPI application.
    3. Access the endpoint as a GET request:
       /retrieve_chunks?query=<query>&jwt_token=<JWT_TOKEN>
"""

import os
import json
import time
from typing import AsyncGenerator, List, Tuple, Optional

from fastapi import FastAPI, Query
from starlette.responses import StreamingResponse
from dotenv import load_dotenv

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core import StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from sentence_transformers import CrossEncoder
from jinja2 import Template

from rag_retriever_service.src.logs import log_reranking as log
from rag_retriever_service.src.utils import verify_data
from rag_retriever_service.src.utils import utils
from rag_retriever_service.src.config.load_config import get_config_value
from chromadb.config import Settings
import logging
from rag_retriever_service.src.filters import metadata_filter

# ------------------------------------------------------------------------------
# Load environment variables
# ------------------------------------------------------------------------------
os.environ["TOKENIZERS_PARALLELISM"] = "false"
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Rag-Service")

# ------------------------------------------------------------------------------
# Initialize ChromaDB
# ------------------------------------------------------------------------------
db_host = get_config_value("CHROMA_DB_HOST", "chromadb")
db_port = get_config_value("CHROMA_DB_PORT", "8000")

chromadb_client = chromadb.HttpClient(
    host=db_host,
    port=int(db_port),
    settings=Settings(anonymized_telemetry=False)
)

config = chromadb_client.get_collection("system_config").get()["metadatas"][0]
chroma_collection = chromadb_client.get_or_create_collection(
    config["collection_name"]
)

vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
storage_context = StorageContext.from_defaults(vector_store=vector_store)

logger.info(f"The index contains {chroma_collection.count()} chunks.")
logger.info("Index setup complete. RAG-Retriever-Service-API is ready!")

# ------------------------------------------------------------------------------
# Initialize embedding model from Hugging Face
# ------------------------------------------------------------------------------
embed_model = HuggingFaceEmbedding(config["model"])

# ------------------------------------------------------------------------------
# Create the VectorStoreIndex
# ------------------------------------------------------------------------------
index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store,
    storage_context=storage_context,
    embed_model=embed_model
)

# ------------------------------------------------------------------------------
# Cross-encoder for re-ranking
# ------------------------------------------------------------------------------
cross_encoder_model_name = get_config_value("CROSS_ENCODER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
cross_encoder = CrossEncoder(cross_encoder_model_name)

# ------------------------------------------------------------------------------
# Load Prompt Template (Jinja2)
# ------------------------------------------------------------------------------

# Compute the directory where app.py resides.
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# Build the absolute path to the template.
template_path = os.path.join(THIS_DIR, "..", "prompts", "rag_prompt_template.txt")

with open(template_path, "r", encoding="utf-8") as file:
    template_content = file.read()
    
template = Template(template_content)

# ------------------------------------------------------------------------------
# Create FastAPI app
# ------------------------------------------------------------------------------
app = FastAPI()

def sse_message(message: str) -> str:
    """Helper function to format SSE messages."""
    return f"data:{message}\n\n"

@app.get("/retrieve_chunks")
async def retrieve_chunks(
    query: str = Query(..., description="User's query for retrieving documents."),
    jwt_token: str = Query(..., description="JWT Token for user authentication."),
    similarity_top_k: Optional[int] = Query(
        None,
        description=(
            "Number of top chunks to retrieve (optional). If not provided, "
            "the service uses the value from SIMILARITY_TOP_K in your configuration."
        )
    )
) -> StreamingResponse:
    """
    Endpoint: /retrieve_chunks

    Retrieve relevant chunks from the index based on the user's query.
    If Keycloak authentication is enabled, filter by the user's allowed groups.
    Return updates (in SSE format) for the retrieval and re-ranking steps,
    and finally return the prepared RAG prompt and sources.
    """
    async def event_stream() -> AsyncGenerator[str, None]:
        start_time = time.time()

        # Step 1: Verify user groups (if Keycloak auth is enabled)
        chroma_db_meta_data_filters = None
        if get_config_value("USE_KEYCLOAK_AUTH", 'false').lower() == 'true':
            user_groups = verify_data.verify_and_decode_token(jwt_token)
            if not user_groups:
                yield sse_message("Invalid User.")
                final_payload = {
                    'rag_prompt': None,
                    'sources': None,
                    'status': "failed"
                }
                yield sse_message(json.dumps(final_payload))
                return

            allow_filter_key = get_config_value("METADATA_ALLOW_FILTER_KEY", 'allow_view')
            deny_filter_key = get_config_value("METADATA_DENY_FILTER_KEY", 'deny_view')
            chroma_db_meta_data_filters = metadata_filter.create_filter_for_user_group(
                user_groups, allow_filter_key=allow_filter_key, deny_filter_key=deny_filter_key
            )

        # Step 2: Retrieval
        yield sse_message(json.dumps({'message': 'Retrieval in progress...', 'status': 'pending'}))
        top_k = similarity_top_k if similarity_top_k is not None else int(
            get_config_value("SIMILARITY_TOP_K", "5")
        )
        
        retriever = index.as_retriever(
            similarity_top_k=top_k,
            filters=chroma_db_meta_data_filters
        )
        retrieved_nodes = retriever.retrieve(query)
        yield sse_message("Retrieval done.")

        chunks: List[Tuple[str, str, str]] = [
            (node.get_content(), node.metadata["path"], node.metadata["chunk_header"]) for node in retrieved_nodes
        ]

        if not chunks:
            yield sse_message("No relevant chunks found.")
            final_payload = {
                'rag_prompt': "No relevant chunks found for your query.",
                'sources': [],
                'status': 'success'
            }
            yield sse_message(json.dumps(final_payload))
            return

        # Step 3: Re-ranking
        yield sse_message("Reranking in progress...")
        query_chunk_pairs = [(query, content) for (content, _, _) in chunks]
        scores = cross_encoder.predict(query_chunk_pairs)
        reranked_chunks = [
            chunk for _, chunk in 
            sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        ]
        yield sse_message("Reranking done.")

        # Step 4: Construct final RAG prompt & sources
        reranked_chunks_with_numbers = [
            f"chunk {idx+1}: ### Content: {chunk[0]} | Path: {chunk[1]} | Header: {chunk[2]} ###"
            for idx, chunk in enumerate(reranked_chunks)
        ]
        filled_prompt = template.render(context=reranked_chunks_with_numbers, query=query)
        sources = [
            {"context": chunk[0], "path": chunk[1], "header": chunk[2]} 
            for chunk in reranked_chunks
        ]
        final_payload = {
            'rag_prompt': filled_prompt,
            'sources': sources,
            'status': 'success'
        }

        # Step 5: Optional logging
        if get_config_value('LOG_RERANKING', 'false').lower() == 'true':
            elapsed_time = time.time() - start_time
            float_scores = utils.convert_list_to_float(scores)
            sorted_scored_chunks = sorted(
                zip(float_scores, chunks),
                key=lambda x: x[0],
                reverse=True
            )
            log.save_in_json(
                get_config_value('LOG_RERANKING_OUTPUT_FILE', "reranking_log.json"),
                chunks,
                sorted_scored_chunks,
                query,
                sources,
                filled_prompt,
                elapsed_time
            )

        yield sse_message(json.dumps(final_payload))

    return StreamingResponse(event_stream(), media_type="text/event-stream")