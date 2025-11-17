"""Shared methods handling ."""

import enum
from typing import Any, Callable, Optional


def check_component_state_matches_awaited(component_state: dict, awaited_state: dict) -> bool:
    """Check if the given component state matches the awaited state."""
    for awaited_attr, awaited_attr_value in awaited_state.items():
        if awaited_attr not in component_state:
            return False
        component_state_attr_value = component_state[awaited_attr]
        if component_state_attr_value != awaited_attr_value:
            return False
    return True


def update_task_status(task_callback: Optional[Callable], **task_statuses: Any) -> None:
    """Wraps the task callback to report lrc statuses."""
    if task_callback:
        task_callback(**task_statuses)


def report_task_progress(
    progress_msg: str, command_progress_callback: Optional[Callable] = None
) -> None:
    """Wraps the command progress callback to update device status."""
    if command_progress_callback:
        command_progress_callback(progress_msg)


def convert_enums_to_names(values: list[Any]) -> list[str]:
    """Convert any enums in the given list to their names."""
    enum_labels = []
    for val in values:
        if isinstance(val, enum.IntEnum):
            enum_labels.append(val.name)
        else:
            enum_labels.append(val)
    return enum_labels


def report_awaited_attributes(
    progress_callback: Optional[Callable],
    awaited_attributes: list[Any],
    awaited_values: list[Any],
    device: Any = None,
) -> None:
    """Report the awaited attributes and their expected values."""
    if awaited_values:
        attributes_str = ", ".join(awaited_attributes)
        values_str = convert_enums_to_names(awaited_values)
        values_str = ", ".join(map(str, values_str))

        if device:
            msg = f"Awaiting {device} {attributes_str} change to {values_str}"
        else:
            msg = f"Awaiting {attributes_str} change to {values_str}"

        report_task_progress(msg, progress_callback)
