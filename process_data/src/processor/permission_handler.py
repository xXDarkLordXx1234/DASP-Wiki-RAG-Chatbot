import logging
import os
import re
from pathlib import Path

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Regular expression patterns to group permissions from files
ALLOW_VIEW = re.compile(r"\* Set ALLOWWEBVIEW = (.+)")
DENY_VIEW = re.compile(r"\* Set DENYWEBVIEW = (.+)")


class PermissionHandler(BaseModel):
    """
    A class to handle permissions for a given path.
    """

    source_dir: Path
    """The path to the directory containing the permissions files."""

    cache: dict[Path, tuple[str, str]] = Field(default_factory=dict)
    """A cache to store the permissions for each directory."""

    def reset(self) -> None:
        """
        Reset the cache.
        """
        self.cache = {}

    @staticmethod
    def extract(
        file_path: Path,
    ) -> tuple[str, str]:
        """
        Extract the ALLOWWEBVIEW and DENYWEBVIEW permissions from a
        WebPreferences.txt file.

        Parameters
        ----------
        dir_path : str
            The path to the directory containing the WebPreferences.txt
            file. It is assumed that the file exists and is readable.

        Returns
        -------
        tuple[str, str]
            A tuple containing the ALLOWWEBVIEW and DENYWEBVIEW permissions
            for the directory. If the permissions are not found, the values
            will be empty strings.
        """
        allow_view = ""
        deny_view = ""
        with open(file_path, "r") as file:
            content = file.read()
            # Use regular expressions to find ALLOWWEBVIEW and DENYWEBVIEW
            # entries
            allow_match = ALLOW_VIEW.search(content)
            deny_match = DENY_VIEW.search(content)

            if allow_match:
                allow_view = ",".join(
                    sorted(g.strip() for g in allow_match.group(1).split(","))
                )
            if deny_match:
                deny_view = ",".join(
                    sorted(g.strip() for g in deny_match.group(1).split(","))
                )
        return allow_view, deny_view

    def load(self) -> None:
        """
        Load the permissions for each directory in the path.
        The permissions should be stored in a WebPreferences.txt file.
        """
        self.cache = {}
        for dirpath, _, filenames in os.walk(self.source_dir):
            if "WebPreferences.txt" in filenames:
                path = Path(dirpath).resolve()

                permissions = self.extract(path / "WebPreferences.txt")
                if permissions:
                    self.cache[path] = permissions

    def find(self, file_path: Path) -> tuple[str, str]:
        """
        Find the permissions for a given file path.

        Parameters
        ----------
        file_path : Path
            The path to the file for which to find the permissions

        Returns
        -------
        tuple[str, str]
            A tuple containing the ALLOWWEBVIEW and DENYWEBVIEW permissions
            for the directory containing the file. If the permissions are not
            found, the values will be empty strings.
        """
        # Normalize the path to ensure consistency
        for parent in [file_path] + list(file_path.parents):
            if parent in self.cache:
                return self.cache[parent]

        # No permissions found
        return "", ""
