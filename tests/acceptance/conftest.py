"""Tests for running ska-mid-dish-manager acceptance tests"""

import pytest
import tango

from ska_mid_dish_manager.models.dish_enums import DishMode


def get_ds_init_values():
    """Returns the values for a freshly started DS device"""
    return {
        "non_polled_attr_1": 79.0,
        "polled_attr_1": 38,
        "operatingMode": 2,
        "pointingState": 4,
        "healthState": 0,
        "powerState": 0,
        "indexerPosition": 0,
        "configuredBand": 0,
        "achievedPointing": (0.0, 0.0, 30.0),
        "desiredPointing": (0.0, 0.0, 30.0),
    }


def get_spf_init_values():
    """Returns the values for a freshly started SPF device"""
    return {
        "skipAttributeUpdates": False,
        "b1CapabilityState": 1,
        "b2CapabilityState": 1,
        "b3CapabilityState": 1,
        "b4CapabilityState": 1,
        "b5aCapabilityState": 1,
        "b5bCapabilityState": 1,
        "operatingMode": 2,
        "bandInFocus": 0,
        "healthState": 0,
        "powerState": 1,
    }


def get_spfrx_init_values():
    """Returns the values for a freshly started SPFRx device"""
    return {
        "b1CapabilityState": 2,
        "b2CapabilityState": 2,
        "b3CapabilityState": 2,
        "b4CapabilityState": 2,
        "b5aCapabilityState": 2,
        "b5bCapabilityState": 2,
        "operatingMode": 2,
        "healthState": 0,
        "configuredBand": 0,
        "capturingData": False,
    }


def save_tango_device_attribute_state(device_proxy):
    """Saves the devices monitored attributes to a dictionary"""
    state = {}

    for attr in device_proxy.get_attribute_list():
        try:
            state[attr] = device_proxy.read_attribute(attr).value
        except Exception:  # pylint:disable=broad-except
            continue

    return state


def restore_tango_device_attribute_state(device_proxy, state):
    """Uses a dictionary of attributes and updates the tango devices attributes"""
    for attr in device_proxy.get_attribute_list():
        attribute_config = device_proxy.get_attribute_config(attr)

        if str(attribute_config.writable) == "READ_WRITE":
            if attr in state:
                try:
                    device_proxy.write_attribute(attr, state[attr])
                except Exception:  # pylint:disable=broad-except
                    continue


@pytest.fixture(autouse=True)
def setup_and_teardown(
    event_store,
    dish_manager_proxy,
    ds_device_proxy,
    spf_device_proxy,
    spfrx_device_proxy,
):
    """Reset the tango devices to a fresh state before each test"""
    # Code that will run before the test
    proxies = [
        ds_device_proxy,
        spf_device_proxy,
        spfrx_device_proxy,
    ]

    initial_states = [
        get_ds_init_values(),
        get_spf_init_values(),
        get_spfrx_init_values(),
    ]

    # initial_states = []

    for proxy, state in zip(proxies, initial_states):
        restore_tango_device_attribute_state(proxy, state)
        initial_state = save_tango_device_attribute_state(proxy)

        print(f"\nInitial state ({proxy})")
        print("===================================================")
        print(state)

        print(f"\nState after restoring initial ({proxy})")
        print("===================================================")
        print(initial_state)

        # initial_states.append(initial_state)

    dish_manager_proxy.synccomponentstates()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    print("\ndishMode:", dish_manager_proxy.dishMode)

    assert event_store.wait_for_value(DishMode.STANDBY_LP)

    # assert False

    # A test function will be run at this point
    yield

    # Code that will run after the test:
    # proxies.reverse()

    # for proxy in proxies:
    #     initial_state = initial_states.pop()

    #     restore_tango_device_attribute_state(proxy, initial_state)
