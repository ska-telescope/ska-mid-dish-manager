"""Helper utilities for the ska-mid-dish-manager package."""

import enum
import logging
from typing import Any, Callable, Optional

import tango


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


def get_device_attribute_property_value(
    attribute_name, device_name, logger=logging.getLogger(__name__)
) -> Optional[str]:
    """Read memorized attributes values from TangoDB.

    :param: attribute_name: Tango attribute name
    :type attribute_name: str
    :return: value for the given attribute
    :rtype: Optional[str]
    """
    logger.debug("Getting attribute property value for %s.", attribute_name)
    database = tango.Database()
    attr_property = database.get_device_attribute_property(device_name, attribute_name)
    attr_property_value = attr_property[attribute_name]
    if len(attr_property_value) > 0:  # If the returned dict is not empty
        return attr_property_value["__value"][0]
    return None
