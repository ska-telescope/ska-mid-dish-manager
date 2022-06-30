import logging

import pytest
from ska_tango_base.control_model import CommunicationStatus

from ska_mid_dish_manager.component_managers import TangoDeviceComponentManager

LOGGER = logging.getLogger(__name__)


@pytest.mark.timeout(10)
def test_non_existant_component(caplog):
    caplog.set_level(logging.INFO)
    tcmanager = TangoDeviceComponentManager(
        "fake/fqdn/1", max_workers=1, logger=LOGGER
    )
    while "Retry count [3]" not in caplog.text:
        pass
    assert tcmanager.communication_state == CommunicationStatus.DISABLED
    tcmanager.stop_communicating()
    assert tcmanager.communication_state == CommunicationStatus.NOT_ESTABLISHED
