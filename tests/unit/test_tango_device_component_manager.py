import logging

import pytest
from ska_tango_base.control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers import TangoDeviceComponentManager

LOGGER = logging.getLogger(__name__)


@pytest.mark.timeout(10)
def test_non_existing_component(caplog):
    caplog.set_level(logging.INFO)
    tc_manager = TangoDeviceComponentManager(
        "fake/fqdn/1", max_workers=1, logger=LOGGER
    )
    while "Retry count [3]" not in caplog.text:
        pass
    assert tc_manager.communication_state == CommunicationStatus.DISABLED
    tc_manager.stop_communicating()
    assert tc_manager.communication_state == CommunicationStatus.NOT_ESTABLISHED

