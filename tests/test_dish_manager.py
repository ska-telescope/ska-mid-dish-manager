import pytest
import tempfile

from ska_mid_dish_manager import DishManager
from ska_tango_base.commands import ResultCode
from tango.test_context import DeviceTestContext


@pytest.fixture(scope="function")
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
    yield tango_context
    tango_context.stop()


def test_On(dish_manager):
    response = dish_manager.On()
    assert response == (ResultCode.OK, "On command completed OK")


def test_Off(dish_manager):
    response = dish_manager.Off()
    assert response == (ResultCode.OK, "On command completed OK")
