import logging

import pytest
import tango
from utils import EventStore, tango_dev_proxy

from ska_mid_dish_manager.models.dish_enums import Band, DishMode

LOGGER = logging.getLogger(__name__)


@pytest.fixture(name="dish_manager", scope="module")
def dish_manager_device_proxy():
    return tango_dev_proxy("ska001/elt/master", LOGGER)


@pytest.fixture(name="dish_structure", scope="module")
def dish_structure_device_proxy():
    return tango_dev_proxy("ska001/ds/managersimulator", LOGGER)


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


@pytest.fixture(scope="function")
def reset_ds_indexer_position(dish_structure, event_store):
    # do nothing if indexer is unknown
    if dish_structure.indexerPosition.name == "UNKNOWN":
        return

    if dish_structure.operatingMode.name not in ["STOW", "STANDBY", "POINT"]:
        dish_structure.subscribe_event(
            "operatingMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )
        # indexer wont be moving if ds is not in allowed mode
        # transition ds to stow to allow SetIndexPosition cmd accepted
        dish_structure.Stow()
        STOW = 5
        event_store.wait_for_value(STOW)

    LOGGER.info("Resetting indexer position to UNKNOWN")
    UNKNOWN = 0
    dish_structure.SetIndexPosition(UNKNOWN)


@pytest.fixture(scope="function")
def reset_receiver_devices(spf, spfrx):
    LOGGER.info("Restoring all receiver devices to default")
    spf.ResetToDefault()
    spfrx.ResetToDefault()


@pytest.fixture
def dish_freq_band_configuration(
    event_store,
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
                event_store,
            )
            event_store.clear_queue()

            [[_], [_]] = dish_manager.command_inout(f"ConfigureBand{band_number}", False)

            try:
                # wait for events
                event_store.wait_for_value(Band(int(band_number)), timeout=60)
                assert dish_manager.configuredBand.name == f"B{band_number}"
                LOGGER.info(f"{dish_manager} successfully transitioned to Band {band_number}")
            except RuntimeError:
                LOGGER.info(
                    f"Expected {dish_manager} to transition to band {band_number}"
                    f" no event was recorded. ConfiguredBand:{dish_manager.configuredBand.name}"
                )
            except AssertionError:
                LOGGER.info(
                    f"Expected {dish_manager} to be in band {band_number}"
                    f" but currently reporting band {dish_manager.configuredBand.name}"
                )

    return _BandSelector()


@pytest.fixture
def modes_helper(
    event_store,
    dish_manager,
    modes_command_map,
    dish_freq_band_configuration,
):
    """
    A helper that manages device modes using events
    """

    class _ModesHelper:
        def ensure_dish_manager_mode(self, mode_name):
            """Move dish master to mode_name.
            Via STANDBY_FP, to ensure any mode can move to any mode.
            """
            if dish_manager.dishMode.name == mode_name:
                LOGGER.info("Dish master is already at requested mode")
                return

            # handle case where dish mode is unknown
            if dish_manager.dishMode.name == "UNKNOWN":
                self.dish_manager_go_to_mode("STOW")
                if mode_name == "STOW":
                    return

            if mode_name == "STOW":
                self.dish_manager_go_to_mode("STOW")
                return
            elif mode_name == "STANDBY_FP":
                self.dish_manager_go_to_mode("STANDBY_FP")
                return
            else:
                # transition to desired mode through STANDBY_FP
                self.dish_manager_go_to_mode("STANDBY_FP")
                self.dish_manager_go_to_mode(mode_name)

        def dish_manager_go_to_mode(self, mode_name):
            """Move device to mode_name"""
            if dish_manager.dishMode.name == mode_name:
                LOGGER.info("Dish master is already at requested mode")
                return

            # make sure there is a configured
            # band if the requested mode is operate
            if mode_name == "OPERATE" and dish_manager.configuredBand.name in ["NONE", "UNKNOWN"]:
                dish_freq_band_configuration.go_to_band(2)

            dish_manager.subscribe_event(
                "dishMode",
                tango.EventType.CHANGE_EVENT,
                event_store,
            )
            event_store.clear_queue()

            # Move to mode_name
            command_name = modes_command_map[mode_name]
            LOGGER.info(
                f"Moving {dish_manager} from " f"{dish_manager.dishMode.name} to {mode_name}"
            )

            LOGGER.info(f"{dish_manager} executing {command_name} ")
            [[_], [_]] = dish_manager.command_inout(command_name)

            try:
                # wait for events
                event_store.wait_for_value(DishMode[mode_name], timeout=60)
                assert dish_manager.dishMode.name == mode_name
                LOGGER.info(f"{dish_manager} successfully transitioned to {mode_name} mode")
            except RuntimeError:
                LOGGER.info(
                    f"Expected {dish_manager} to transition to {mode_name} dish mode"
                    f" but no event was recorded. Current dishMode:{dish_manager.dishMode.name}"
                )
            except AssertionError:
                LOGGER.info(
                    f"Expected {dish_manager} to be in {mode_name} dish mode"
                    f" but currently reporting {dish_manager.dishMode.name} dish mode"
                )

    return _ModesHelper()
