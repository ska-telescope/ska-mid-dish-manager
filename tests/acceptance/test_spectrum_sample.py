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

    spectrum_sample_initial_value = dish_manager_proxy.frequencyResponse
    spfrx_spectrum_sample = spfrx_device_proxy.spectrumSample
    # Wait for the initial sample value to be read and emitted as an event
    event_store.wait_for_value(spfrx_spectrum_sample, timeout=7)
    assert len(spectrum_sample_initial_value) == 8202
    spfrx_updated_spectrum_sample = spfrx_device_proxy.spectrumSample = np.ones(
        8202, dtype=np.float32
    )
    event_store.wait_for_value(spfrx_updated_spectrum_sample, timeout=7)
    dish_manager_proxy.unsubscribe_event()
