"""Test device Monitor."""

import logging
from functools import partial
from queue import Empty, Queue
from threading import Event

import pytest
import tango
from mock import MagicMock

from ska_mid_dish_manager.component_managers.device_monitor import TangoDeviceMonitor
from ska_mid_dish_manager.component_managers.device_proxy_factory import DeviceProxyManager

LOGGER = logging.getLogger(__name__)


# TODO These tests are not marked with the acceptance marker,
# so are not executed in CI,need to add the marker and make sure they run
def test_device_monitor(monitor_tango_servers, caplog, spf_device_fqdn):
    """Device monitoring sanity check."""
    # TODO all the tests dont have a marker so are not executed, fix this
    caplog.set_level(logging.DEBUG)
    event_queue = Queue()
    device_proxy_factory = DeviceProxyManager(LOGGER, Event())
    tdm = TangoDeviceMonitor(
        spf_device_fqdn, device_proxy_factory, ["powerState"], event_queue, LOGGER
    )
    tdm.monitor()
    event = event_queue.get(timeout=4)
    # Make sure we end up connected, may take a second or so to come through
    event_data = event.item

    assert not event_data.err
    assert event_data.attr_value.name == "powerState"
    assert event_queue.empty()
    spf_device = tango.DeviceProxy(spf_device_fqdn)
    spf_device.powerState = 1
    spf_device.powerState = 2
    event = event_queue.get(timeout=4)
    if event.item.attr_value.value == 1:
        # Just skip the first update, if any, may already be 1
        event = event_queue.get(timeout=4)
    assert event.item.attr_value.value == 2


def test_multi_monitor(caplog, spf_device_fqdn):
    """Device monitoring check multi attributes."""
    test_attributes = (
        "operatingmode",
        "powerstate",
        "healthstate",
        "bandinfocus",
        "b1capabilitystate",
        "b2capabilitystate",
        "b3capabilitystate",
        "b4capabilitystate",
        "b5acapabilitystate",
        "b5bcapabilitystate",
    )
    caplog.set_level(logging.DEBUG)
    event_queue = Queue()
    device_proxy_factory = DeviceProxyManager(LOGGER, Event())
    tdm = TangoDeviceMonitor(
        spf_device_fqdn, device_proxy_factory, test_attributes, event_queue, LOGGER
    )
    tdm.monitor()
    test_attributes_list = list(test_attributes)
    for _ in range(len(test_attributes)):
        event = event_queue.get(timeout=4)
        assert event.item.attr_value.name.lower() in test_attributes_list
        test_attributes_list.remove(event.item.attr_value.name.lower())
    assert not test_attributes_list


def test_device_monitor_stress(spf_device_fqdn):
    """Reconnect many times to see if it recovers."""
    logs_queue = Queue()

    def add_log(logs_queue, *args):
        logs_queue.put(args)

    mocked_logger = MagicMock()
    mocked_logger.info.side_effect = partial(add_log, logs_queue)
    mocked_logger.debug.side_effect = partial(add_log, logs_queue)

    event_queue = Queue()
    device_proxy_factory = DeviceProxyManager(mocked_logger, Event())
    tdm = TangoDeviceMonitor(
        spf_device_fqdn, device_proxy_factory, ["powerState"], event_queue, mocked_logger
    )
    for i in range(10):
        tdm.monitor()
        event = event_queue.get(timeout=4)
        assert tdm._run_count == i + 1  # pylint: disable=W0212
        assert not event.item.err
        assert event.item.attr_value.name == "powerState"
        assert event_queue.empty()
        # Wait a bit for things to settle
        try:
            event_queue.get(timeout=0.5)
        except Empty:
            pass

    all_logs = []
    while not logs_queue.empty():
        all_logs.append(str(logs_queue.get(timeout=3)))

    assert (
        all_logs.count(
            "('Unsubscribed from %s for attr %s', 'mid-dish/simulator-spfc/SKA001', 'powerState')"
        )
        == 9
    )
    assert (
        all_logs.count(
            "('Subscribed on %s to attr %s', 'mid-dish/simulator-spfc/SKA001', 'powerState')"
        )
        == 10
    )


def test_connection_error(caplog):
    """Test that connection is retried."""
    caplog.set_level(logging.DEBUG)
    event_queue = Queue()
    device_proxy_factory = DeviceProxyManager(LOGGER, Event())
    tdm = TangoDeviceMonitor(
        "fake_device", device_proxy_factory, ["powerState"], event_queue, LOGGER
    )
    tdm.monitor()
    with pytest.raises(Empty):
        event_queue.get(timeout=8)
    all_logs = [record.message for record in caplog.records]
    for i in range(0, 2):
        assert f"Cannot connect to fake_device try number {i}" in all_logs
