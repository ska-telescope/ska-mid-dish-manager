"""Test device Monitor"""
import logging
from queue import Empty, Queue

import pytest
import tango
from mock import MagicMock, call
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.device_monitor import TangoDeviceMonitor

LOGGER = logging.getLogger(__name__)


def test_device_monitor(caplog, spf_device_fqdn):
    """Device monitoring sanity check"""
    caplog.set_level(logging.DEBUG)
    event_queue = Queue()
    callback_mock = MagicMock()
    tdm = TangoDeviceMonitor(spf_device_fqdn, ["powerState"], event_queue, LOGGER, callback_mock)
    tdm.monitor()
    event = event_queue.get(timeout=4)
    # Make sure we end up connected, may take a second or so to come through
    if len(callback_mock.call_args_list) != 2:
        with pytest.raises(Empty):
            event_queue.get(timeout=2)
    assert callback_mock.call_args_list[0] == call(CommunicationStatus.NOT_ESTABLISHED)
    assert callback_mock.call_args_list[1] == call(CommunicationStatus.ESTABLISHED)
    assert not event.err
    assert event.attr_value.name == "powerState"
    assert event_queue.empty()
    spf_device = tango.DeviceProxy(spf_device_fqdn)
    spf_device.powerState = 1
    spf_device.powerState = 2
    event = event_queue.get(timeout=4)
    if event.attr_value.value == 1:
        # Just skip the first update, if any, may already be 1
        event = event_queue.get(timeout=4)
    assert event.attr_value.value == 2


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
    callback_mock = MagicMock()
    tdm = TangoDeviceMonitor(spf_device_fqdn, test_attributes, event_queue, LOGGER, callback_mock)
    tdm.monitor()
    test_attributes_list = list(test_attributes)
    for _ in range(len(test_attributes)):
        event = event_queue.get(timeout=4)
        assert event.attr_value.name.lower() in test_attributes_list
        test_attributes_list.remove(event.attr_value.name.lower())
    callback_mock.assert_called_with(CommunicationStatus.ESTABLISHED)
    assert not test_attributes_list


def test_device_monitor_stress(caplog):
    """Reconnect many times to see if it recovers"""
    caplog.set_level(logging.DEBUG)
    event_queue = Queue()
    callback_mock = MagicMock()
    tdm = TangoDeviceMonitor(
        "mid_d0001/spf/simulator", ["powerState"], event_queue, LOGGER, callback_mock
    )
    for i in range(20):
        tdm.monitor()
        assert tdm._run_count == i + 1  # pylint: disable=W0212
        event = event_queue.get(4)
        assert not event.err
        assert event.attr_value.name == "powerState"
        assert event_queue.empty()
    all_logs = [record.message for record in caplog.records]
    # 20 Subscriptions
    assert all_logs.count("Subscribed on mid_d0001/spf/simulator to attr powerState") == 20
    # 19 Unsubscriptions
    assert all_logs.count("Unsubscribed from mid_d0001/spf/simulator for attr powerState") == 19

    # Check comms established and not established updated
    callback_mock.assert_has_calls(
        (call(CommunicationStatus.ESTABLISHED), call(CommunicationStatus.NOT_ESTABLISHED)),
        any_order=True,
    )
    # Check we finish up with established
    assert callback_mock.call_args_list[-1] == call(CommunicationStatus.ESTABLISHED)


def test_connection_error(caplog):
    """Test that connection is retried"""
    caplog.set_level(logging.DEBUG)
    event_queue = Queue()
    callback_mock = MagicMock()
    tdm = TangoDeviceMonitor("fake_device", ["powerState"], event_queue, LOGGER, callback_mock)
    tdm.monitor()
    with pytest.raises(Empty):
        event_queue.get(timeout=4)
    all_logs = [record.message for record in caplog.records]
    for i in range(1, 4):
        assert f"Tango error on fake_device for attr powerState, try number {i}" in all_logs
