import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)


from src.processor.permission_handler import PermissionHandler  # noqa: E402

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


def create_permissions(
    source_dir: Path, permission: dict[str, list[str]] | None = None
) -> None:
    if permission is None:
        permission = EXAMPLE_PERMISSIONS

    allowed = "      * Set ALLOWWEBVIEW = " + ", ".join(
        permission["allow_web_view"]
    )
    denied = "      * Set DENYWEBVIEW = " + ", ".join(
        permission["deny_web_view"]
    )
    content = allowed + "\n" + denied + "\n"
    with open(source_dir / "WebPreferences.txt", "w") as f:
        f.write(content)


@pytest.fixture
def setup_and_cleanup():
    current_dir = Path(__file__).resolve().parent
    source_dir = current_dir / "test_dir"
    if source_dir.exists():
        shutil.rmtree(source_dir)
    source_dir.mkdir()

    permission_handler = PermissionHandler(source_dir=source_dir)

    yield source_dir, permission_handler

    shutil.rmtree(source_dir)


def test_existing_path(setup_and_cleanup: tuple[Path, PermissionHandler]):
    source_dir, permission_handler = setup_and_cleanup

    create_permissions(source_dir)

    permission_handler.load()

    path = source_dir / "example.txt"

    allow_view, deny_view = permission_handler.find(path)

    assert allow_view == ",".join(EXAMPLE_PERMISSIONS["allow_web_view"])
    assert deny_view == ",".join(EXAMPLE_PERMISSIONS["deny_web_view"])


def test_non_existing_path(setup_and_cleanup: tuple[Path, PermissionHandler]):
    source_dir, permission_handler = setup_and_cleanup

    permission_handler.load()

    path = source_dir / "non_existing.txt"

    allow_view, deny_view = permission_handler.find(path)

    assert allow_view == ""
    assert deny_view == ""


def test_sub_path(setup_and_cleanup: tuple[Path, PermissionHandler]):
    source_dir, permission_handler = setup_and_cleanup

    create_permissions(source_dir)

    permission_handler.load()

    path = source_dir / "sub_dir" / "example.txt"

    allow_view, deny_view = permission_handler.find(path)

    assert allow_view == ",".join(EXAMPLE_PERMISSIONS["allow_web_view"])
    assert deny_view == ",".join(EXAMPLE_PERMISSIONS["deny_web_view"])


def test_reset(setup_and_cleanup: tuple[Path, PermissionHandler]):
    source_dir, permission_handler = setup_and_cleanup

    create_permissions(source_dir)

    permission_handler.load()

    path = source_dir / "example.txt"

    allow_view, deny_view = permission_handler.find(path)

    assert allow_view == ",".join(EXAMPLE_PERMISSIONS["allow_web_view"])
    assert deny_view == ",".join(EXAMPLE_PERMISSIONS["deny_web_view"])

    permission_handler.reset()

    allow_view, deny_view = permission_handler.find(path)

    assert allow_view == ""
    assert deny_view == ""
