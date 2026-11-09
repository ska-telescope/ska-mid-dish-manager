"""Tests for FannedOutWaitForState."""

import logging
import time
from unittest.mock import MagicMock

import pytest

from ska_mid_dish_manager.models.dish_enums import FannedOutCommandStatus
from ska_mid_dish_manager.models.fanned_out_command import FannedOutWaitForState

LOGGER = logging.getLogger(__name__)


def _wait(component_state: dict, timeout_s: float = 0, progress_callback=None):
    device_cm = MagicMock()
    device_cm._component_state = component_state
    return FannedOutWaitForState(
        logger=LOGGER,
        device="SPFRx",
        device_component_manager=device_cm,
        awaited_component_state={"operatingmode": "OPERATE"},
        timeout_s=timeout_s,
        progress_callback=progress_callback,
    )


@pytest.mark.unit
def test_completes_when_state_matches():
    component_state = {"operatingmode": "STANDBY"}
    progress_callback = MagicMock()
    wait = _wait(component_state, progress_callback=progress_callback)

    wait.execute()
    assert wait.status == FannedOutCommandStatus.IN_PROGRESS

    wait.report_progress()
    assert wait.status == FannedOutCommandStatus.IN_PROGRESS

    component_state["operatingmode"] = "OPERATE"
    wait.report_progress()
    assert wait.status == FannedOutCommandStatus.COMPLETED
    assert wait.successful

    messages = [str(c) for c in progress_callback.call_args_list]
    assert any("Awaiting SPFRx operatingmode change to OPERATE" in m for m in messages)
    assert any("SPFRx.WaitForState completed" in m for m in messages)


@pytest.mark.unit
def test_completes_immediately_if_already_satisfied():
    wait = _wait({"operatingmode": "OPERATE"})
    wait.execute()
    wait.report_progress()
    assert wait.status == FannedOutCommandStatus.COMPLETED


@pytest.mark.unit
def test_times_out():
    wait = _wait({"operatingmode": "STANDBY"}, timeout_s=0.01)
    wait.execute()
    time.sleep(0.02)
    wait.report_progress()
    assert wait.status == FannedOutCommandStatus.TIMED_OUT
    assert wait.failed


@pytest.mark.unit
def test_timeout_does_not_fail_when_continuing_on_timeout():
    device_cm = MagicMock()
    device_cm._component_state = {"operatingmode": "STANDBY"}
    wait = FannedOutWaitForState(
        logger=LOGGER,
        device="SPFRx",
        device_component_manager=device_cm,
        awaited_component_state={"operatingmode": "OPERATE"},
        timeout_s=0.01,
        continue_on_timeout=True,
    )
    wait.execute()
    time.sleep(0.02)
    wait.report_progress()
    assert wait.status == FannedOutCommandStatus.TIMED_OUT
    assert not wait.failed
    assert wait.successful
    assert wait.finished
