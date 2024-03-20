"""Test that all dish manager attributes are configured for events"""
import pytest
import tango


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
def test_attribute_change_events(dish_manager_proxy):
    """Test all attributes have change events configured"""
    dm_attributes = dish_manager_proxy.get_attribute_list()

    all_attr_ch_events_configured = True
    for attribute in dm_attributes:
        try:
            dish_manager_proxy.subscribe_event(
                attribute, tango.EventType.CHANGE_EVENT, tango.utils.EventCallback()
            )
        except tango.DevFailed as err:
            assert err.args[0].reason == "API_AttributePollingNotStarted"
            print(f"Attribute {attribute} does not have a push events configured.")
            all_attr_ch_events_configured = False

    assert all_attr_ch_events_configured


# pylint: disable=too-many-locals,unused-argument
@pytest.mark.acceptance
def test_attribute_archive_events(dish_manager_proxy):
    """Test all attributes have archive events configured"""
    dm_attributes = dish_manager_proxy.get_attribute_list()

    all_attr_arch_events_configured = True
    for attribute in dm_attributes:
        try:
            dish_manager_proxy.subscribe_event(
                attribute, tango.EventType.ARCHIVE_EVENT, tango.utils.EventCallback()
            )
        except tango.DevFailed as err:
            assert err.args[0].reason == "API_AttributePollingNotStarted"
            print(f"Attribute {attribute} does not have a archive events configured.")
            all_attr_arch_events_configured = False

    assert all_attr_arch_events_configured
