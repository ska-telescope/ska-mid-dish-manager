"""This module provides utility functions for interacting with Tango devices."""

import logging
from typing import List, Optional

import tango


class TangoDbAccessor:
    """A class to access Tango device properties."""

    def __init__(self, logger: logging.Logger, tango_device_name: str):
        self._logger = logger
        self._tango_device_name = tango_device_name
        self._database = tango.Database()

    def get_device_property_value(self, property_name: str) -> Optional[List[str]]:
        """Read device property value from TangoDB.

        :param property_name: Tango device property name
        :type property_name: str
        :return: value for the given property
        :rtype: Optional[str]
        """
        self._logger.debug("Getting device property value for %s.", property_name)
        try:
            device_properties = self._database.get_device_property(
                self._tango_device_name, property_name
            )
            property_values = device_properties.get(property_name)
            return property_values
        except tango.DevFailed as e:
            self._logger.error("Failed to read property %s: %s", property_name, e)
        return None

    def set_device_property_value(self, property_name: str, value: str) -> None:
        """Set a device property value in TangoDB.

        :param property_name: Tango device property name
        :type property_name: str
        :param value: Value to set for the property
        :type value: str
        """
        self._logger.debug("Setting device property %s to value %s.", property_name, value)
        try:
            self._database.put_device_property(self._tango_device_name, {property_name: value})
        except tango.DevFailed as e:
            self._logger.error("Failed to set property %s: %s", property_name, e)

    def get_device_attribute_property_value(self, attribute_name, device_name) -> Optional[str]:
        """Read memorized attributes values from TangoDB.

        :param: attribute_name: Tango attribute name
        :type attribute_name: str
        :return: value for the given attribute
        :rtype: Optional[str]
        """
        self._logger.debug("Getting attribute property value for %s.", attribute_name)
        database = tango.Database()
        attr_property = database.get_device_attribute_property(device_name, attribute_name)
        attr_property_value = attr_property[attribute_name]
        if len(attr_property_value) > 0:  # If the returned dict is not empty
            return attr_property_value["__value"][0]
        return None
