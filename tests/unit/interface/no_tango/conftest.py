import logging
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from ska_control_model import CommunicationStatus, ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from tests.utils import ComponentStateStore

LOGGER = logging.getLogger(__name__)


@pytest.fixture()
def mock_command_tracker() -> MagicMock:
    """"""
    return MagicMock()


@pytest.fixture()
def callbacks() -> dict:
    """Return a dictionary of callbacks."""
    return {
        "build_state_cb": MagicMock(),
        "quality_state_cb": MagicMock(),
        "comm_state_cb": MagicMock(),
        "comp_state_cb": ComponentStateStore(),
        "task_cb": MagicMock(),
    }


@pytest.fixture()
def component_manager(mock_command_tracker: MagicMock, callbacks: dict) -> Generator:
    """Fixture that returns the component manager under test.

    :param callbacks: a dictionary of mocks passed as callbacks

    :return: the component manager under test
    """

    def _simulate_lrc_callbacks(*args, **kwargs):
        task_callback = args[-1]
        task_callback(status=TaskStatus.IN_PROGRESS)
        task_callback(status=TaskStatus.COMPLETED, result=(ResultCode.OK, str(None)))
        return TaskStatus.QUEUED, "message"

    with (
        patch.multiple(
            "ska_mid_dish_manager.component_managers.tango_device_cm.TangoDeviceComponentManager",
            read_attribute_value=MagicMock(),
            write_attribute_value=MagicMock(),
            update_state_from_monitored_attributes=MagicMock(),
            execute_command=MagicMock(),
            run_device_command=MagicMock(side_effect=_simulate_lrc_callbacks),
        ),
        patch("ska_mid_dish_manager.component_managers.tango_device_cm.DeviceProxyManager"),
        patch("ska_mid_dish_manager.component_managers.spfrx_cm.MonitorPing"),
        patch.multiple(
            "ska_mid_dish_manager.utils.schedulers.WatchdogTimer",
            disable=MagicMock(),
        ),
    ):
        dish_manager_cm = DishManagerComponentManager(
            LOGGER,
            mock_command_tracker,
            callbacks["build_state_cb"],
            callbacks["quality_state_cb"],
            "device-1",
            "sub-device-1",
            "sub-device-2",
            "sub-device-3",
            communication_state_callback=callbacks["comm_state_cb"],
            component_state_callback=callbacks["comp_state_cb"],
        )
        dish_manager_cm.start_communicating()
        # since the devices are mocks, no change events
        # will be emitted to transition the state to ESTABLISHED
        for sub_component_manager in dish_manager_cm.sub_component_managers.values():
            sub_component_manager._update_communication_state(CommunicationStatus.ESTABLISHED)

        yield dish_manager_cm
