import logging

import pytest
from ska_tango_base.control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers import TangoDeviceComponentManager

LOGGER = logging.getLogger(__name__)


@pytest.mark.timeout(10)
def test_tango_device_component_manager(caplog):
    caplog.set_level(logging.INFO)
    tcmanager = TangoDeviceComponentManager(
        "fake/fqdn/1", max_workers=1, logger=LOGGER
    )
    # Keep waiting for
    while "Retry count [3]" not in caplog.text:
        pass
    tcmanager.stop_communicating()
    assert tcmanager.communication_state == CommunicationStatus.DISABLED
    assert tcmanager._task_executor._abort_event.is_set()
    assert tcmanager._task_executor._executor._work_queue.empty
