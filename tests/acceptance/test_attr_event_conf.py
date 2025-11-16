"""Test that all dish manager attributes are configured for events."""

import pytest
import tango

from tests.utils import remove_subscriptions, setup_subscriptions

IGNORE_ATTRIBUTES_LIST = [
    "lrcProtocolVersions",
]


@pytest.mark.acceptance
def test_attribute_change_events(dish_manager_proxy):
    """Test all attributes have change events configured."""
    all_attributes = dish_manager_proxy.get_attribute_list()
    dm_attributes = [a for a in all_attributes if a not in IGNORE_ATTRIBUTES_LIST]
    callback = tango.utils.EventCallback()
    attr_cb_mapping = {attribute: callback for attribute in dm_attributes}

    all_attr_ch_events_configured = True
    err_msg = ""
    subscriptions = {}

    try:
        subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)
    except tango.DevFailed as err:
        assert err.args[0].reason == "API_AttributePollingNotStarted", err
        err_msg = err.args[0].desc
        all_attr_ch_events_configured = False
    finally:
        remove_subscriptions(subscriptions)

    assert all_attr_ch_events_configured, err_msg


@pytest.mark.acceptance
def test_attribute_archive_events(dish_manager_proxy):
    """Test all attributes have archive events configured."""
    all_attributes = dish_manager_proxy.get_attribute_list()
    dm_attributes = [a for a in all_attributes if a not in IGNORE_ATTRIBUTES_LIST]
    callback = tango.utils.EventCallback()
    attr_cb_mapping = {attribute: callback for attribute in dm_attributes}

    all_attr_arch_events_configured = True
    err_msg = ""
    subscriptions = {}

    try:
        subscriptions = setup_subscriptions(
            dish_manager_proxy, attr_cb_mapping, tango.EventType.ARCHIVE_EVENT
        )
    except tango.DevFailed as err:
        assert err.args[0].reason == "API_AttributePollingNotStarted", err
        err_msg = err.args[0].desc
        all_attr_arch_events_configured = False
    finally:
        remove_subscriptions(subscriptions)

    assert all_attr_arch_events_configured, err_msg
