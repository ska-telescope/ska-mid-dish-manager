"""
Verify that dish lmc updates static pointing model parameters on a write
"""

import json
import logging

import pytest
from pytest_bdd import given, scenario, then, when
from pytest_bdd.parsers import parse
from utils import poll_for_attribute_value

LOGGER = logging.getLogger(__name__)


@pytest.mark.lmc
@scenario("XTP-28120.feature", "LMC accepts write to static pointing parameters")
def test_dish_lmc_accepts_write_to_static_pointing_model_parameters():
    # pylint: disable=missing-function-docstring
    pass


@given(parse("dish_manager has an attribute {pointing_model_parameter}"))
def dish_manager_has_attribute(pointing_model_parameter, dish_manager):
    # pylint: disable=missing-function-docstring
    list_of_parameters = dish_manager.get_attribute_list()
    assert pointing_model_parameter in list_of_parameters


@when(parse("I write {value} to {pointing_model_parameter}"))
def write_to_parameter(value, pointing_model_parameter, dish_manager):
    # pylint: disable=missing-function-docstring
    dish_manager.write_attribute(pointing_model_parameter, json.loads(value))


@then(parse("the dish_structure static pointing model parameters are updated"))
def parameters_are_updated():
    # pylint: disable=missing-function-docstring
    pass


@then(parse("{pointing_model_parameter} should report {new_value}"))
def check_reported_value(pointing_model_parameter, new_value, dish_manager):
    # pylint: disable=missing-function-docstring
    new_values = json.loads(new_value)

    assert poll_for_attribute_value(dish_manager, pointing_model_parameter, new_values)
