import logging
import os
import re
import string
import unicodedata
from pathlib import Path
from typing import Any

import contractions  # type: ignore
import numpy as np
import tiktoken
from llama_index.embeddings.huggingface import HuggingFaceEmbedding  # type: ignore
from nltk.corpus import stopwords  # type: ignore
from nltk.stem import WordNetLemmatizer  # type: ignore
from nltk.tokenize import word_tokenize  # type: ignore
from numpy.typing import NDArray
from pydantic import BaseModel

from .chunk import Chunk

logger = logging.getLogger(__name__)


class EmbeddingFactory(BaseModel):
    """A factory class to create embeddings for a given text."""

    model: HuggingFaceEmbedding
    chunk_size: int
    chunk_overlap: int
    include_headers_in_chunks: bool
    include_headers_in_embedding: bool
    include_path_in_embedding: bool
    ignored_line_starts: list[str]
    remove_stopwords: bool
    lemmatize: bool
    remove_numbers: bool
    remove_accents: bool
    header_match: str
    hard_header_split: bool

    def __init__(
        self,
        model: str,
        **data: Any,
    ) -> None:
        """
        Initialize the EmbeddingFactory.

        Parameters
        ----------
        model : str
            The name of the HuggingFace model to use for embeddings.
        """
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")

        super().__init__(
            model=HuggingFaceEmbedding(model, device=device),
            **data,
        )
        # Download NLTK resources
        import nltk  # type: ignore

        nltk.download(  # type: ignore
            ["stopwords", "punkt", "wordnet", "omw-1.4", "punkt_tab"],
            quiet=True,
        )

    async def embed(self, chunks: list[Chunk]) -> NDArray[np.float32]:
        """
        Create embeddings for a list of text.

        Parameters
        ----------
        chunks : list[Chunks]
            A list of chunks to create embeddings for.

        Returns
        -------
        NDArray[np.float32]
            An array of embeddings for the input text.
        """
        return await self.model.aget_text_embedding_batch(
            [
                self.clean_text(
                    (chunk.path if self.include_path_in_embedding else "")
                    + (
                        " ".join(chunk.headers)
                        if self.include_headers_in_embedding
                        and not self.include_headers_in_chunks
                        else ""
                    )
                    + chunk.content
                )
                for chunk in chunks
            ]
        )

    def get_headers(self, line: str) -> tuple[int | None, str | None]:
        """
        Get the headers from a line of text.

        Parameters
        ----------
        line : str
            The line of text to extract headers from.

        Returns
        -------
        tuple[int | None, str | None]
            A tuple containing the level of the header and the header itself.
        """
        header_match = re.match(self.header_match, line)
        if header_match:
            return line.count("+") - 2, header_match.group(1).strip()
        return None, None

    def clean_text(
        self,
        text: str,
    ) -> str:
        """
        Cleans and preprocesses text for embedding generation.

        Parameters:
            text (str): Input text to clean

        Returns:
            str: Cleaned text
        """

        # Text normalization pipeline
        text = text.lower()
        text = re.sub(r"http\S+", "", text)  # Remove URLs
        text = re.sub(r"<[^>]+>", "", text)  # Remove HTML tags
        text = contractions.fix(text)  # Expand contractions # type: ignore
        text = re.sub(
            r"[-/]", " ", text
        )  # Replace hyphens/slashes with spaces
        text = text.translate(
            str.maketrans("", "", string.punctuation)
        )  # Remove punctuation

        if self.remove_numbers:
            text = re.sub(r"\d+", "", text)

        if self.remove_accents:
            text = (
                unicodedata.normalize("NFKD", text)
                .encode("ascii", "ignore")
                .decode("utf-8", "ignore")
            )

        text = re.sub(r"\s+", " ", text).strip()  # Remove extra whitespace

        # Tokenization and advanced processing
        tokens = word_tokenize(text)

        if self.remove_stopwords:
            stop_words = set(stopwords.words("english"))  # type: ignore
            tokens = [t for t in tokens if t not in stop_words]

        if self.lemmatize:
            lemmatizer = WordNetLemmatizer()
            tokens = [lemmatizer.lemmatize(t) for t in tokens]

        return " ".join(tokens)

    def is_ignored_line(self, line: str) -> bool:
        """
        Check if a line should be ignored.

        Parameters
        ----------
        line : str
            The line to check.

        Returns
        -------
        bool
            True if the line should be ignored, False otherwise
        """
        for ignored_line in self.ignored_line_starts:
            if line.startswith(ignored_line):
                return True
        return False

    def split_file(self, path: Path) -> list[tuple[list[str], str]]:
        """
        Split a file into sections based on headers.

        Parameters
        ----------
        path : Path
            The path to the file to split.

        Returns
        -------
        list[tuple[list[str], str]]
            A list of sections containing headers and content
        """
        sections: list[tuple[list[str], str]] = []
        current_headers: list[str] = []
        current_section: str = ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if self.is_ignored_line(line):
                        continue

                    level, header = self.get_headers(line)
                    if level is None:
                        current_section += line + "\n"
                    else:
                        assert header is not None
                        if current_section:
                            sections.append(
                                (list(current_headers), current_section)
                            )

                        current_headers = current_headers[:level]
                        current_headers.append(header)
                        current_section = " ".join(current_headers) + "\n"
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
        return sections

    def clean_content(self, base_dir: str, file_path: str) -> list[Chunk]:
        """
        Clean the content of a file and split it into chunks.

        Parameters
        ----------
        base_dir : str
            The base directory of the file.
        file_path : str
            The path to the file.

        Returns
        -------
        List[Chunk]
            A list of chunks containing the cleaned content.
        """
        enc = tiktoken.get_encoding("cl100k_base")
        sections = self.split_file(Path(os.path.join(base_dir, file_path)))
        chunks: list[Chunk] = []
        current_chunk: str = ""
        current_token_length: int = 0
        start_headers: list[str] = []
        index = 0
        for headers, content in sections:
            for line in content.split("\n"):
                line_token_length = len(enc.encode(self.clean_text(line)))
                if current_token_length + line_token_length > self.chunk_size:
                    chunks.append(
                        Chunk(
                            id=index,
                            path=file_path,
                            content=current_chunk,
                            headers=start_headers,
                        )
                    )
                    index += 1
                    start_headers = headers
                    current_chunk = enc.decode(
                        enc.encode(current_chunk)[-self.chunk_overlap :]
                    )
                    current_token_length = len(
                        enc.encode(self.clean_text(current_chunk))
                    )

                current_chunk += line + "\n"
                current_token_length += line_token_length
                if len(start_headers) == 0:
                    start_headers = headers
            if current_chunk and self.hard_header_split:
                chunks.append(
                    Chunk(
                        id=index,
                        path=file_path,
                        content=current_chunk,
                        headers=start_headers,
                    )
                )
                index += 1
                current_chunk = ""
                current_token_length = 0
                start_headers = []

        if current_chunk:
            chunks.append(
                Chunk(
                    id=index,
                    path=file_path,
                    content=current_chunk,
                    headers=start_headers,
                )
            )

        return chunks
