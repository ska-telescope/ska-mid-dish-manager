"""Test ignoring subservient devices."""

# pylint: disable=invalid-name,redefined-outer-name,unused-argument
import pytest
import tango

from tests.utils import set_ignored_devices


@pytest.fixture
def toggle_ignore_spfrx(dish_manager_proxy):
    """Ignore SPFRx"""
    set_ignored_devices(dish_manager_proxy=dish_manager_proxy, ignore_spf=False, ignore_spfrx=True)
    yield
    set_ignored_devices(
        dish_manager_proxy=dish_manager_proxy, ignore_spf=False, ignore_spfrx=False
    )


@pytest.fixture
def toggle_ignore_spf(dish_manager_proxy):
    """Ignore SPF"""
    set_ignored_devices(dish_manager_proxy=dish_manager_proxy, ignore_spf=True, ignore_spfrx=False)
    yield
    set_ignored_devices(
        dish_manager_proxy=dish_manager_proxy, ignore_spf=False, ignore_spfrx=False
    )


@pytest.fixture
def toggle_ignore_spf_and_spfrx(dish_manager_proxy):
    """Ignore SPF and SPFRx"""
    set_ignored_devices(dish_manager_proxy=dish_manager_proxy, ignore_spf=True, ignore_spfrx=True)
    yield
    set_ignored_devices(
        dish_manager_proxy=dish_manager_proxy, ignore_spf=False, ignore_spfrx=False
    )


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_ignoring_spf(toggle_ignore_spf, event_store_class, dish_manager_proxy):
    """Test ignoring SPF device."""

    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longrunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyFPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "SetStandbyFPMode called on DS",
        "SPF device is disabled. SetOperateMode call ignored",
        "Awaiting dishMode change to STANDBY_FP",
        "SetStandbyFPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_ignoring_spfrx(toggle_ignore_spfrx, event_store_class, dish_manager_proxy):
    """Test ignoring SPFRX device."""

    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longrunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    [[_], [unique_id]] = dish_manager_proxy.SetStowMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyLPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "SetStandbyLPMode called on DS",
        "SetStandbyLPMode called on SPF",
        "SPFRX device is disabled. SetStandbyMode call ignored",
        "Awaiting dishMode change to STANDBY_LP",
        "SetStandbyLPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_ignoring_all(toggle_ignore_spf_and_spfrx, event_store_class, dish_manager_proxy):
    """Test ignoring both SPF and SPFRx devices."""
    result_event_store = event_store_class()
    progress_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "longrunningCommandResult",
        tango.EventType.CHANGE_EVENT,
        result_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    [[_], [unique_id]] = dish_manager_proxy.SetStowMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    [[_], [unique_id]] = dish_manager_proxy.SetStandbyLPMode()
    result_event_store.wait_for_command_id(unique_id, timeout=8)

    expected_progress_updates = [
        "SetStandbyLPMode called on DS",
        "SPF device is disabled. SetStandbyLPMode call ignored",
        "SPFRX device is disabled. SetStandbyMode call ignored",
        "Awaiting dishMode change to STANDBY_LP",
        "SetStandbyLPMode completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store
    for message in expected_progress_updates:
        assert message in events_string
