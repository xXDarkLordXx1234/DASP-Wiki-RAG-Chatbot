from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from typing import Any

import chromadb
import polars as pl
from chromadb.api import AsyncClientAPI
from chromadb.api.models.AsyncCollection import AsyncCollection  # type: ignore
from chromadb.config import Settings

from .change_types import ChangeType
from .chunk import Chunk
from .config import Config
from .embedding_factory import EmbeddingFactory
from .index_factory import IndexFactory

logger = logging.getLogger(__name__)


async def load_chroma_config(client: AsyncClientAPI, config: Config) -> None:
    """
    Load the system configuration into ChromaDB.

    Parameters
    ----------
    client : AsyncClientAPI
        The ChromaDB client to use.
    config : Config
        The configuration to use.
    """
    system_config: dict[str, str | int] = config.embedding.model_dump()
    system_config["ignored_line_starts"] = "|".join(
        sorted(config.embedding.ignored_line_starts)
    )
    system_config["collection_name"] = config.chromadb.collection_name

    collection = await client.get_or_create_collection(
        config.system_config_collection_name
    )

    docs = await collection.get()
    assert docs["metadatas"] is not None
    if len(docs["metadatas"]) == 0:
        logger.info("Adding system config to ChromaDB")
        await collection.add(
            ids="system_config", embeddings=[[1]], metadatas=system_config
        )
    elif (
        hashlib.sha256(
            json.dumps(docs["metadatas"][0], sort_keys=True).encode("utf-8")
        ).hexdigest()
        != hashlib.sha256(
            json.dumps(system_config, sort_keys=True).encode("utf-8")
        ).hexdigest()
    ):
        logger.info("Updating system config in ChromaDB")
        await collection.update(
            ids="system_config", embeddings=[[1]], metadatas=system_config
        )
    else:
        return

    # Clear all collections except the system config collection
    collections = await client.list_collections()
    for c in collections:
        if c.name != config.system_config_collection_name:
            all_items = await c.get(include=[])
            if all_items["ids"]:
                logger.info(
                    f"Deleting all {len(all_items['ids'])} docs "
                    f"in collection {c.name}"
                )
                await c.delete(ids=all_items["ids"])
    # Clear the index
    if config.index.index_path.exists():
        logger.info("Clearing index")
        config.index.index_path.unlink()


