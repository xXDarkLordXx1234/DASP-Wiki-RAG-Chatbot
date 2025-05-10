# DASP-WikiRAG

DASP-WikiRAG monitors a specified directory and automatically embeds file contents, making them available for natural language search via a vector database. This repository provides tools for indexing, retrieval, and demo interfaces to interact with your embedded data.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Getting Started](#getting-started)
  - [Docker Setup](#docker-setup)
  - [Optional Index Configuration](#optional-index-configuration)
- [Development](#development)
  - [Indexing Component](#indexing-component)
  - [RAG Retriever Service](#rag-retriever-service)
  - [Demo Frontend](#demo-frontend)
- [Connecting to ChromaDB](#connecting-to-chromadb)

---

## Overview

DASP-WikiRAG is designed to:

- **Monitor a Directory:** Watch a user-defined directory for new or updated files.
- **Automatic Embedding:** Process and embed file contents for natural language queries.
- **Flexible Configuration:** Adjust parameters for indexing and embedding via environment variables or configuration files.
- **Seamless Integration:** Easily connect to the underlying ChromaDB for retrieval tasks.

---

## Features

- **Directory Monitoring:** Automatic detection and processing of new files.
- **Customizable Embedding:** Use any HuggingFace embedding model (default: `sentence-transformers/paraphrase-MiniLM-L6-v2`).
- **Advanced Text Processing:** Options for stopword removal, lemmatization, number/accent removal, and header handling.
- **Modular Design:** Separate components for indexing, retrieval (RAG), and a demo frontend.
- **Dockerized Setup:** Quick and isolated deployment with Docker Compose.

---

## Getting Started

### Docker Setup

1. **Configure Directory Volume:**
   - Open the [`docker-compose.yml`](docker-compose.yml) file.
   - Adjust the volume mapping for your data:
     ```yaml
     volumes:
       - ./WikiData:/external/directory:ro
     ```
     Replace `./WikiData` with the actual path to the directory you wish to monitor.
   - Alternatively, set the `SOURCE_DATA_PATH` environment variable.

2. **Build and Run:**
   - Build the Docker image and run it in detached mode:
     ```bash
     docker-compose up --build -d
     ```

Alternatively you can also use our provided [deploy script](vm_autodeploy/README.md) to for an easier setup.

### Optional Index Configuration

You can fine-tune the indexing and embedding behavior via environment variables. Below are the available options with their default values:

- **RELOAD_SECONDS:** `60`  
  *Interval (in seconds) between checking for new files.*

- **MIN_FILE_SIZE:** `32`  
  *Minimum file size (in bytes) to be processed.*

- **EMBEDDING_MODEL_NAME:** `"sentence-transformers/paraphrase-MiniLM-L6-v2"`  
  *Name of the embedding model from HuggingFace.*

- **CHUNK_SIZE:** `256`  
  *Maximum chunk size (in tokens) for embeddings.*

- **CHUNK_OVERLAP:** `64`  
  *Overlap (in tokens) between consecutive chunks.*

- **INCLUDE_HEADERS_IN_CHUNKS:** `0`  
  *Include headers in text chunks (0: No, 1: Yes).*

- **INCLUDE_HEADERS_IN_EMBEDDING:** `1`  
  *Include headers when generating embeddings (0: No, 1: Yes).*

- **INCLUDE_PATH_IN_EMBEDDING:** `1`  
  *Include file path in the embedding context (0: No, 1: Yes).*

- **IGNORED_LINE_STARTS:** `"%META"`  
  *Lines starting with these strings are ignored. Separate multiple values with a semicolon.*

- **REMOVE_STOPWORDS:** `1`  
  *Remove stopwords (0: No, 1: Yes).*

- **LEMMATIZE:** `1`  
  *Apply lemmatization (0: No, 1: Yes).*

- **REMOVE_NUMBERS:** `1`  
  *Remove numbers from text (0: No, 1: Yes).*

- **REMOVE_ACCENTS:** `1`  
  *Remove accents (0: No, 1: Yes).*

- **HARD_HEADER_SPLIT:** `0`  
  *Split text strictly at headers (0: No, 1: Yes).*

- **HEADER_MATCH:** `"^---\\++\\s+\\*?(?:%[A-Z]+%)?(.*?)(?:%[A-Z]+%)?\\*?$"`  
  *Regex pattern to identify headers.*

These variables can be added to the `environment` section in the [`docker-compose.yml`](docker-compose.yml) file or directly modified in the [`config.yml`](process_data/src/config.yml) file.

---

## Development

If you prefer to develop outside of Docker, follow the instructions below for each component.

### Indexing Component

For more details, refer to the [Indexing Documentation](process_data/README.md).

### RAG Retriever Service

For more details, refer to the [RAG Service Retriever Documentation](rag_retriever_service/README.md).

### Demo Frontend

A demo frontend is provided for testing the RAG Retriever Service. For setup and usage instructions, see [Demo Frontend Documentation](demo_frontend/README.md).

---

## Connecting to ChromaDB

After starting the Docker container or running the indexing service, you can connect to ChromaDB for querying. An example usage is provided in the [example_query.ipynb](example_query.ipynb) notebook.