import logging
from collections.abc import Generator
from unittest.mock import Mock, patch

import pytest
from ska_control_model import CommunicationStatus, ResultCode, TaskStatus

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from tests.utils import ComponentStateStore

LOGGER = logging.getLogger(__name__)


@pytest.fixture()
def mock_command_tracker() -> Mock:
    """"""
    return Mock()


@pytest.fixture()
def callbacks() -> dict:
    """Return a dictionary of callbacks."""
    return {
        "build_state_cb": Mock(),
        "quality_state_cb": Mock(),
        "comm_state_cb": Mock(),
        "comp_state_cb": ComponentStateStore(),
        "task_cb": Mock(),
    }


@pytest.fixture()
def component_manager(mock_command_tracker: Mock, callbacks: dict) -> Generator:
    """
    Fixture that returns the component manager under test.

    :param callbacks: a dictionary of mocks passed as callbacks

    :return: the component manager under test
    """

    def _simulate_lrc_callbacks(*args, **kwargs):
        task_callback = args[-1]
        task_callback(status=TaskStatus.IN_PROGRESS)
        task_callback(status=TaskStatus.COMPLETED, result=(ResultCode.OK, str(None)))
        return TaskStatus.QUEUED, "message"

    with patch.multiple(
        "ska_mid_dish_manager.component_managers.tango_device_cm.TangoDeviceComponentManager",
        run_device_command=Mock(side_effect=_simulate_lrc_callbacks),
        update_state_from_monitored_attributes=Mock(),
        write_attribute_value=Mock(),
        execute_command=Mock(),
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
        # all the command handlers are decorated with check_communicating
        # transition communication to the component as ESTABLISHED
        dish_manager_cm._update_communication_state(CommunicationStatus.ESTABLISHED)
        yield dish_manager_cm
