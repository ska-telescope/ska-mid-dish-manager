import pytest
from unittest import mock
import tempfile

from ska_mid_dish_manager.dish_manager import DishManager
from ska_tango_base.commands import ResultCode

from tango_simlib.utilities.validate_device import validate_device_from_url

import tango
from tango.test_context import DeviceTestContext


@pytest.fixture(scope="module")
def dish_manager(request):
    """Creates and returns a TANGO DeviceTestContext object.

    :param request: _pytest.fixtures.SubRequest
        A request object gives access to the requesting test context.
    """
    _, tango_db_path = tempfile.mkstemp(prefix="tango")
    tango_context = DeviceTestContext(
        DishManager, db=tango_db_path, process=False, properties={}
    )
    tango_context.start()
    yield tango_context.device
    tango_context.stop()


def test_On(dish_manager):
    response = dish_manager.On()
    assert response == (ResultCode.OK, "On command completed OK")


def test_Off(dish_manager):
    response = dish_manager.Off()
    assert response == (ResultCode.OK, "On command completed OK")


SPEC_URLS = {
    "dish_master": (
        "https://gitlab.com/ska-telescope/telescope-model/-/raw/"
        "master/spec/tango/dsh/DishMaster.yaml"
    ),
    "ska_tango_guide_ska_wide": (
        "https://gitlab.com/ska-telescope/telescope-model/-/raw/"
        "master/spec/tango/ska_wide/Guidelines.yaml"
    ),
}


def test_dish_manager_conforms_to_ska_wide_spec(dish_manager):
    with mock.patch("tango.DeviceProxy") as dp:
        dp.return_value = dish_manager
        result = validate_device_from_url(
            dp.name(),
            SPEC_URLS["ska_tango_guide_ska_wide"],
            False,
        )
        assert not result


def test_dish_manager_conforms_to_dish_master_spec(dish_manager):
    with mock.patch("tango.DeviceProxy") as dp:
        dp.return_value = dish_manager
        result = validate_device_from_url(
            dp.name(),
            SPEC_URLS["dish_master"],
            False,
        )
        assert not result
