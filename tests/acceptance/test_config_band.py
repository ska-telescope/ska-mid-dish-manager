"""Test ConfigureBand2"""
import pytest
import tango

from ska_mid_dish_manager.devices.test_devices.utils import (
    set_configuredBand_b1,
    set_configuredBand_b2,
    set_dish_manager_to_standby_lp,
)
from ska_mid_dish_manager.models.dish_enums import Band, DishMode


@pytest.mark.acceptance
@pytest.mark.SKA_mid
@pytest.mark.forked
def test_configure_band_2(event_store_class, dish_manager_proxy):
    """Test ConfigureBand2"""
    set_dish_manager_to_standby_lp(event_store_class, dish_manager_proxy)
    assert dish_manager_proxy.dishMode == DishMode.STANDBY_LP

    # make sure configureBand is not B2
    set_configuredBand_b1()

    main_event_store = event_store_class()
    progress_event_store = event_store_class()
    band_event_store = event_store_class()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        main_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "longRunningCommandProgress",
        tango.EventType.CHANGE_EVENT,
        progress_event_store,
    )

    dish_manager_proxy.subscribe_event(
        "configuredBand",
        tango.EventType.CHANGE_EVENT,
        band_event_store,
    )
    # Seting the dish mode to standby full power
    dish_manager_proxy.SetStandbyFPMode()
    assert main_event_store.wait_for_value(DishMode.STANDBY_FP, timeout=5)
    set_configuredBand_b2()
    band_event_store.wait_for_value(Band.B2, timeout=5)

    expected_progress_updates = [
        "SetIndexPosition called on DS",
        (
            "Awaiting DS indexerposition to change to "
            "[<IndexerPosition.B2: 2>]"
        ),
        "ConfigureBand2 called on SPFRX",
        ("Awaiting SPFRX configuredband to change to [<Band.B2: 2>]"),
        "Awaiting dishmode change to 3",
        ("SPF operatingmode changed to, [<SPFOperatingMode.OPERATE: 3>]"),
        ("SPFRX configuredband changed to, [<Band.B2: 2>]"),
        "ConfigureBand2 completed",
    ]

    events = progress_event_store.wait_for_progress_update(
        expected_progress_updates[-1], timeout=6
    )

    events_string = "".join([str(event) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
    for message in expected_progress_updates:
        assert message in events_string
