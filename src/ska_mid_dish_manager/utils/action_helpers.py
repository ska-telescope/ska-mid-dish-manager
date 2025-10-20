"""Shared methods handling ."""

import enum
from typing import Callable, Optional


def check_component_state_matches_awaited(component_state: dict, awaited_state: dict) -> bool:
    """Check if the given component state matches the awaited state."""
    for awaited_attr, awaited_attr_value in awaited_state.items():
        if awaited_attr not in component_state:
            return False
        component_state_attr_value = component_state[awaited_attr]
        if component_state_attr_value != awaited_attr_value:
            return False
    return True


def update_task_status(task_callback: Optional[Callable], **task_statuses) -> None:
    """Wraps the task callback to report lrc statuses."""
    if task_callback:
        task_callback(**task_statuses)


def convert_enums_to_names(values) -> list[str]:
    """Convert any enums in the given list to their names."""
    enum_labels = []
    for val in values:
        if isinstance(val, enum.IntEnum):
            enum_labels.append(val.name)
        else:
            enum_labels.append(val)
    return enum_labels


def report_awaited_attributes(task_callback, awaited_attributes, awaited_values, device=None):
    """Report the awaited attributes and their expected values."""
    if awaited_values:
        awaited_attributes = ", ".join(awaited_attributes)
        awaited_values = convert_enums_to_names(awaited_values)
        awaited_values = ", ".join(map(str, awaited_values))
        if device:
            msg = f"Awaiting {device} {awaited_attributes} change to {awaited_values}"
        else:
            msg = f"Awaiting {awaited_attributes} change to {awaited_values}"

        update_task_status(task_callback, progress=msg)
