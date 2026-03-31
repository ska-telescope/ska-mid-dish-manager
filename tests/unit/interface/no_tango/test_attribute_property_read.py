"""Test that we handle cases from DB read."""

import logging
from unittest import mock
from unittest.mock import MagicMock

import pytest

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


@pytest.mark.unit
@pytest.mark.parametrize(
    "read_response,expected_response",
    [
        # Valid
        ({"ignoreSpfrx": {"__value": ["true"]}}, "true"),
        ({"ignoreSpfrx": {"ignoreSpfrx": ["true"]}}, "true"),
        # Invalid
        ({"ignoreSpfrx": {}}, None),
        ({"ignoreSpfrx": {"ignoreSpfrx": []}}, None),
        ({"something_else": {"__value": []}}, None),
        ({"something_else": {"__value": ["true"]}}, None),
        ({"something_else": {"something_else": ["true"]}}, None),
    ],
)
def test_get_attribute_property_value(
    mock_command_tracker: MagicMock, callbacks: dict, read_response, expected_response
):
    """Test the attribute property read."""
    with mock.patch(
        "ska_mid_dish_manager.component_managers.dish_manager_cm.tango.Database"
    ) as mocked_tangodb:
        database_mock = MagicMock(name="database_mock")
        database_mock.get_device_attribute_property.return_value = read_response
        mocked_tangodb.return_value = database_mock

        dish_manager_cm = DishManagerComponentManager(
            logging.getLogger(__name__),
            mock_command_tracker,
            callbacks["build_state_cb"],
            callbacks["quality_state_cb"],
            "device-1",
            "sub-device-1",
            "sub-device-2",
            "sub-device-3",
            "sub-device-4",
            action_timeout_s=120,
            communication_state_callback=callbacks["comm_state_cb"],
            component_state_callback=callbacks["comp_state_cb"],
            command_progress_callback=callbacks["progress_cb"],
        )
        dish_manager_cm.try_update_memorized_attributes_from_db
        result = dish_manager_cm._get_device_attribute_property_value("ignoreSpfrx")

        assert result == expected_response, (
            "Expected [{expected_response}], but got [{result}] for [{read_response}]"
        )
