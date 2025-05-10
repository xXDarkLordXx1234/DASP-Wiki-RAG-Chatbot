import rust_python_module  # type: ignore

ResultType = tuple[str, str, list[str]]


class RustModule:
    """A wrapper around the Rust module to provide a Python interface."""

    @staticmethod
    def search_paths(
        paths: list[str], regex_patterns: list[str] | None
    ) -> list[ResultType]:
        """
        Search the given list of file paths and analyse their contents.

        Parameters
        ----------
        paths : list[str]
            The list of file paths to search.
        regex_patterns : list[str] | None
            The list of regex patterns to search for in the files.

        Returns
        -------
        list[ResultType]
            A list of tuples containing the file path, hash, and the results
            of the regex search.
        """
        return rust_python_module.search_paths(  # type: ignore
            paths, regex_patterns
        )

    @staticmethod
    def search_directory(
        directory: str,
        regex_patterns: list[str] | None,
        ignored_files: list[str] | None = None,
        min_file_size: int = 0,
    ) -> list[ResultType]:
        """
        Search the given directory and analyse its contents.

        Parameters
        ----------
        directory : str
            The directory to search.
        regex_patterns : list[str] | None
            The list of regex patterns to search for in the files.
        ignored_files : list[str] | None, optional
            A list of file names to ignore, by default None
        min_file_size : int, optional
            The minimum file size to search, by default 0

        Returns
        -------
        list[ResultType]
            A list of tuples containing the file path, hash, and the results
            of the regex search.
        """
        return rust_python_module.search_directory(  # type: ignore
            str(directory), regex_patterns, ignored_files, min_file_size
        )

    @staticmethod
    def map_authors(
        paths: list[str], author_regex: str, example_author: str
    ) -> list[str]:
        """
        Find the real author of files with the given author regex.

        Parameters
        ----------
        paths : list[str]
            The list of file paths to search.
        author_regex : str
            The regex pattern to search for in the files.
        example_author : str
            The base system author to avoid.

        Returns
        -------
        list[str]
            A list of authors for each file.
        """
        return rust_python_module.map_authors(  # type: ignore
            paths, author_regex, example_author
        )
