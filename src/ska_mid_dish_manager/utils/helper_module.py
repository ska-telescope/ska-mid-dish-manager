"""Helper utilities for the ska-mid-dish-manager package."""

import enum
from typing import Any, Callable, Optional


def convert_enums_to_names(values: list[Any]) -> list[str]:
    """Convert any enums in the given list to their names."""
    enum_labels = []
    for val in values:
        if isinstance(val, enum.IntEnum):
            enum_labels.append(val.name)
        else:
            enum_labels.append(val)
    return enum_labels


def update_task_status(task_callback: Optional[Callable], **task_statuses) -> None:
    """Wraps the task callback to report lrc statuses."""
    if task_callback:
        task_callback(**task_statuses)
