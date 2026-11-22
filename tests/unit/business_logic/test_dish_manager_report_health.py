"""Test how DishManagerComponentManager adapts its health to report_health()."""

from unittest.mock import MagicMock

import pytest
from ska_control_model import HealthState

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager


def _report(health_state, health_info):
    """Call report_health without building a whole component manager."""
    callback = MagicMock()
    component_manager = MagicMock(_health_report_callback=callback)
    DishManagerComponentManager.report_health(component_manager, health_state, health_info)
    return callback


@pytest.mark.unit
@pytest.mark.parametrize(
    ("health_state", "health_info", "expected"),
    [
        (HealthState.OK, [], (HealthState.OK, [])),
        (HealthState.OK, ["reason"], (HealthState.DEGRADED, ["reason"])),
        (HealthState.DEGRADED, [], (HealthState.DEGRADED, ["reason unknown"])),
        (HealthState.FAILED, ["reason"], (HealthState.FAILED, ["reason"])),
        (HealthState.UNKNOWN, [], (HealthState.FAILED, ["reason unknown"])),
    ],
)
def test_report_health_satisfies_base_class_rules(health_state, health_info, expected):
    """OK has no info, other states always have info, and UNKNOWN is never reported."""
    _report(health_state, health_info).assert_called_once_with(*expected)


@pytest.mark.unit
def test_report_health_without_callback_does_nothing():
    """No callback means nothing to report to, and no error."""
    component_manager = MagicMock(_health_report_callback=None)
    DishManagerComponentManager.report_health(component_manager, HealthState.OK, [])
