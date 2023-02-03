"""A DishManager test device to connect to the test SPFRX etc."""
# pylint: disable=invalid-name, abstract-method
import os

from tango import Database, DbDevInfo

from ska_mid_dish_manager.devices.DishManagerDS import DishManager


class DishManagerTestDevice(DishManager):
    """Test DishManager device"""


def main():
    """Script entrypoint"""
    DishManagerTestDevice.run_server()


# pylint: disable=protected-access
if __name__ == "__main__":
    db = Database()
    test_device = DbDevInfo()
    if "DEVICE_NAME" in os.environ:
        # DEVICE_NAME should be in the format domain/family/member
        test_device.name = os.environ["DEVICE_NAME"]
    else:
        # fall back to default name
        test_device.name = "test/dishmanager/1"
    test_device._class = "DishManagerTestDevice"
    test_device.server = "DishManagerTestDevice/test"
    db.add_server(test_device.server, test_device, with_dserver=True)
    main()
