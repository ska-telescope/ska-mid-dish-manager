import logging
import sys

import pytest
import tango
from utils import EventStore, tango_dev_proxy

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    IndexerPosition,
    SPFOperatingMode,
)

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
LOGGER = logging.getLogger(__name__)


@pytest.fixture(name="dish_manager", scope="module")
def dish_manager_device_proxy():
    return tango_dev_proxy("ska001/elt/master", LOGGER)


@pytest.fixture(name="dish_structure", scope="module")
def dish_structure_device_proxy():
    return tango_dev_proxy("ska001/ds/manager", LOGGER)


@pytest.fixture(name="spf", scope="module")
def spf_device_proxy():
    return tango_dev_proxy("ska001/spf/simulator", LOGGER)


@pytest.fixture(name="spfrx", scope="module")
def spfrx_device_proxy():
    return tango_dev_proxy("ska001/spfrx/simulator", LOGGER)


@pytest.fixture
def modes_command_map():
    return {
        "STANDBY_LP": "SetStandbyLPMode",
        "STANDBY_FP": "SetStandbyFPMode",
        "OPERATE": "SetOperateMode",
        "STOW": "SetStowMode",
    }


@pytest.fixture
def event_store():
    """Fixture for storing events"""
    return EventStore()


@pytest.fixture(scope="module")
def dish_manager_event_store():
    """Fixture for storing dish_manager events"""
    return EventStore()


@pytest.fixture(scope="module")
def dish_structure_event_store():
    """Fixture for storing dish structure events"""
    return EventStore()


@pytest.fixture(scope="module")
def spfrx_event_store():
    """Fixture for storing spfrx events"""
    return EventStore()


@pytest.fixture(scope="module")
def spf_event_store():
    """Fixture for storing spf events"""
    return EventStore()


@pytest.fixture
def dish_freq_band_configuration(
    dish_manager_event_store,
    dish_manager,
):
    """
    A helper that manages dish lmc frequency band configuration
    """

    class _BandSelector:
        def go_to_band(self, band_number):
            if dish_manager.configuredBand.name == f"B{band_number}":
                LOGGER.info("Dish master is already at requested band")
                return

            allowed_modes = ["STANDBY_FP", "STOW", "OPERATE"]
            current_dish_mode = dish_manager.dishMode.name
            if not (current_dish_mode in allowed_modes):
                LOGGER.info(
                    f"Dish master cannot request ConfigureBand while in {current_dish_mode}"
                )
                return

            dish_manager.subscribe_event(
                "configuredBand",
                tango.EventType.CHANGE_EVENT,
                dish_manager_event_store,
            )
            dish_manager_event_store.clear_queue()

            [[_], [_]] = dish_manager.command_inout(f"ConfigureBand{band_number}", False)

            dish_manager_event_store.wait_for_value(Band(int(band_number)), timeout=60)
            assert dish_manager.configuredBand.name == f"B{band_number}"
            LOGGER.info(f"{dish_manager} successfully transitioned to Band {band_number}")

    return _BandSelector()


@pytest.fixture
def modes_helper(
    dish_manager_event_store,
    dish_manager,
    modes_command_map,
    dish_freq_band_configuration,
):
    """
    A helper that manages device modes using events
    """

    class _ModesHelper:
        def ensure_dish_manager_mode(self, desired_mode_name):
            """Move dish master to desired_mode_name.
            Via STANDBY_FP, to ensure any mode can move to any mode.
            """
            if dish_manager.dishMode.name == desired_mode_name:
                LOGGER.info("Dish master is already at requested mode")
                return

            # handle case where dish mode is unknown
            if dish_manager.dishMode.name == "UNKNOWN":
                self.dish_manager_go_to_mode("STOW")
                if desired_mode_name == "STOW":
                    return

            if desired_mode_name == "STOW":
                self.dish_manager_go_to_mode("STOW")
                return
            elif desired_mode_name == "STANDBY_FP":
                self.dish_manager_go_to_mode("STANDBY_FP")
                return
            else:
                # transition to desired mode through STANDBY_FP
                self.dish_manager_go_to_mode("STANDBY_FP")
                self.dish_manager_go_to_mode(desired_mode_name)

        def dish_manager_go_to_mode(self, desired_mode_name):
            """Move device to desired_mode_name"""
            if dish_manager.dishMode.name == desired_mode_name:
                LOGGER.info("Dish master is already at requested mode")
                return

            # make sure there is a configured
            # band if the requested mode is operate
            if desired_mode_name == "OPERATE" and dish_manager.configuredBand.name in [
                "NONE",
                "UNKNOWN",
            ]:
                dish_freq_band_configuration.go_to_band(2)

            dish_manager.subscribe_event(
                "dishMode",
                tango.EventType.CHANGE_EVENT,
                dish_manager_event_store,
            )
            dish_manager_event_store.clear_queue()

            # Move to mode_name
            command_name = modes_command_map[desired_mode_name]
            LOGGER.info(
                f"Moving {dish_manager} from "
                f"{dish_manager.dishMode.name} to {desired_mode_name}"
            )

            LOGGER.info(f"{dish_manager} executing {command_name} ")
            [[_], [_]] = dish_manager.command_inout(command_name)

            # wait for events
            dish_manager_event_store.wait_for_value(DishMode[desired_mode_name], timeout=8)
            assert dish_manager.dishMode.name == desired_mode_name
            LOGGER.info(f"{dish_manager} successfully transitioned to {desired_mode_name} mode")

    return _ModesHelper()


@pytest.fixture(autouse=True)
def setup_and_teardown(
    event_store,
    dish_manager_proxy,
    ds_device_proxy,
    spf_device_proxy,
    spfrx_device_proxy,
):
    """Reset the tango devices to a fresh state before each test"""

    # ds_device_proxy.ResetToDefault()
    spfrx_device_proxy.ResetToDefault()
    spf_device_proxy.ResetToDefault()

    ds_device_proxy.subscribe_event(
        "operatingMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    ds_device_proxy.subscribe_event(
        "indexerPosition",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    if ds_device_proxy.operatingMode != DSOperatingMode.STOW:
        ds_device_proxy.Stow()
        assert event_store.wait_for_value(DSOperatingMode.STOW, timeout=9)

    ds_device_proxy.SetStandbyLPMode()
    assert event_store.wait_for_value(DSOperatingMode.STANDBY_LP, timeout=9)

    if ds_device_proxy.indexerPosition != IndexerPosition.B1:
        ds_device_proxy.SetIndexPosition(IndexerPosition.B1)
        assert event_store.wait_for_value(IndexerPosition.B1, timeout=9)

    spf_device_proxy.subscribe_event(
        "operatingMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )
    assert event_store.wait_for_value(SPFOperatingMode.STANDBY_LP, timeout=7)
    event_store.clear_queue()

    dish_manager_proxy.SyncComponentStates()

    dish_manager_proxy.subscribe_event(
        "dishMode",
        tango.EventType.CHANGE_EVENT,
        event_store,
    )

    try:
        event_store.wait_for_value(DishMode.STANDBY_LP, timeout=7)
    except RuntimeError as err:
        component_states = dish_manager_proxy.GetComponentStates()
        raise RuntimeError(f"DishManager not in STANDBY_LP:\n {component_states}\n") from err

    yield
