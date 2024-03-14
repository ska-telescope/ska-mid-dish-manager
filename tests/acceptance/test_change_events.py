"""Test that all dish manager attributes are configured for events"""
import pytest
import tango


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
def test_attribute_events(dish_manager_proxy):
    dm_attributes = dish_manager_proxy.get_attribute_list()

    all_attr_ch_events_configured = True
    for attribute in dm_attributes:
        try:
            dish_manager_proxy.subscribe_event(
                attribute, tango.EventType.CHANGE_EVENT, tango.utils.EventCallback()
            )
        except tango.DevFailed as e:
            assert e.args[0].reason == "API_AttributePollingNotStarted"
            print(f"Attribute {attribute} does not have a push events configured.")
            all_attr_ch_events_configured = False

    assert all_attr_ch_events_configured
