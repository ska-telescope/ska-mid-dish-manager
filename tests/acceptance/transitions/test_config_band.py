"""Test ConfigureBand2."""

import pytest
from ska_mid_dish_dcp_lib.device.b5dc_device_mappings import B5dcFrequency

from ska_mid_dish_manager.models.dish_enums import Band, DishMode
from tests.utils import remove_subscriptions, setup_subscriptions


@pytest.mark.acceptance
def test_configure_band_a(monitor_tango_servers, event_store_class, dish_manager_proxy):
    """Test ConfigureBand2."""
    main_event_store = event_store_class()
    result_event_store = event_store_class()
    status_event_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": main_event_store,
        "configuredBand": main_event_store,
        "Status": status_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # make sure configuredBand is not B2
    if dish_manager_proxy.configuredBand != Band.B1:
        [[_], [unique_id]] = dish_manager_proxy.ConfigureBand1(True)
        result_event_store.wait_for_command_id(unique_id, timeout=30)
        assert dish_manager_proxy.configuredBand == Band.B1
        assert dish_manager_proxy.dishMode == DishMode.OPERATE

    main_event_store.clear_queue()
    status_event_store.clear_queue()

    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand2(True)
    result_event_store.wait_for_command_result(
        unique_id, '[0, "SetOperateMode completed."]', timeout=30
    )
    main_event_store.wait_for_value(Band.B2, timeout=30)
    main_event_store.wait_for_value(DishMode.OPERATE, timeout=30)
    assert dish_manager_proxy.configuredBand == Band.B2
    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    expected_progress_updates = [
        # ConfigureBand2
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand2",
        "Awaiting DS indexerposition change to B2",
        "Awaiting SPFRX configuredband change to B2",
        "Awaiting configuredband change to B2",
        "DS indexerposition changed to B2",
        "DS.SetIndexPosition completed",
        "SPFRX configuredband changed to B2",
        "SPFRX.ConfigureBand2 completed",
        "ConfigureBand2 complete. Triggering on success action.",
        # Then SetOperateMode
        "Fanned out commands: SPF.SetOperateMode, DS.SetPointMode",
        "Awaiting SPF operatingmode change to OPERATE",
        "Awaiting DS operatingmode change to POINT",
        "Awaiting dishmode change to OPERATE",
        "SPF operatingmode changed to OPERATE",
        "SPF.SetOperateMode completed",
        "DS operatingmode changed to POINT",
        "DS.SetPointMode completed",
        "SetOperateMode completed",
    ]

    events = status_event_store.get_queue_values()
    events_string = "".join([str(attr_value) for _, attr_value in events])
    for message in expected_progress_updates:
        assert message in events_string

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
@pytest.mark.parametrize(
    ("band_request", "expected_band", "message_str"),
    [
        ("ConfigureBand1", Band.B1, "B1"),
        ("ConfigureBand3", Band.B3, "B3"),
        ("ConfigureBand4", Band.B4, "B4"),
        ("ConfigureBand5a", Band.B5a, "B5a"),
        ("ConfigureBand5b", Band.B5b, "B5b"),
        # End up in B2 again
        ("ConfigureBand2", Band.B2, "B2"),
    ],
)
def test_configure_band_b(
    band_request: str,
    expected_band: Band,
    message_str: str,
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test ConfigureBand."""
    # Just skip the band we already are in
    if expected_band == dish_manager_proxy.configuredBand:
        pytest.skip(f"Already in band {expected_band}")

    main_event_store = event_store_class()
    result_event_store = event_store_class()
    status_event_store = event_store_class()

    attr_cb_mapping = {
        "configuredBand": main_event_store,
        "Status": status_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    res = dish_manager_proxy.command_inout(band_request, True)
    assert res
    assert len(res) == 2
    main_event_store.wait_for_value(expected_band, timeout=15)
    assert dish_manager_proxy.configuredBand == expected_band

    spfrx_config_band_cmd = f"SPFRX.{band_request}"
    if expected_band == Band.B5b:
        spfrx_config_band_cmd = "SPFRX.ConfigureBand1"

    expected_progress_updates = [
        f"Fanned out commands: DS.SetIndexPosition, {spfrx_config_band_cmd}",
        f"Awaiting configuredband change to {message_str}",
        f"{band_request} complete",
    ]
    events = status_event_store.wait_for_progress_update(expected_progress_updates[-1], timeout=6)
    events_string = "".join([str(event.attr_value.value) for event in events])

    # Check that all the expected progress messages appeared
    # in the event store.
    for message in expected_progress_updates:
        assert message in events_string

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_configure_band_2_from_stow(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test ConfigureBand2."""
    main_event_store = event_store_class()
    result_event_store = event_store_class()
    status_event_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": main_event_store,
        "configuredBand": main_event_store,
        "Status": status_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    # make sure configuredBand is not B2
    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand1(True)
    result_event_store.wait_for_command_result(
        unique_id, '[0, "SetOperateMode completed."]', timeout=30
    )
    assert dish_manager_proxy.configuredBand == Band.B1
    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    main_event_store.clear_queue()
    status_event_store.clear_queue()

    # Stow the dish
    current_el = dish_manager_proxy.achievedPointing[2]
    stow_position = 90.2
    estimate_stow_duration = stow_position - current_el  # elevation speed is 1 degree per second
    dish_manager_proxy.SetStowMode()
    main_event_store.wait_for_value(DishMode.STOW, timeout=estimate_stow_duration + 10)

    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand2(True)
    result_event_store.wait_for_command_result(
        unique_id, '[0, "ConfigureBand2 completed."]', timeout=30
    )
    main_event_store.wait_for_value(Band.B2, timeout=30)

    expected_progress_updates = [
        # ConfigureBand2
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand2",
        "Awaiting DS indexerposition change to B2",
        "Awaiting SPFRX configuredband change to B2",
        "Awaiting configuredband change to B2",
        "DS indexerposition changed to B2",
        "DS.SetIndexPosition completed",
        "SPFRX configuredband changed to B2",
        "SPFRX.ConfigureBand2 completed",
    ]

    events = status_event_store.get_queue_values(timeout=0)

    events_string = "".join([str(attr_value) for _, attr_value in events])
    for message in expected_progress_updates:
        assert message in events_string

    assert dish_manager_proxy.configuredBand == Band.B2
    assert dish_manager_proxy.dishMode == DishMode.STOW

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance
def test_configure_band_json(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
):
    """Test ConfigureBand with JSON string."""
    main_event_store = event_store_class()
    result_event_store = event_store_class()
    status_event_store = event_store_class()

    attr_cb_mapping = {
        "dishMode": main_event_store,
        "configuredBand": main_event_store,
        "Status": status_event_store,
        "longRunningCommandResult": result_event_store,
    }
    subscriptions = setup_subscriptions(dish_manager_proxy, attr_cb_mapping)

    json_payload_1 = """
    {
        "dish": {
            "receiver_band": "1",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """
    # make sure configuredBand is not B2
    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand(json_payload_1)
    result_event_store.wait_for_command_result(
        unique_id, '[0, "SetOperateMode completed."]', timeout=30
    )
    assert dish_manager_proxy.configuredBand == Band.B1
    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    main_event_store.clear_queue()
    status_event_store.clear_queue()

    json_payload_2 = """
    {
        "dish": {
            "receiver_band": "2",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """
    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand(json_payload_2)
    result_event_store.wait_for_command_result(
        unique_id, '[0, "SetOperateMode completed."]', timeout=30
    )
    assert dish_manager_proxy.configuredBand == Band.B2
    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    expected_progress_updates = [
        # ConfigureBand
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand",
        "Awaiting DS indexerposition change to B2",
        "Awaiting SPFRX configuredband change to B2",
        "Awaiting configuredband change to B2",
        "DS indexerposition changed to B2",
        "DS.SetIndexPosition completed",
        "SPFRX configuredband changed to B2",
        "SPFRX.ConfigureBand completed",
    ]

    events = status_event_store.get_queue_values(timeout=0)

    events_string = "".join([str(attr_value) for _, attr_value in events])
    for message in expected_progress_updates:
        assert message in events_string

    # Do it again to check result
    result_event_store.clear_queue()
    status_event_store.clear_queue()
    # Check that dish manager allows configure band when already in requested band
    # but does not set the indexer position again.
    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand(json_payload_2)
    result_event_store.wait_for_command_result(
        unique_id, '[0, "SetOperateMode completed"]', timeout=30
    )
    assert dish_manager_proxy.configuredBand == Band.B2
    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    expected_progress_updates = [
        "Fanned out commands: SPFRX.ConfigureBand",
        "Awaiting SPFRX configuredband change to B2",
        "Awaiting configuredband change to B2",
        "SPFRX configuredband changed to B2",
        "SPFRX.ConfigureBand completed",
    ]

    events = status_event_store.get_queue_values(timeout=0)

    events_string = "".join([str(attr_value) for _, attr_value in events])
    for message in expected_progress_updates:
        assert message in events_string

    remove_subscriptions(subscriptions)


@pytest.mark.acceptance_incl_b5dc
def test_configure_band_json_with_b5dc_fanout(
    monitor_tango_servers,
    event_store_class,
    dish_manager_proxy,
    b5dc_device_proxy,
):
    """Test ConfigureBand with receiver band 5b and sub band configuration."""
    main_event_store = event_store_class()
    result_event_store = event_store_class()
    status_event_store = event_store_class()

    dm_attr_cb_mapping = {
        "dishMode": main_event_store,
        "configuredBand": main_event_store,
        "Status": status_event_store,
        "lrcFinished": result_event_store,
    }

    # Setup Dish Manager subscriptions
    subscriptions = setup_subscriptions(dish_manager_proxy, dm_attr_cb_mapping)

    # Setup B5DC proxy subscription to subband attr
    b5dc_subband_evt_store = event_store_class()

    b5dc_subband_sub = setup_subscriptions(
        b5dc_device_proxy, {"rfcmFrequency": b5dc_subband_evt_store}
    )

    # Ensure configuredBand is not B5b
    json_payload_1 = """
    {
        "dish": {
            "receiver_band": "2",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """
    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand(json_payload_1)
    result_event_store.wait_for_finished_command_result(
        unique_id, "[0, 'SetOperateMode completed.']", timeout=60
    )
    assert dish_manager_proxy.configuredBand == Band.B2
    assert dish_manager_proxy.dishMode == DishMode.OPERATE

    # Ensure B5dc proxy sub band is not 11.1GHz
    current_sub_band = b5dc_device_proxy.rfcmFrequency
    if current_sub_band == B5dcFrequency.F_11_1_GHZ.frequency_value_ghz():
        b5dc_device_proxy.SetFrequency(B5dcFrequency.F_13_2_GHZ)

        # Increased timeout period to account for the polling
        # loop refreshing the b5dc attribute values
        b5dc_subband_evt_store.wait_for_value(B5dcFrequency.F_13_2_GHZ.frequency_value_ghz(), 30)

    main_event_store.clear_queue()
    b5dc_subband_evt_store.clear_queue()

    json_payload_with_sub_band = """
    {
        "dish": {
            "receiver_band": "5b",
            "sub_band": "1",
            "spfrx_processing_parameters": [
                {
                    "dishes": ["all"],
                    "sync_pps": true
                }
            ]
        }
    }
    """
    [[_], [unique_id]] = dish_manager_proxy.ConfigureBand(json_payload_with_sub_band)
    result_event_store.wait_for_finished_command_result(
        unique_id, "[0, 'SetOperateMode completed.']", timeout=60
    )
    assert dish_manager_proxy.configuredBand == Band.B5b
    assert dish_manager_proxy.dishMode == DishMode.OPERATE
    assert b5dc_subband_evt_store.wait_for_value(
        B5dcFrequency.F_11_1_GHZ.frequency_value_ghz(), 30
    )

    expected_status_updates = [
        "Fanned out commands: DS.SetIndexPosition, SPFRX.ConfigureBand, B5DC.SetFrequency",
        "Awaiting DS indexerposition change to B5b",
        "Awaiting SPFRX configuredband change to B1",
        "Awaiting B5DC rfcmfrequency change to 11.1",
        "Awaiting configuredband change to B5b",
        "DS indexerposition changed to B5b",
        "SPFRX configuredband changed to B1",
        "B5DC rfcmfrequency changed to 11.1",
    ]

    events = status_event_store.get_queue_values(timeout=0)

    events_string = "".join([str(attr_value) for _, attr_value in events])
    for message in expected_status_updates:
        assert message in events_string

    remove_subscriptions(b5dc_subband_sub)
    remove_subscriptions(subscriptions)
