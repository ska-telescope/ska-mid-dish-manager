"""Tests for CommandActions."""

import logging
from threading import Event
from unittest import mock

import pytest
from ska_control_model import AdminMode, ResultCode, TaskStatus

from ska_mid_dish_manager.models.command_actions import (
    ConfigureBandActionSequence,
    SetStandbyLPModeAction,
    TrackLoadStaticOffAction,
)
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    DSOperatingMode,
    DSPowerState,
    IndexerPosition,
    SPFOperatingMode,
    SPFRxOperatingMode,
)

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


@pytest.mark.unit
class TestCommandActions:
    """Tests for CommandActions."""

    # pylint: disable=protected-access,attribute-defined-outside-init
    def setup_method(self):
        """Set up context."""
        sub_component_managers_mock = {
            "DS": mock.MagicMock(
                _component_state={
                    "powerstate": DSPowerState.LOW_POWER,
                    "operatingmode": DSOperatingMode.STANDBY,
                    "indexerposition": IndexerPosition.B1,
                    "actstaticoffsetvalueel": 1,
                    "actstaticoffsetvaluexel": 1,
                },
                execute_command=mock.MagicMock(return_value=(None, None)),
            ),
            "SPF": mock.MagicMock(
                _component_state={"operatingmode": SPFOperatingMode.STANDBY_LP},
                execute_command=mock.MagicMock(return_value=(None, None)),
            ),
            "SPFRX": mock.MagicMock(
                _component_state={
                    "configuredband": Band.B1,
                    "operatingmode": SPFRxOperatingMode.STANDBY,
                    "adminmode": AdminMode.ONLINE,
                },
                execute_command=mock.MagicMock(return_value=(None, None)),
            ),
        }

        self.dish_manager_cm_mock = mock.MagicMock(
            _component_state={
                "dishmode": DishMode.STANDBY_LP,
                "configuredband": None,
                "actstaticoffsetvalueel": 1,
                "actstaticoffsetvaluexel": 1,
            },
        )
        self.dish_manager_cm_mock.sub_component_managers = sub_component_managers_mock

        def is_device_ignored(device: str):
            """Check whether the given device is ignored."""
            return False

        self.dish_manager_cm_mock.is_device_ignored = is_device_ignored

    def teardown_method(self):
        """Tear down context."""
        return

    @pytest.mark.unit
    def test_happy_path_command_no_argument(self):
        """Test set_standby_lp_mode."""
        task_abort_event = Event()
        # Save any progress calls
        progress_calls = []

        def my_task_callback(**kwargs):
            if kwargs.get("progress") is not None:
                progress_calls.append(kwargs["progress"])

        SetStandbyLPModeAction(LOGGER, self.dish_manager_cm_mock).execute(
            my_task_callback, task_abort_event
        )

        expected_progress_updates = [
            "Fanned out commands: SPF.SetStandbyLPMode, SPFRX.SetStandbyMode, DS.SetStandbyMode",
            # Expected sub device changes
            "Awaiting DS operatingmode, powerstate change to STANDBY, LOW_POWER",
            "Awaiting SPF operatingmode change to STANDBY_LP",
            "Awaiting SPFRX operatingmode change to STANDBY",
            # Expected action change
            "Awaiting dishmode change to STANDBY_LP",
            # Changes
            "SPF operatingmode changed to STANDBY_LP",
            "SPFRX operatingmode changed to STANDBY",
            "DS operatingmode changed to STANDBY",
            "SetStandbyLPMode completed",
        ]

        progress_string = "".join([str(event) for event in progress_calls])

        for progress_update in expected_progress_updates:
            assert progress_update in progress_string

    @pytest.mark.unit
    def test_happy_path_command_with_argument(self):
        """Test track_load_static_off."""
        task_abort_event = Event()
        # Save any progress calls
        progress_calls = []

        # pylint: disable=unused-argument
        def my_task_callback(**kwargs):
            if kwargs.get("progress") is not None:
                progress_calls.append(kwargs["progress"])

        TrackLoadStaticOffAction(
            LOGGER,
            self.dish_manager_cm_mock,
            off_xel=1,
            off_el=1,
        ).execute(my_task_callback, task_abort_event)

        expected_progress_updates = [
            "Fanned out commands: DS.TrackLoadStaticOff",
            # Expected sub device changes
            "Awaiting DS actstaticoffsetvaluexel, actstaticoffsetvalueel change to 1, 1",
            # Expected action change
            "Awaiting actstaticoffsetvaluexel, actstaticoffsetvalueel change to 1, 1",
            # Changes
            "DS actstaticoffsetvaluexel changed to 1",
            "DS actstaticoffsetvalueel changed to 1",
            "TrackLoadStaticOff completed",
        ]

        progress_string = "".join([str(event) for event in progress_calls])

        for progress_update in expected_progress_updates:
            assert progress_update in progress_string

    @pytest.mark.unit
    def test_unhappy_path_command_failed_task_status(self):
        """Test set_standby_lp_mode."""
        self.dish_manager_cm_mock.sub_component_managers["SPF"].execute_command = mock.MagicMock(
            return_value=(TaskStatus.FAILED, "some failure message")
        )
        task_abort_event = Event()
        # Save any progress calls
        progress_calls = []

        def my_task_callback(**kwargs):
            if kwargs.get("progress") is not None:
                progress_calls.append(kwargs["progress"])

        SetStandbyLPModeAction(LOGGER, self.dish_manager_cm_mock).execute(
            my_task_callback, task_abort_event
        )

        # reset the mock to avoid side effects
        self.dish_manager_cm_mock.sub_component_managers["SPF"].execute_command = mock.MagicMock(
            return_value=(None, None)
        )

        expected_progress_updates = [
            "SetStandbyLPMode failed some failure message",
        ]
        progress_string = "".join([str(event) for event in progress_calls])

        for progress_update in expected_progress_updates:
            assert progress_update in progress_string

    @pytest.mark.unit
    def test_configure_band_sequence_from_fp(self):
        """Test configure_band_cmd happy path from full power."""
        task_abort_event = Event()
        progress_calls = []
        result_calls = []

        def my_task_callback(**kwargs):
            if kwargs.get("progress") is not None:
                progress_calls.append(kwargs["progress"])

                # Update the mock component states as callbacks come in so that the states move
                # as expected
                if "Awaiting configuredband change to B2" in kwargs["progress"]:
                    self.dish_manager_cm_mock.sub_component_managers["DS"]._component_state[
                        "indexerposition"
                    ] = IndexerPosition.B2
                    self.dish_manager_cm_mock.sub_component_managers["SPFRX"]._component_state[
                        "configuredband"
                    ] = Band.B2
                    self.dish_manager_cm_mock._component_state["configuredband"] = Band.B2
                elif "Awaiting dishmode change to OPERATE" in kwargs["progress"]:
                    self.dish_manager_cm_mock.sub_component_managers["DS"]._component_state[
                        "operatingmode"
                    ] = DSOperatingMode.POINT
                    self.dish_manager_cm_mock._component_state["dishmode"] = DishMode.OPERATE
            if kwargs.get("result") is not None:
                result_calls.append(kwargs.get("result"))

        # Set mock component states to FP
        self.dish_manager_cm_mock.sub_component_managers["DS"]._component_state[
            "operatingmode"
        ] = DSOperatingMode.STANDBY
        self.dish_manager_cm_mock.sub_component_managers["SPF"]._component_state[
            "operatingmode"
        ] = SPFOperatingMode.OPERATE
        self.dish_manager_cm_mock._component_state["dishmode"] = DishMode.STANDBY_FP

        ConfigureBandActionSequence(
            LOGGER,
            self.dish_manager_cm_mock,
            band_number=Band.B2,
            synchronise=True,
        ).execute(my_task_callback, task_abort_event)

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

        progress_string = "".join([str(event) for event in progress_calls])

        for progress_update in expected_progress_updates:
            assert progress_update in progress_string

        assert len(result_calls) == 1
        assert result_calls[0] == (ResultCode.OK, "SetOperateMode completed")

    @pytest.mark.unit
    def test_configure_band_sequence_from_lp(self):
        """Test configure_band_cmd happy path from low power."""
        task_abort_event = Event()
        progress_calls = []
        result_calls = []

        def my_task_callback(**kwargs):
            if kwargs.get("progress") is not None:
                progress_calls.append(kwargs["progress"])

                # Update the mock component states as callbacks come in so that the states move
                # as expected
                if "Awaiting dishmode change to STANDBY_FP" in kwargs["progress"]:
                    self.dish_manager_cm_mock.sub_component_managers["DS"]._component_state[
                        "operatingmode"
                    ] = DSOperatingMode.STANDBY
                    self.dish_manager_cm_mock.sub_component_managers["DS"]._component_state[
                        "powerstate"
                    ] = DSPowerState.FULL_POWER
                    self.dish_manager_cm_mock.sub_component_managers["SPF"]._component_state[
                        "operatingmode"
                    ] = SPFOperatingMode.OPERATE
                    self.dish_manager_cm_mock._component_state["dishmode"] = DishMode.STANDBY_FP
                elif "Awaiting configuredband change to B2" in kwargs["progress"]:
                    self.dish_manager_cm_mock.sub_component_managers["DS"]._component_state[
                        "indexerposition"
                    ] = IndexerPosition.B2
                    self.dish_manager_cm_mock.sub_component_managers["SPFRX"]._component_state[
                        "configuredband"
                    ] = Band.B2
                    self.dish_manager_cm_mock._component_state["configuredband"] = Band.B2
                elif "Awaiting dishmode change to OPERATE" in kwargs["progress"]:
                    self.dish_manager_cm_mock.sub_component_managers["DS"]._component_state[
                        "operatingmode"
                    ] = DSOperatingMode.POINT
                    self.dish_manager_cm_mock._component_state["dishmode"] = DishMode.OPERATE
            if kwargs.get("result") is not None:
                result_calls.append(kwargs.get("result"))

        ConfigureBandActionSequence(
            LOGGER,
            self.dish_manager_cm_mock,
            band_number=Band.B2,
            synchronise=True,
        ).execute(my_task_callback, task_abort_event)

        expected_progress_updates = [
            # First SetStandbyFPMode
            "Fanned out commands: DS.SetStandbyMode, DS.SetPowerMode",
            "Awaiting DS operatingmode change to STANDBY",
            "Awaiting DS powerstate change to FULL_POWER",
            "Awaiting dishmode change to STANDBY_FP",
            "DS operatingmode changed to STANDBY",
            "DS.SetStandbyMode completed",
            "DS powerstate changed to FULL_POWER",
            "DS.SetPowerMode completed",
            "SetStandbyFPMode complete. Triggering on success action.",
            # Then ConfigureBand2
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

        progress_string = "".join([str(event) for event in progress_calls])

        for progress_update in expected_progress_updates:
            assert progress_update in progress_string

        assert len(result_calls) == 1
        assert result_calls[0] == (ResultCode.OK, "SetOperateMode completed")
