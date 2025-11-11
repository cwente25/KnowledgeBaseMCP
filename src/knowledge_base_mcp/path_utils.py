"""Path handling utilities for hierarchical category management."""

import re
from pathlib import Path
from typing import List, Optional


class InvalidPathError(Exception):
    """Raised when a category path is invalid."""
    pass


def normalize_path(path: str) -> str:
    """
    Normalize a category path by removing leading/trailing slashes
    and collapsing multiple slashes.

    Args:
        path: Category path to normalize

    Returns:
        Normalized path

    Examples:
        >>> normalize_path("work//clients/")
        "work/clients"
        >>> normalize_path("/personal/")
        "personal"
    """
    if not path:
        return ""

    # Remove leading and trailing slashes
    path = path.strip("/")

    # Collapse multiple slashes
    path = re.sub(r'/+', '/', path)

    # Remove any ./ or ../ components for security
    parts = path.split("/")
    clean_parts = [p for p in parts if p and p not in (".", "..")]

    return "/".join(clean_parts)


def validate_path(path: str) -> tuple[bool, Optional[str]]:
    """
    Validate a category path.

    Valid paths contain only:
    - Alphanumeric characters (a-z, A-Z, 0-9)
    - Hyphens (-)
    - Underscores (_)
    - Forward slashes (/) as separators

    Args:
        path: Category path to validate

    Returns:
        Tuple of (is_valid, error_message)

    Examples:
        >>> validate_path("work/clients")
        (True, None)
        >>> validate_path("work/cli@nts")
        (False, "Invalid characters in path...")
    """
    if not path:
        return False, "Path cannot be empty"

    # Check for invalid characters
    if not re.match(r'^[a-zA-Z0-9_/-]+$', path):
        return False, (
            f"Invalid characters in path '{path}'. "
            "Only alphanumeric, hyphens, underscores, and forward slashes allowed."
        )

    # Check each component
    parts = path.split("/")
    for part in parts:
        if not part:
            return False, f"Empty component in path '{path}'"

        # Component should not start or end with hyphen/underscore
        if part[0] in ('-', '_') or part[-1] in ('-', '_'):
            return False, (
                f"Path component '{part}' cannot start or end with hyphen or underscore"
            )

    return True, None


def split_path(path: str) -> List[str]:
    """
    Split a category path into its components.

    Args:
        path: Category path

    Returns:
        List of path components

    Examples:
        >>> split_path("work/clients/acme")
        ["work", "clients", "acme"]
    """
    path = normalize_path(path)
    if not path:
        return []
    return path.split("/")


def join_path(*components: str) -> str:
    """
    Safely join path components.

    Args:
        *components: Path components to join

    Returns:
        Joined path

    Examples:
        >>> join_path("work", "clients", "acme")
        "work/clients/acme"
    """
    # Filter out empty components and join
    valid_components = [c.strip("/") for c in components if c and c.strip("/")]
    return "/".join(valid_components)


def get_parent_path(path: str) -> Optional[str]:
    """
    Get the parent directory path.

    Args:
        path: Category path

    Returns:
        Parent path or None if at root level

    Examples:
        >>> get_parent_path("work/clients/acme")
        "work/clients"
        >>> get_parent_path("work")
        None
    """
    path = normalize_path(path)
    if not path or "/" not in path:
        return None

    parts = path.split("/")
    return "/".join(parts[:-1])


def get_category_name(path: str) -> str:
    """
    Get the category name (last component) from a path.

    Args:
        path: Category path

    Returns:
        Category name

    Examples:
        >>> get_category_name("work/clients/acme")
        "acme"
        >>> get_category_name("work")
        "work"
    """
    path = normalize_path(path)
    if not path:
        return ""

    parts = path.split("/")
    return parts[-1]


def get_depth(path: str) -> int:
    """
    Get the depth level of a path (0 for root level).

    Args:
        path: Category path

    Returns:
        Depth level (0 = root, 1 = one level deep, etc.)

    Examples:
        >>> get_depth("work")
        0
        >>> get_depth("work/clients")
        1
        >>> get_depth("work/clients/acme")
        2
    """
    path = normalize_path(path)
    if not path:
        return 0
    return len(path.split("/")) - 1


def is_subpath_of(child_path: str, parent_path: str) -> bool:
    """
    Check if child_path is a subpath of parent_path.

    Args:
        child_path: Potential child path
        parent_path: Potential parent path

    Returns:
        True if child_path is under parent_path

    Examples:
        >>> is_subpath_of("work/clients/acme", "work")
        True
        >>> is_subpath_of("work/clients/acme", "work/clients")
        True
        >>> is_subpath_of("personal", "work")
        False
    """
    child = normalize_path(child_path)
    parent = normalize_path(parent_path)

    if not parent:
        return True  # Everything is under root

    return child.startswith(parent + "/") or child == parent


def would_create_cycle(source_path: str, dest_path: str) -> bool:
    """
    Check if moving source_path to dest_path would create a circular reference.

    Args:
        source_path: Source category path
        dest_path: Destination category path

    Returns:
        True if operation would create a cycle

    Examples:
        >>> would_create_cycle("work", "work/clients")
        True
        >>> would_create_cycle("work/clients", "personal")
        False
    """
    source = normalize_path(source_path)
    dest = normalize_path(dest_path)

    # Moving to itself
    if source == dest:
        return True

    # Moving to its own subdirectory
    if is_subpath_of(dest, source):
        return True

    return False
