"""Test device Monitor"""
import logging
from queue import Empty, Queue

import pytest
import tango
import time

from ska_mid_dish_manager.component_managers.device_monitor import TangoDeviceMonitor

LOGGER = logging.getLogger(__name__)


def empty_func(*args, **kwargs):
    """An empty function"""
    pass  # pylint:disable=unnecessary-pass


def test_device_monitor(caplog, spf_device_fqdn):
    """Device monitoring sanity check"""
    caplog.set_level(logging.DEBUG)
    event_queue = Queue()
    tdm = TangoDeviceMonitor(spf_device_fqdn, ["powerState"], event_queue, LOGGER, empty_func)
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
    """Device monitoring check multi attributes"""
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
    tdm = TangoDeviceMonitor(spf_device_fqdn, test_attributes, event_queue, LOGGER, empty_func)
    tdm.monitor()
    test_attributes_list = list(test_attributes)
    for _ in range(len(test_attributes)):
        event = event_queue.get(timeout=4)
        assert event.item.attr_value.name.lower() in test_attributes_list
        test_attributes_list.remove(event.item.attr_value.name.lower())
    assert not test_attributes_list


def test_device_monitor_stress(caplog):
    """Reconnect many times to see if it recovers"""
    caplog.set_level(logging.DEBUG)
    event_queue = Queue()
    tdm = TangoDeviceMonitor(
        "mid_d0001/spf/simulator", ["powerState"], event_queue, LOGGER, empty_func
    )
    for i in range(20):
        tdm.monitor()
        event = event_queue.get(timeout=4)
        assert tdm._run_count == i + 1  # pylint: disable=W0212
        assert not event.item.err
        assert event.item.attr_value.name == "powerState"
        assert event_queue.empty()

    time.sleep(3)

    all_logs = [record.message for record in caplog.records]

    logging.info(all_logs)
    logging.info(all_logs.count("Subscribed on mid_d0001/spf/simulator to attr powerState"))
    logging.info(all_logs.count("Unsubscribed from mid_d0001/spf/simulator for attr powerState"))

    subscribe_count = all_logs.count("Subscribed on mid_d0001/spf/simulator to attr powerState")
    successful_unsubscribe_count = all_logs.count("Unsubscribed from mid_d0001/spf/simulator for attr powerState")
    unsuccessful_unsubscribe_count = all_logs.count("Could not unsubscribe from mid_d0001/spf/simulator for attr powerState")

    # 20 Subscriptions
    assert subscribe_count == 20
    # 19 Unsubscriptions
    assert (successful_unsubscribe_count + unsuccessful_unsubscribe_count) == 19


def test_connection_error(caplog):
    """Test that connection is retried"""
    caplog.set_level(logging.DEBUG)
    event_queue = Queue()
    tdm = TangoDeviceMonitor("fake_device", ["powerState"], event_queue, LOGGER, empty_func)
    tdm.monitor()
    with pytest.raises(Empty):
        event_queue.get(timeout=8)
    all_logs = [record.message for record in caplog.records]
    for i in range(0, 2):
        assert f"Cannot connect to fake_device try number {i}" in all_logs
