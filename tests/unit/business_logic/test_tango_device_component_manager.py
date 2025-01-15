# pylint: disable=protected-access
"""Unit tests checking generic component manager behaviour."""

import logging
import time
from unittest import mock

import pytest
import tango
from ska_control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers.tango_device_cm import TangoDeviceComponentManager

LOGGER = logging.getLogger(__name__)


# pylint: disable=invalid-name, missing-function-docstring
@pytest.mark.timeout(5)
@pytest.mark.forked
@pytest.mark.unit
def test_component_manager_continues_reconnecting_when_device_is_unreachable(caplog):
    caplog.set_level(logging.DEBUG)
    tc_manager = TangoDeviceComponentManager("fake/fqdn/1", LOGGER, ("fake_attr",))
    tc_manager.start_communicating()
    retry_log = "An error occured creating a device proxy to fake/fqdn/1, retrying in"
    while retry_log not in caplog.text:
        time.sleep(0.5)

    assert tc_manager.communication_state == CommunicationStatus.NOT_ESTABLISHED
    # clean up afterwards
    tc_manager.stop_communicating()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango")
def test_happy_path(caplog):
    """Tango device is reachable and communicates with component manager

    Tango layer is mocked and checks are made on the mock for expected
    calls made when communication is established and component is
    updated accordingly
    """
    caplog.set_level(logging.DEBUG)

    # set up mocks
    comm_state_cb = mock.MagicMock()
    comp_state_cb = mock.MagicMock()

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        ("some_attr",),
        communication_state_callback=comm_state_cb,
        component_state_callback=comp_state_cb,
    )

    tc_manager.start_communicating()
    assert comm_state_cb.called
    # clean up afterwards
    tc_manager.stop_communicating()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
def test_unhappy_path(patched_dp, caplog):
    """Tango device is unreachable and can't communicate with component manager

    Similar to `test_component_manager_continues_reconnecting_...` except
    Tango layer is mocked here. Checks are made on the mock for expected
    calls and logs when communication is attempted by component manager
    on mocked device
    """
    caplog.set_level(logging.DEBUG)

    # configure mock
    patched_dp.side_effect = tango.DevFailed("FAIL")

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        ("some_attr", "some_other_attr"),
    )

    tc_manager.start_communicating()

    default_retry_times = [1, 2, 3, 4, 6]
    # wait a bit
    time.sleep(sum(default_retry_times))

    logs = [record.message for record in caplog.records]
    for count, retry_time in enumerate(default_retry_times, start=1):
        assert (
            f"Try number {count}: An error occurred creating a device "
            f"proxy to a/b/c, retrying in {retry_time}s" in logs
        )
    # clean up afterwards
    tc_manager.stop_communicating()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
def test_device_goes_away(caplog):
    """
    Start up the component_manager.
    Signal a lost connection via an event
    Check for updated communication state
    """
    caplog.set_level(logging.DEBUG)

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        ("some_attr", "some_other_attr"),
    )

    tc_manager.start_communicating()
    # wait a bit for the state to change
    time.sleep(0.5)
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED

    # Set up an error mock event
    mock_error = mock.MagicMock(name="mock_error")
    mock_error.err = True
    mock_error.name = "some_attr"
    # Trigger a failure event
    tc_manager._events_queue.put(mock_error)
    # wait a bit for the state to change
    time.sleep(0.5)
    assert tc_manager.communication_state == CommunicationStatus.NOT_ESTABLISHED

    # Set up a valid mock event
    mock_attr_value = mock.MagicMock(name="mock_attr_value")
    mock_attr_value.name = "some_attr"
    mock_attr_value.quality = tango.AttrQuality.ATTR_VALID
    mock_data = mock.MagicMock(name="mock_data")
    mock_data.attr_value = mock_attr_value
    mock_data.err = False
    # trigger a valid event
    tc_manager._events_queue.put(mock_data)

    # wait a bit for the state to change
    time.sleep(0.5)
    assert tc_manager.communication_state == CommunicationStatus.ESTABLISHED

    # TODO clean up afterwards (THIS SHOULD BE A FINALIZER ELSE THINGS HANG)
    tc_manager.stop_communicating()
