"""Management document paths, independent of the administrator API namespace."""

WORKSPACE_PATH = "/workspace"
PREVIEW_PATH = "/preview"


def is_workspace_path(path: str) -> bool:
    return path == WORKSPACE_PATH or path.startswith(f"{WORKSPACE_PATH}/")


def is_preview_path(path: str) -> bool:
    return path.rstrip("/").startswith(f"{PREVIEW_PATH}/")
