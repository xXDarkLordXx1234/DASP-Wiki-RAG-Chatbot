import logging
from pathlib import Path
from typing import Any

import polars as pl
from pydantic import BaseModel

from .change_types import ChangeType
from .permission_handler import PermissionHandler
from .rust_module import RustModule

logger = logging.getLogger(__name__)

# Regular expression patterns to extract metadata from files
REGEX_PATTERNS = [
    r'author="([^"]+)"',
    r'comment="([^"]+)"',
    r'date="([^"]+)"',
    r'format="([^"]+)"',
    r'reprev="([^"]+)"',
    r'version="([^"]+)"',
    r'name="([^"]+)"',
]

# Schema for the index
SCHEMA = pl.Schema(
    {
        "path": pl.String,
        "hash": pl.String,
        "author": pl.String,
        "comment": pl.String,
        "date": pl.Int64,
        "format": pl.String,
        "reprev": pl.Int16,
        "version": pl.Int16,
        "topicparent": pl.String,
        "allow_view": pl.String,
        "deny_view": pl.String,
    }
)

# Enum for change types
CHANGE_TYPES = pl.Enum(
    [ChangeType.ADDED, ChangeType.DELETED, ChangeType.MODIFIED]
)


class IndexFactory(BaseModel):
    """A class to create and manage an index of files in a directory."""

    source_dir: str
    """The source directory to search."""

    index_path: Path
    """The path to the index file."""

    permission_handler: PermissionHandler
    """The permission handler to use."""

    ignored_files: list[str] | None
    """The list of files to ignore."""

    min_file_size: int
    """A minimum file size to search for."""

    def __init__(
        self,
        *,
        source_dir: Path,
        index_path: Path,
        ignored_files: list[str] | None = None,
        min_file_size: int = 0,
        **kwargs: Any,
    ) -> None:
        """
        Create a new IndexFactory instance.

        Parameters
        ----------
        source_dir : Path
            The source directory to search.
        index_path : Path
            The path to the index file.
        ignored_files : list[str] | None, optional
            The list of files to ignore, by default None
        min_file_size : int, optional
            A minimum file size to search for, by default 0
        """
        source_dir = source_dir.resolve()
        super().__init__(
            source_dir=str(source_dir),
            permission_handler=PermissionHandler(source_dir=source_dir),
            index_path=index_path,
            ignored_files=ignored_files,
            min_file_size=min_file_size,
        )

    def reset(self) -> None:
        """Reset the index and permission handler."""
        self.index_path.unlink(missing_ok=True)
        self.permission_handler.reset()

    @staticmethod
    def map_authors(paths: pl.Series) -> pl.Series:
        """
        Map the authors in the given paths.

        Parameters
        ----------
        paths : pl.Series
            The paths to map.

        Returns
        -------
        pl.Series
            The mapped authors.
        """
        return pl.Series(
            RustModule.map_authors(
                paths.to_list(), r'author="([^"]+)"', "BaseUserMapping_999"
            )
        )

    def get_index(self) -> pl.LazyFrame:
        """
        Get the index of files in the source directory.

        Returns
        -------
        pl.LazyFrame
            The index of files.
        """
        self.permission_handler.load()
        results = RustModule.search_directory(
            self.source_dir,
            REGEX_PATTERNS,
            self.ignored_files,
            self.min_file_size,
        )

        permissions = [
            self.permission_handler.find(Path(result[0]).resolve())
            for result in results
        ]

        # Create a LazyFrame from the results and permissions
        df = pl.LazyFrame(
            {
                "path": (x[0] for x in results),
                "hash": (x[1] for x in results),
                "author": (x[2][0] if x[2][0] else None for x in results),
                "comment": (x[2][1] if x[2][1] else None for x in results),
                "date": (int(x[2][2]) if x[2][2] else None for x in results),
                "format": (x[2][3] if x[2][3] else None for x in results),
                "reprev": (int(x[2][4]) if x[2][4] else None for x in results),
                "version": (
                    int(x[2][5]) if x[2][5] else None for x in results
                ),
                "topicparent": (x[2][6] if x[2][6] else None for x in results),
                "allow_view": (x[0] for x in permissions),
                "deny_view": (x[1] for x in permissions),
            },
            schema=SCHEMA,
        ).with_columns(
            # If the author is "BaseUserMapping_999", map it to the actual author
            pl.when(
                pl.col("author") == "BaseUserMapping_999",
            )
            .then(pl.col("path").map_batches(self.map_authors))
            .otherwise(pl.col("author"))
            .alias("author")
        )

        return df

    def filter(
        self, old: pl.LazyFrame | None, new: pl.LazyFrame
    ) -> pl.LazyFrame:
        """
        Filter the changes between the old and new indexes.

        Parameters
        ----------
        old : pl.LazyFrame | None
            The old index.
        new : pl.LazyFrame
            The new index.

        Returns
        -------
        pl.LazyFrame
            The filtered changes.
        """
        if old is None:
            changes = new.with_columns(
                pl.lit(ChangeType.ADDED).alias("change_type")
            ).with_columns(pl.col("change_type").cast(CHANGE_TYPES))
            return changes

        changes = (
            old.join(new, on="path", how="full")
            # Filter the changes based on the changes of hash and permissions
            .with_columns(
                pl.when(
                    pl.col("hash").is_null()
                    & pl.col("hash_right").is_not_null()
                )
                .then(
                    pl.lit(ChangeType.ADDED)
                )  # Files present only in `changes` (newly added)
                .when(
                    pl.col("hash").is_not_null()
                    & pl.col("hash_right").is_null()
                )
                .then(
                    pl.lit(ChangeType.DELETED)
                )  # Files present only in `index` (removed)
                .when(
                    (pl.col("hash") != pl.col("hash_right"))
                    | (pl.col("allow_view") != pl.col("allow_view_right"))
                    | (pl.col("deny_view") != pl.col("deny_view_right"))
                )
                .then(
                    pl.lit(ChangeType.MODIFIED)
                )  # Files with mismatched "created" values
                .otherwise(pl.lit("U"))  # Files that remain unchanged
                .alias("change_type")
            )
            # Filter out unchanged files
            .filter(pl.col("change_type") != "U")
            .with_columns(pl.col("change_type").cast(CHANGE_TYPES))
            # Select the columns to keep
            .with_columns(
                [
                    pl.when(pl.col("change_type") == ChangeType.DELETED)
                    .then(
                        pl.col(col)
                    )  # Drop `_right` columns by setting them to None
                    .otherwise(pl.col(col + "_right"))
                    .alias(col)
                    for col in new.collect_schema().names()
                ]
            )
            .select(
                [
                    *new.collect_schema().names(),
                    "change_type",
                ]
            )
        )

        return changes

    async def get_changes(self) -> pl.DataFrame | None:
        """
        Get the current index and compare it with the previous index.

        Returns
        -------
        pl.DataFrame | None
            The changes between the indexes.
        """
        new = await self.get_index().collect_async()

        if not self.index_path.exists():
            changes = await self.filter(None, new.lazy()).collect_async()
            new.write_parquet(self.index_path)
            return changes

        old = pl.scan_parquet(self.index_path)
        changes = await self.filter(old, new.lazy()).collect_async()

        if changes.is_empty():
            return None

        new.write_parquet(self.index_path)

        return changes
