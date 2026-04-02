from unittest import mock

import pytest
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import (
    TangoDeviceComponentManager,
)


@pytest.mark.unit
@pytest.mark.parametrize(
    "monitored_attrs, current_subs, new_attr, expected_trigger",
    [
        (["attr1", "attr2"], {"attr1"}, "attr2", True),  # in monitored, grows == True
        (
            ["attr1", "attr2"],
            {"attr1", "attr2"},
            "attr2",
            False,
        ),  # in monitored, no growth == False
        (["attr1", "attr2"], {"attr1"}, "attr3", False),  # not monitored, grows == False
    ],
)
def test_sync_communication_conditional(monitored_attrs, current_subs, new_attr, expected_trigger):
    cm = TangoDeviceComponentManager(
        tango_device_fqdn="test/device",
        logger=mock.MagicMock(),
        monitored_attributes=monitored_attrs,
    )

    # Set up initial subscriptions
    cm._active_attr_event_subscriptions = set(current_subs)

    # Patch logger and methods that are called if condition triggers
    cm.logger = mock.MagicMock()
    cm._update_communication_state = mock.MagicMock()
    cm._fetch_build_state_information = mock.MagicMock()

    # Call the method
    cm.sync_communication_to_valid_event(new_attr)

    # All cases: the attribute is added to subscriptions
    assert new_attr in cm._active_attr_event_subscriptions

    if expected_trigger:
        cm._update_communication_state.assert_called_once_with(CommunicationStatus.ESTABLISHED)
        cm._fetch_build_state_information.assert_called_once()
        cm.logger.info.assert_called_once()
    else:
        cm._update_communication_state.assert_not_called()
        cm._fetch_build_state_information.assert_not_called()
        cm.logger.info.assert_not_called()
