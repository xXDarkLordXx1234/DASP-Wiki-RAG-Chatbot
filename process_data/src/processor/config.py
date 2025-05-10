from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List

from pydantic import BaseModel, ConfigDict, field_validator


class IndexConfig(BaseModel):
    """A class to hold the configuration for the index."""

    source_dir: Path
    """The source directory to index."""

    index_path: Path
    """The path to the index file."""

    ignored_files: List[str] | None
    """A list of files to ignore."""

    min_file_size: int
    """The minimum file size to index."""

    reload_seconds: int
    """The number of seconds to wait between index reloads."""

    @field_validator("index_path")
    def validate_index_path(cls, value: Path) -> Path:
        """
        Validate the index path.

        Parameters
        ----------
        value : Path
            The path to the index file

        Returns
        -------
        Path
            The path to the index file

        Raises
        ------
        ValueError
            If the index path is not a .parquet file
        """
        if not value.suffix == ".parquet":
            raise ValueError("Index path must be a .parquet file.")
        return value

    @field_validator("source_dir")
    def validate_source_dir(cls, value: Path) -> Path:
        """
        Validate the source directory.

        Parameters
        ----------
        value : Path
            The source directory to index

        Returns
        -------
        Path
            The source directory to index

        Raises
        ------
        ValueError
            If the directory does not exist or is not accessible
        """
        if not value.is_dir():
            raise ValueError(
                f"Directory '{value}' does not exist or is not accessible."
            )
        return value


class ChromaDBConfig(BaseModel):
    """A class to hold the configuration for the ChromaDB."""

    host: str
    """The host to connect to."""

    port: int
    """The port to connect to."""

    collection_name: str
    """The name of the collection to use."""


class EmbeddingConfig(BaseModel):
    """A class to hold the configuration for the embeddings."""

    model: str
    """The name of the embedding model to use."""

    chunk_size: int
    """The size of the chunks to use."""

    chunk_overlap: int
    """The overlap of the chunks to use."""

    include_headers_in_chunks: bool
    """Whether to include headers in the chunks."""

    include_headers_in_embedding: bool
    """Whether to include headers in the embedding."""

    include_path_in_embedding: bool
    """Whether to include the path in the embedding."""

    ignored_line_starts: list[str]
    """The list of ignored line starts."""

    remove_stopwords: bool
    """Whether to remove stopwords."""

    lemmatize: bool
    """Whether to lemmatize."""

    remove_numbers: bool
    """Whether to remove numbers."""

    remove_accents: bool
    """Whether to remove accents."""

    header_match: str
    """The regular expression to match headers."""

    hard_header_split: bool
    """Whether to hard split chunks on headers or not."""


