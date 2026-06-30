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
    event_id = spfrx_device_proxy.subscribe_event(
        "spectrumSample",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    event_store.clear_queue()
    spfrx_updated_spectrum_sample = spfrx_device_proxy.spectrumSample = np.ones(
        8202, dtype=np.float32
    )
    event_store.wait_for_value(spfrx_updated_spectrum_sample, timeout=8)
    dish_manager_spectrum_sample = dish_manager_proxy.spectrumSample
    np.testing.assert_array_equal(spfrx_device_proxy.spectrumSample, dish_manager_spectrum_sample)
    spfrx_device_proxy.unsubscribe_event(event_id)
