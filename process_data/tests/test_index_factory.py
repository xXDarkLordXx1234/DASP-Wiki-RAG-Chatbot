import os
import shutil
import sys
from pathlib import Path
from typing import Any

import polars as pl
import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)


from src.processor.change_types import ChangeType  # noqa: E402
from src.processor.index_factory import IndexFactory  # noqa: E402

EXAMPLE_PERMISSIONS: dict[str, list[str]] = {
    "allow_web_view": [
        "Main.group-1",
        "Main.group-2",
    ],
    "deny_web_view": [
        "Main.group-3",
        "Main.group-4",
    ],
}

EXAMPLE_METADATA: dict[str, str | int] = {
    "author": "test user",
    "comment": "test comment",
    "date": 12345,
    "format": "1.1",
    "reprev": 123,
    "version": 12,
    "topic_parent": "test topic parent",
    "allow_view": ",".join(EXAMPLE_PERMISSIONS["allow_web_view"]),
    "deny_view": ",".join(EXAMPLE_PERMISSIONS["deny_web_view"]),
}


def create_permissions(
    source_dir: Path, permission: dict[str, list[str]] | None = None
) -> None:
    if permission is None:
        permission = EXAMPLE_PERMISSIONS

    header = get_content(**EXAMPLE_METADATA)
    allowed = "      * Set ALLOWWEBVIEW = " + ", ".join(
        permission["allow_web_view"]
    )
    denied = "      * Set DENYWEBVIEW = " + ", ".join(
        permission["deny_web_view"]
    )
    content = header + "\n" + allowed + "\n" + denied + "\n"
    with open(source_dir / "WebPreferences.txt", "w") as f:
        f.write(content)


def get_content(**kwargs: Any) -> str:
    topic_info = (
        "{"
        + " ".join(
            f'{key}="{value}"'
            for key, value in kwargs.items()
            if key
            in ["author", "comment", "date", "format", "reprev", "version"]
        )
        + "}"
    )
    header = (
        f"%META:TOPICINFO{topic_info}%\n"
        f'%META:TOPICPARENT{{name="{kwargs["topic_parent"]}"}}%\n'
    )

    body = "Hello World!\n" * 25

    return header + body


def change_assertions(
    change_row: pl.DataFrame,
    file_path: Path,
    change_type: str,
    metadata: dict[str, str | int],
):
    assert change_row.get_column("path")[0] == str(file_path)
    assert change_row.get_column("change_type")[0] == change_type
    assert change_row.get_column("author")[0] == metadata["author"]
    assert change_row.get_column("comment")[0] == metadata["comment"]
    assert change_row.get_column("date")[0] == metadata["date"]
    assert change_row.get_column("format")[0] == metadata["format"]
    assert change_row.get_column("reprev")[0] == metadata["reprev"]
    assert change_row.get_column("version")[0] == metadata["version"]
    assert change_row.get_column("topicparent")[0] == metadata["topic_parent"]
    assert change_row.get_column("allow_view")[0] == metadata["allow_view"]
    assert change_row.get_column("deny_view")[0] == metadata["deny_view"]


@pytest.fixture
def setup_and_cleanup():
    current_dir = Path(__file__).resolve().parent
    source_dir = current_dir / "test_dir"
    if source_dir.exists():
        shutil.rmtree(source_dir)
    source_dir.mkdir()

    create_permissions(source_dir)

    index_factory = IndexFactory(
        source_dir=source_dir,
        index_path=Path("test_index.parquet"),
    )

    yield source_dir, index_factory

    index_factory.reset()

    shutil.rmtree(source_dir)


@pytest.mark.asyncio
async def test_file_creation(setup_and_cleanup: tuple[Path, IndexFactory]):
    source_dir, index_factory = setup_and_cleanup
    file_path = source_dir / "test.txt"

    await index_factory.get_changes()

    with open(file_path, "w") as f:
        f.write(get_content(**EXAMPLE_METADATA))

    changes = await index_factory.get_changes()

    assert changes is not None
    assert len(changes) == 1
    change_assertions(
        changes[0], file_path, ChangeType.ADDED, EXAMPLE_METADATA
    )


@pytest.mark.asyncio
async def test_file_deletion(setup_and_cleanup: tuple[Path, IndexFactory]):
    source_dir, index_factory = setup_and_cleanup
    file_path = source_dir / "test.txt"

    with open(file_path, "w") as f:
        f.write(get_content(**EXAMPLE_METADATA))

    await index_factory.get_changes()

    os.remove(file_path)

    changes = await index_factory.get_changes()

    assert changes is not None
    assert len(changes) == 1
    assert changes[0].get_column("path")[0] == str(file_path)
    assert changes[0].get_column("change_type")[0] == ChangeType.DELETED


@pytest.mark.asyncio
async def test_file_modification(setup_and_cleanup: tuple[Path, IndexFactory]):
    source_dir, index_factory = setup_and_cleanup

    file_path = source_dir / "test.txt"

    with open(file_path, "w") as f:
        f.write(get_content(**EXAMPLE_METADATA))

    await index_factory.get_changes()

    with open(file_path, "a") as f:
        f.write("Hello, World!")

    changes = await index_factory.get_changes()

    assert changes is not None
    assert len(changes) == 1
    change_assertions(
        changes[0], file_path, ChangeType.MODIFIED, EXAMPLE_METADATA
    )


@pytest.mark.asyncio
async def test_permissions_modification(
    setup_and_cleanup: tuple[Path, IndexFactory]
):
    source_dir, index_factory = setup_and_cleanup

    file_path = source_dir / "test.txt"

    with open(file_path, "w") as f:
        f.write(get_content(**EXAMPLE_METADATA))

    await index_factory.get_changes()

    new_permissions: dict[str, list[str]] = {
        "allow_web_view": ["new-group"],
        "deny_web_view": ["new-group-2"],
    }

    create_permissions(source_dir, new_permissions)

    changes = await index_factory.get_changes()

    assert changes is not None
    assert len(changes) == 2

    metadata = EXAMPLE_METADATA.copy()

    metadata["allow_view"] = ",".join(new_permissions["allow_web_view"])
    metadata["deny_view"] = ",".join(new_permissions["deny_web_view"])

    changes = changes.filter(pl.col("path") == str(file_path))

    change_assertions(changes[0], file_path, ChangeType.MODIFIED, metadata)


@pytest.mark.asyncio
async def test_file_modification_no_change(
    setup_and_cleanup: tuple[Path, IndexFactory]
):
    source_dir, index_factory = setup_and_cleanup
    file_path = source_dir / "test.txt"

    with open(file_path, "w") as f:
        f.write(get_content(**EXAMPLE_METADATA))

    await index_factory.get_changes()

    with open(file_path, "a") as f:
        f.write("")

    changes = await index_factory.get_changes()

    assert changes is None


@pytest.mark.asyncio
async def test_reset(setup_and_cleanup: tuple[Path, IndexFactory]):
    source_dir, index_factory = setup_and_cleanup
    file_path = source_dir / "test.txt"

    await index_factory.get_changes()

    with open(file_path, "w") as f:
        f.write(get_content(**EXAMPLE_METADATA))

    changes = await index_factory.get_changes()

    index_factory.reset()

    assert not index_factory.index_path.exists()

    changes = await index_factory.get_changes()

    assert changes is not None
    assert len(changes) == 2