class Config(BaseModel):
    """A class to hold the configuration for the processor."""

    index: IndexConfig
    """The configuration for the index."""

    chromadb: ChromaDBConfig
    """The configuration for the ChromaDB."""

    embedding: EmbeddingConfig
    """The configuration for the embeddings."""

    logging_file_handler: logging.FileHandler | None = None
    """The file handler for the logger"""

    system_config_collection_name: str
    """The name of the collection to use for system configuration"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def load(cls, file_path: Path) -> Config:
        """
        Load the configuration from a YAML file.

        Parameters
        ----------
        file_path : Path
            The path to the YAML file

        Returns
        -------
        Config
            The configuration
        """
        import yaml  # type: ignore

        # Load YAML config
        with open(file_path, "r") as file:
            raw_config = yaml.safe_load(file)

        # Update with environment variables if they exist
        if external_path := os.getenv("EXTERNAL_PATH"):
            raw_config["index"]["source_dir"] = external_path

        if system_config_collection_name := os.getenv(
            "SYSTEM_CONFIG_COLLECTION_NAME"
        ):
            raw_config["system_config_collection_name"] = (
                system_config_collection_name
            )

        if index_path := os.getenv("INDEX_PATH"):
            raw_config["index"]["index_path"] = index_path

        if os.getenv("IS_PERSISTENT"):
            persistent_path = Path("/index/index")
            persistent_path.mkdir(parents=True, exist_ok=True)
            raw_config["index"]["index_path"] = (
                persistent_path / raw_config["index"]["index_path"]
            )

            # Add file handler to logger
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
            )
            file_handler = logging.FileHandler(
                str(persistent_path / "processor.log")
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            raw_config["logging_file_handler"] = file_handler

        if ignored_files := os.getenv("IGNORED_FILES"):
            raw_config["index"]["ignored_files"] = ignored_files.split(",")

        if min_file_size := os.getenv("MIN_FILE_SIZE"):
            raw_config["index"]["min_file_size"] = int(min_file_size)

        if chroma_db_host := os.getenv("CHROMA_DB_HOST"):
            raw_config["chromadb"]["host"] = chroma_db_host

        if chroma_db_port := os.getenv("CHROMA_DB_PORT"):
            raw_config["chromadb"]["port"] = int(chroma_db_port)

        if reload_seconds := os.getenv("RELOAD_SECONDS"):
            if reload_seconds.isdigit():
                raw_config["index"]["reload_seconds"] = int(reload_seconds)

        if collection_name := os.getenv("COLLECTION_NAME"):
            raw_config["chromadb"]["collection_name"] = collection_name

        if embedding_model_name := os.getenv("EMBEDDING_MODEL_NAME"):
            raw_config["embedding"]["model"] = embedding_model_name

        if chunk_size := os.getenv("CHUNK_SIZE"):
            raw_config["embedding"]["chunk_size"] = int(chunk_size)

        if chunk_overlap := os.getenv("CHUNK_OVERLAP"):
            raw_config["embedding"]["chunk_overlap"] = int(chunk_overlap)

        if include_headers_in_chunks := os.getenv("INCLUDE_HEADERS_IN_CHUNKS"):
            assert include_headers_in_chunks in [
                "0",
                "1",
            ], "INCLUDE_HEADERS_IN_CHUNKS must be 0 or 1"
            raw_config["embedding"]["include_headers_in_chunks"] = (
                int(include_headers_in_chunks) == 1
            )

        if include_headers_in_embedding := os.getenv(
            "INCLUDE_HEADERS_IN_EMBEDDING"
        ):
            assert include_headers_in_embedding in [
                "0",
                "1",
            ], "INCLUDE_HEADERS_IN_EMBEDDING must be 0 or 1"
            raw_config["embedding"]["include_headers_in_embedding"] = (
                int(include_headers_in_embedding) == 1
            )

        if include_path_in_embedding := os.getenv("INCLUDE_PATH_IN_EMBEDDING"):
            assert include_path_in_embedding in [
                "0",
                "1",
            ], "INCLUDE_PATH_IN_EMBEDDING must be 0 or 1"
            raw_config["embedding"]["include_path_in_embedding"] = (
                int(include_path_in_embedding) == 1
            )

        if ignored_line_starts := os.getenv("IGNORED_LINE_STARTS"):
            raw_config["embedding"]["ignored_line_starts"] = (
                ignored_line_starts.split(";")
            )

        if remove_stopwords := os.getenv("REMOVE_STOPWORDS"):
            assert remove_stopwords in [
                "0",
                "1",
            ], "REMOVE_STOPWORDS must be 0 or 1"
            raw_config["embedding"]["remove_stopwords"] = (
                int(remove_stopwords) == 1
            )

        if lemmatize := os.getenv("LEMMATIZE"):
            assert lemmatize in [
                "0",
                "1",
            ], "LEMMATIZE must be 0 or 1"
            raw_config["embedding"]["lemmatize"] = int(lemmatize) == 1

        if remove_numbers := os.getenv("REMOVE_NUMBERS"):
            assert remove_numbers in [
                "0",
                "1",
            ], "REMOVE_NUMBERS must be 0 or 1"
            raw_config["embedding"]["remove_numbers"] = (
                int(remove_numbers) == 1
            )

        if remove_accents := os.getenv("REMOVE_ACCENTS"):
            assert remove_accents in [
                "0",
                "1",
            ], "REMOVE_ACCENTS must be 0 or 1"
            raw_config["embedding"]["remove_accents"] = (
                int(remove_accents) == 1
            )

        if header_match := os.getenv("HEADER_MATCH"):
            raw_config["embedding"]["header_match"] = header_match

        if hard_header_split := os.getenv("HARD_HEADER_SPLIT"):
            assert hard_header_split in [
                "0",
                "1",
            ], "HARD_HEADER_SPLIT must be 0 or 1"
            raw_config["embedding"]["hard_header_split"] = (
                int(hard_header_split) == 1
            )

        return cls(**raw_config)
