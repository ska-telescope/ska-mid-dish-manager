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
        "conn_state_cb": MagicMock(),
        "quality_state_cb": MagicMock(),
        "comm_state_cb": MagicMock(),
        "comp_state_cb": ComponentStateStore(),
        "task_cb": MagicMock(),
    }


@pytest.fixture()
def component_manager(mock_command_tracker: MagicMock, callbacks: dict) -> Generator:
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

    def _simulate_execute_command(*args):
        return [[ResultCode.OK], [f"{args[0]} completed"]]

    with patch.multiple(
        "ska_mid_dish_manager.component_managers.tango_device_cm.TangoDeviceComponentManager",
        read_attribute_value=MagicMock(),
        write_attribute_value=MagicMock(),
        update_state_from_monitored_attributes=MagicMock(),
        execute_command=MagicMock(side_effect=_simulate_execute_command),
        run_device_command=MagicMock(side_effect=_simulate_lrc_callbacks),
    ):
        dish_manager_cm = DishManagerComponentManager(
            LOGGER,
            mock_command_tracker,
            callbacks["conn_state_cb"],
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
