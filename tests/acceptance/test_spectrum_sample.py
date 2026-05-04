"""Test SPFRx spectrum sample attribute."""

from typing import Any

import numpy as np
import pytest
import tango


@pytest.mark.acceptance
def test_spectrum_sample_attribute_read(
    dish_manager_proxy: tango.DeviceProxy,
    event_store_class: Any,
    spfrx_device_proxy: tango.DeviceProxy,
):
    """Test that the spectrumSample attribute correctly reports the 8202-length
    float array from the component manager state.
    """
    event_store = event_store_class()
    dish_manager_proxy.subscribe_event(
        "frequencyResponse",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    spfrx_spectrum_sample = spfrx_device_proxy.read_attribute("spectrumSample").value
    spectrum_sample_expected_value = dish_manager_proxy.read_attribute("frequencyResponse").value
    # Wait for the first value to be read and emitted as an event
    event_store.wait_for_value(spectrum_sample_expected_value, timeout=7)
    assert isinstance(spectrum_sample_expected_value, np.ndarray)
    assert spectrum_sample_expected_value.shape == (8202,)
    assert spfrx_spectrum_sample == spectrum_sample_expected_value
    dish_manager_proxy.unsubscribe_event()
