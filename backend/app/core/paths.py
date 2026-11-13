"""Management document paths, independent of the administrator API namespace."""

WORKSPACE_PATH = "/workspace"


def is_workspace_path(path: str) -> bool:
    return path == WORKSPACE_PATH or path.startswith(f"{WORKSPACE_PATH}/")
