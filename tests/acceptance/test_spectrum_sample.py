"""Test SPFRx spectrum sample attribute."""

import pytest
import time
import numpy as np
import tango


def test_spectrum_sample_attribute_read(dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
    spfrx_device_proxy: tango.DeviceProxy
):
    """
    Test that the spectrumSample attribute correctly reports the 8202-length
    float array from the component manager state.
    """
    event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "spectrumSample", tango.EventType.CHANGE_EVENT, event_store
    )

    # Wait for the first value to be read and emitted as an event
    event_store.wait_for_value(timeout=7)
    spfrx_spectrum_sample = spfrx_device_proxy.read_attribute("spectrumSample").value
    expected_value = dish_manager_proxy.read_attribute("spectrumSample").value
    assert isinstance(expected_value, np.ndarray)
    assert expected_value.shape == (8202,)
    assert spfrx_spectrum_sample == expected_value
    dish_manager_proxy.unsubscribe_event()

