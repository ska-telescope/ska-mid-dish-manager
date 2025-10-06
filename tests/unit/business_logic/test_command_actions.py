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
                }
            ),
            "SPF": mock.MagicMock(_component_state={"operatingmode": SPFOperatingMode.STANDBY_LP}),
            "SPFRX": mock.MagicMock(
                _component_state={
                    "configuredband": Band.B1,
                    "operatingmode": SPFRxOperatingMode.STANDBY,
                    "adminmode": AdminMode.ONLINE,
                }
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
        self.command_tracker_mock = mock.MagicMock()

    def teardown_method(self):
        """Tear down context."""
        return

    @pytest.mark.unit
    @mock.patch("ska_mid_dish_manager.models.fanned_out_command.SubmittedSlowCommand")
    def test_happy_path_command_no_argument(self, patched_slow_command):
        """Test set_standby_lp_mode."""
        mock_command_instance = mock.MagicMock()
        mock_command_instance.return_value = (None, None)

        patched_slow_command.return_value = mock_command_instance

        # Set mocked dishmode to desired value so that the command map doesn't wait forever
        task_abort_event = Event()

        # Save any progress calls
        progress_calls = []

        # pylint: disable=unused-argument
        def my_task_callback(progress=None, status=None, result=None):
            if progress is not None:
                progress_calls.append(progress)

        SetStandbyLPModeAction(
            LOGGER, self.command_tracker_mock, self.dish_manager_cm_mock
        ).execute(my_task_callback, task_abort_event)

        expected_progress_updates = [
            "SetStandbyMode called on DS",
            "SetStandbyLPMode called on SPF",
            "SetStandbyMode called on SPFRX",
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
    @mock.patch("ska_mid_dish_manager.models.fanned_out_command.SubmittedSlowCommand")
    def test_happy_path_command_with_argument(self, patched_slow_command):
        """Test configure_band_cmd."""
        mock_command_instance = mock.MagicMock()
        mock_command_instance.return_value = (None, None)

        patched_slow_command.return_value = mock_command_instance

        # Set mocked dishmode to desired value so that the command map doesn't wait forever
        task_abort_event = Event()

        # Save any progress calls
        progress_calls = []

        # pylint: disable=unused-argument
        def my_task_callback(progress=None, status=None, result=None):
            if progress is not None:
                progress_calls.append(progress)

        TrackLoadStaticOffAction(
            LOGGER,
            self.command_tracker_mock,
            self.dish_manager_cm_mock,
            off_xel=1,
            off_el=1,
        ).execute(my_task_callback, task_abort_event)

        expected_progress_updates = [
            "TrackLoadStaticOff called on DS",
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
    @mock.patch("ska_mid_dish_manager.models.fanned_out_command.SubmittedSlowCommand")
    def test_unhappy_path_command_failed_task_status(self, patched_slow_command):
        """Test set_standby_lp_mode."""
        mock_command_instance = mock.MagicMock()
        mock_command_instance.return_value = (TaskStatus.FAILED, "some_command_id")

        patched_slow_command.return_value = mock_command_instance

        # Set mocked dishmode to desired value so that the command map doesn't wait forever
        task_abort_event = Event()

        # Save any progress calls
        progress_calls = []

        # pylint: disable=unused-argument
        def my_task_callback(progress=None, status=None, result=None):
            if progress is not None:
                progress_calls.append(progress)

        SetStandbyLPModeAction(
            LOGGER, self.command_tracker_mock, self.dish_manager_cm_mock
        ).execute(my_task_callback, task_abort_event)

        expected_progress_updates = [
            "SetStandbyLPMode called on SPF, ID some_command_id",
            "SetStandbyLPMode failed some_command_id",
        ]

        progress_string = "".join([str(event) for event in progress_calls])

        for progress_update in expected_progress_updates:
            assert progress_update in progress_string

    @pytest.mark.unit
    @mock.patch("ska_mid_dish_manager.models.fanned_out_command.SubmittedSlowCommand")
    def test_configure_band_sequence_from_fp(self, patched_slow_command):
        """Test configure_band_cmd happy path from full power."""
        mock_command_instance = mock.MagicMock()
        # Simulate all slow commands completing immediately with no errors
        mock_command_instance.return_value = (None, None)
        patched_slow_command.return_value = mock_command_instance

        task_abort_event = Event()
        progress_calls = []
        result_calls = []

        # pylint: disable=unused-argument
        def my_task_callback(progress=None, status=None, result=None):
            if progress is not None:
                progress_calls.append(progress)

                # Update the mock component states as callbacks come in so that the states move
                # as expected
                if "Awaiting configuredband change to B2" in progress:
                    self.dish_manager_cm_mock.sub_component_managers["DS"]._component_state[
                        "indexerposition"
                    ] = IndexerPosition.B2
                    self.dish_manager_cm_mock.sub_component_managers["SPFRX"]._component_state[
                        "configuredband"
                    ] = Band.B2
                    self.dish_manager_cm_mock._component_state["configuredband"] = Band.B2
                elif "Awaiting dishmode change to OPERATE" in progress:
                    self.dish_manager_cm_mock.sub_component_managers["DS"]._component_state[
                        "operatingmode"
                    ] = DSOperatingMode.POINT
                    self.dish_manager_cm_mock._component_state["dishmode"] = DishMode.OPERATE
            if result is not None:
                result_calls.append(result)

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
            self.command_tracker_mock,
            self.dish_manager_cm_mock,
            band_number=Band.B2,
            synchronise=True,
        ).execute(my_task_callback, task_abort_event)

        expected_progress_updates = [
            # ConfigureBand2
            "SetIndexPosition called on DS",
            "Awaiting DS indexerposition change to B2",
            "ConfigureBand2 called on SPFRX, ID",
            "Awaiting SPFRX configuredband change to B2",
            "Awaiting configuredband change to B2",
            "DS indexerposition changed to B2",
            "DS.SetIndexPosition completed",
            "SPFRX configuredband changed to B2",
            "SPFRX.ConfigureBand2 completed",
            "ConfigureBand2 complete. Triggering on success action.",
            # Then SetOperateMode
            "SetOperateMode called on SPF",
            "Awaiting SPF operatingmode change to OPERATE",
            "SetPointMode called on DS",
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
    @mock.patch("ska_mid_dish_manager.models.fanned_out_command.SubmittedSlowCommand")
    def test_configure_band_sequence_from_lp(self, patched_slow_command):
        """Test configure_band_cmd happy path from low power."""
        mock_command_instance = mock.MagicMock()
        # Simulate all slow commands completing immediately with no errors
        mock_command_instance.return_value = (None, None)
        patched_slow_command.return_value = mock_command_instance

        task_abort_event = Event()
        progress_calls = []
        result_calls = []

        # pylint: disable=unused-argument
        def my_task_callback(progress=None, status=None, result=None):
            if progress is not None:
                progress_calls.append(progress)

                # Update the mock component states as callbacks come in so that the states move
                # as expected
                if "Awaiting dishmode change to STANDBY_FP" in progress:
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
                elif "Awaiting configuredband change to B2" in progress:
                    self.dish_manager_cm_mock.sub_component_managers["DS"]._component_state[
                        "indexerposition"
                    ] = IndexerPosition.B2
                    self.dish_manager_cm_mock.sub_component_managers["SPFRX"]._component_state[
                        "configuredband"
                    ] = Band.B2
                    self.dish_manager_cm_mock._component_state["configuredband"] = Band.B2
                elif "Awaiting dishmode change to OPERATE" in progress:
                    self.dish_manager_cm_mock.sub_component_managers["DS"]._component_state[
                        "operatingmode"
                    ] = DSOperatingMode.POINT
                    self.dish_manager_cm_mock._component_state["dishmode"] = DishMode.OPERATE
            if result is not None:
                result_calls.append(result)

        ConfigureBandActionSequence(
            LOGGER,
            self.command_tracker_mock,
            self.dish_manager_cm_mock,
            band_number=Band.B2,
            synchronise=True,
        ).execute(my_task_callback, task_abort_event)

        expected_progress_updates = [
            # First SetStandbyFPMode
            "SetStandbyMode called on DS",
            "Awaiting DS operatingmode change to STANDBY",
            "SetPowerMode called on DS",
            "Awaiting DS powerstate change to FULL_POWER",
            "Awaiting dishmode change to STANDBY_FP",
            "DS operatingmode changed to STANDBY",
            "DS.SetStandbyMode completedDS powerstate changed to FULL_POWER",
            "DS.SetPowerMode completedSetStandbyFPMode complete. Triggering on success action.",
            # Then ConfigureBand2
            "SetIndexPosition called on DS",
            "Awaiting DS indexerposition change to B2",
            "ConfigureBand2 called on SPFRX, ID",
            "Awaiting SPFRX configuredband change to B2",
            "Awaiting configuredband change to B2",
            "DS indexerposition changed to B2",
            "DS.SetIndexPosition completed",
            "SPFRX configuredband changed to B2",
            "SPFRX.ConfigureBand2 completed",
            "ConfigureBand2 complete. Triggering on success action.",
            # Then SetOperateMode
            "SetOperateMode called on SPF",
            "Awaiting SPF operatingmode change to OPERATE",
            "SetPointMode called on DS",
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
