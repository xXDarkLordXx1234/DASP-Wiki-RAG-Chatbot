from typing import Any

from pydantic import BaseModel


class Chunk(BaseModel):
    """A chunk of text with metadata."""

    id: int
    path: str
    content: str
    headers: list[str] = []
    metadata: dict[str, str | int | bool | float]

    def __init__(
        self,
        path: str,
        id: int,
        content: str,
        headers: list[str] | None = None,
    ):
        """Create a new Chunk object.

        Parameters
        ----------
        path : str
            The path to the file the chunk was extracted from.
        id : int
            The unique identifier of the chunk.
        content : str
            The text content of the chunk.
        headers : List[str], optional
            The headers of the chunk, by default None.
        """
        super().__init__(
            path=path,
            id=id,
            content=content,
            headers=headers if headers is not None else [],
            metadata={},
        )

    def copy_metadata(self, metadata: dict[str, Any]) -> None:
        """Copy metadata to the chunk.

        Parameters
        ----------
        metadata : dict[str, Any]
            The metadata to copy.
        """
        self.metadata = {
            key: value for key, value in metadata.items() if value is not None
        }
        self.metadata["path"] = self.path
        self.metadata["chunk_id"] = self.id
        self.metadata["chunk_header"] = ";".join(self.headers)
        self.id = self.id

    def get_id(self) -> str:
        """Get the unique identifier of the chunk.

        Returns
        -------
        str
            The unique identifier of the chunk.
        """
        return f"{self.path}-{self.id}"
