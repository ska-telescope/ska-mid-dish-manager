"""Unit tests for TangoDbAccessor class."""

import logging
from unittest.mock import Mock, patch

import tango

from ska_mid_dish_manager.utils.tango_helpers import TangoDbAccessor


class TestTangoDbAccessor:
    """Test cases for TangoDbAccessor class."""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        self.logger = Mock(spec=logging.Logger)
        self.device_name = "test/device/01"
        self.mock_database = Mock(spec=tango.Database)

        # Patch the tango.Database constructor to return our mock
        self.database_patcher = patch("ska_mid_dish_manager.utils.tango_helpers.tango.Database")
        self.mock_database_class = self.database_patcher.start()
        self.mock_database_class.return_value = self.mock_database

        self.accessor = TangoDbAccessor(self.logger, self.device_name)

    def teardown_method(self):
        """Clean up after each test method."""
        self.database_patcher.stop()

    def test_init(self):
        """Test TangoDbAccessor initialization."""
        self.mock_database_class.assert_called_once()

    def test_get_device_property_value_success(self):
        """Test successful retrieval of device property value."""
        property_name = "TestProperty"
        expected_values = ["value1", "value2"]
        mock_properties = {property_name: expected_values}
        self.mock_database.get_device_property.return_value = mock_properties

        result = self.accessor.get_device_property_value(property_name)

        assert result == expected_values
        self.mock_database.get_device_property.assert_called_once_with(
            self.device_name, property_name
        )

    def test_get_device_property_value_empty_list(self):
        """Test retrieval when property exists but has empty value."""
        property_name = "EmptyProperty"
        expected_values = []
        mock_properties = {property_name: expected_values}
        self.mock_database.get_device_property.return_value = mock_properties

        result = self.accessor.get_device_property_value(property_name)

        assert result == expected_values

    def test_get_device_property_value_tango_exception(self):
        """Test handling of tango.DevFailed exception during property retrieval."""
        property_name = "TestProperty"
        self.mock_database.get_device_property.side_effect = tango.DevFailed()
        result = self.accessor.get_device_property_value(property_name)

        assert result is None
        self.mock_database.get_device_property.assert_called_once_with(
            self.device_name, property_name
        )

    def test_set_device_property_value_success(self):
        """Test successful setting of device property value."""
        property_name = "TestProperty"
        property_value = "test_value"

        self.accessor.set_device_property_value(property_name, property_value)

        self.mock_database.put_device_property.assert_called_once_with(
            self.device_name, {property_name: property_value}
        )

    def test_set_device_property_value_tango_exception(self):
        """Test handling of tango.DevFailed exception during property setting."""
        property_name = "TestProperty"
        property_value = "test_value"

        self.mock_database.put_device_property.side_effect = tango.DevFailed()

        self.accessor.set_device_property_value(property_name, property_value)

        self.mock_database.put_device_property.assert_called_once_with(
            self.device_name, {property_name: property_value}
        )
