"""
Verify that dish lmc exposes the static pointing model parameters
"""

import logging

import pytest
from pytest_bdd import given, scenario, then
from pytest_bdd.parsers import parse
from utils import retrieve_attr_value

LOGGER = logging.getLogger(__name__)


@pytest.mark.lmc
@scenario("XTP-28119.feature", "LMC reports static pointing parameters")
def test_dish_lmc_exposes_static_pointing_model_parameters():
    # pylint: disable=missing-function-docstring
    pass


@given(parse("dish_manager has an attribute {pointing_model_parameter}"))
def dish_manager_has_attribute(pointing_model_parameter, dish_manager):
    # pylint: disable=missing-function-docstring
    list_of_parameters = dish_manager.get_attribute_list()
    assert pointing_model_parameter in list_of_parameters


@then(parse("{pointing_model_parameter} is a list containing 20 float parameters"))
def check_spfrx_operating_mode(pointing_model_parameter, dish_manager):
    # pylint: disable=missing-function-docstring
    param = retrieve_attr_value(dish_manager, pointing_model_parameter)

    assert len(param) == 20
    assert param.dtype.name == "float32"  # type: ignore