class ClientHandler:
    """
    A class to handle the client connection to ChromaDB.
    """

    collection: AsyncCollection
    """The collection in ChromaDB."""

    def __init__(
        self,
        index_factory: IndexFactory,
        chroma_client: AsyncClientAPI,
        embedding_factory: EmbeddingFactory,
        collection_name: str,
    ) -> None:
        """
        Initialize the ClientHandler.

        Parameters
        ----------
        index_factory : IndexFactory
            The index factory to use.
        chroma_client : AsyncClientAPI
            The ChromaDB client to use.
        collection_name : str
            The name of the collection to use.
        embedding_model_name : str
            The name of the embedding model to use.
        """
        self.index_factory = index_factory
        self.client = chroma_client
        self.embedding_factory = embedding_factory
        self.collection_name = collection_name
        self.collection = None  # type: ignore

    def remove_prefix(self, path: str) -> str:
        """
        Remove the base dir from the path.

        Parameters
        ----------
        path : str
            The path to remove the base dir from.

        Returns
        -------
        str
            The path without the base dir.
        """
        return path.removeprefix(str(self.index_factory.source_dir)).lstrip(
            os.sep
        )

    def get_file(self, row: dict[str, Any]) -> list[Chunk]:
        """
        Get the file from the row.

        Parameters
        ----------
        row : dict[str, Any]
            The row to get the file from.

        Returns
        -------
        list[Chunk]
            The list of chunks in the file.
        """

        chunks = self.embedding_factory.clean_content(
            self.index_factory.source_dir,
            self.remove_prefix(row["path"]),
        )

        if not chunks:
            return []

        metadata: dict[str, Any] = row

        for chunk in chunks:
            chunk.copy_metadata(metadata)

        return chunks

    async def get_collection(self) -> None:
        """
        Get the collection from ChromaDB. If it does not exist, reset the
        index and create a new collection.
        """
        collections = await self.client.list_collections()
        if self.collection_name not in [c.name for c in collections]:
            self.collection = await self.client.create_collection(
                name=self.collection_name
            )
            self.index_factory.reset()
        else:
            self.collection = await self.client.get_collection(
                name=self.collection_name
            )

    async def delete_changes(self, df: pl.DataFrame) -> None:
        """
        Delete the changes from the collection.

        Parameters
        ----------
        df : pl.DataFrame
            The changes to delete.
        """
        if df.is_empty():
            return

        await self.collection.delete(
            where={
                "path": {
                    "$in": df.select(pl.col("path"))
                    .to_series()
                    .map_elements(self.remove_prefix, return_dtype=pl.String)
                    .to_list()
                }
            }
        )

    async def add_changes(
        self, df: pl.DataFrame, page_size: int = 100
    ) -> None:
        """
        Add the changes to the collection.

        Parameters
        ----------
        df : pl.DataFrame
            The changes to add.
        page_size : int, optional
            The size of the page to add, by default 100
        """
        if df.is_empty():
            return

        df = df.drop("change_type")
        start = time.time()
        # Add the changes in batches to avoid memory issues

        for page_start in range(0, len(df), page_size):
            page = df[page_start : page_start + page_size]

            chunks = [
                chunk
                for row in page.iter_rows(named=True)
                for chunk in self.get_file(row)
            ]

            if chunks:
                embeddings = await self.embedding_factory.embed(chunks)
                await self.collection.add(
                    ids=[chunk.get_id() for chunk in chunks],
                    documents=[chunk.content for chunk in chunks],
                    embeddings=embeddings,
                    metadatas=[chunk.metadata for chunk in chunks],
                )
        logger.info(f"Added {len(df)} changes in {time.time() - start:.2f}s")

    async def update(self) -> None:
        """
        Update the collection with the changes in the index.
        """
        if self.collection is None:
            await self.get_collection()

        changes = await self.index_factory.get_changes()

        if changes is None or changes.is_empty():
            return

        counts: dict[str, int] = {
            row[0]: row[1]
            for row in changes["change_type"].value_counts().rows()
        }
        logger.info(
            f"Changes: {counts.get(ChangeType.ADDED, 0)} additions, "
            f"{counts.get(ChangeType.MODIFIED, 0)} modifications, "
            f"{counts.get(ChangeType.DELETED, 0)} deletions"
        )

        await self.delete_changes(
            changes.filter(
                pl.col("change_type").is_in(
                    [ChangeType.DELETED, ChangeType.MODIFIED]
                )
            )
        )

        await self.add_changes(
            changes.filter(
                pl.col("change_type").is_in(
                    [ChangeType.ADDED, ChangeType.MODIFIED]
                )
            )
        )

    @classmethod
    async def build(cls, config: Config) -> ClientHandler:
        """
        Build the ClientHandler.

        Parameters
        ----------
        source_dir : Path
            The base directory to use.
        collection_name : str, optional
            The name of the collection to use, by default "WikiData"
        host : str, optional
            The host to connect to, by default "localhost"
        port : int, optional
            The port to connect to, by default 8000
        index_path : Path, optional
            The path to the index, by default "index.parquet"
        embedding_model_name : str, optional
            The name of the embedding model to use, by default
            "paraphrase-MiniLM-L6-v2"
        ignored_files : Tuple[str], optional
            The files to ignore, by default None
        min_file_size : int, optional
            The minimum file size to index, by default 0

        Returns
        -------
        ClientHandler
            The built ClientHandler.
        """
        try:
            chroma_client = await chromadb.AsyncHttpClient(
                host=config.chromadb.host,
                port=config.chromadb.port,
                settings=Settings(anonymized_telemetry=False),
            )
            await chroma_client.heartbeat()
        except Exception as e:
            logger.error("Failed to connect to ChromaDB")
            raise e

        await load_chroma_config(chroma_client, config)
        index_factory = IndexFactory(**config.index.model_dump())

        embedding_factory = EmbeddingFactory(**config.embedding.model_dump())

        return cls(
            index_factory=index_factory,
            chroma_client=chroma_client,
            embedding_factory=embedding_factory,
            collection_name=config.chromadb.collection_name,
        )
