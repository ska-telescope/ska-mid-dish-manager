import logging

from ska_mid_dish_manager.component_managers import TangoDeviceComponentManager


def test_tango_device_component_manager():
    tcmanager = TangoDeviceComponentManager(
        "fqdn", max_workers=1, logger=logging.getLogger()
    )
    assert tcmanager.communication_state
