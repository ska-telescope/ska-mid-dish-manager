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
    retry_log = "failed to connect to tango device fake/fqdn/1, retrying in"
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
            f"Try number {count}: "
            f"failed to connect to tango device a/b/c, retrying in {retry_time}s" in logs
        )
    # clean up afterwards
    tc_manager.stop_communicating()


@pytest.mark.unit
@mock.patch("ska_mid_dish_manager.component_managers.device_proxy_factory.tango.DeviceProxy")
def test_device_goes_away(caplog):
    """
    Start up the component_manager.
    Signal a lost connection via an event
    Check for reconnect
    """
    caplog.set_level(logging.DEBUG)

    tc_manager = TangoDeviceComponentManager(
        "a/b/c",
        LOGGER,
        ("some_,attr",),
    )

    tc_manager.start_communicating()

    # TODO update test after error event callback in tango device cm is updated
    # Set up mock error event
    mock_error = mock.MagicMock()
    mock_error.err = True

    # Trigger the failure
    tc_manager._events_queue.put(mock_error)
    # clean up afterwards
    tc_manager.stop_communicating()
