"""Tests for FannedOutTangoLongRunningCommand."""

import json
import logging
from unittest import mock

import pytest
from ska_control_model import TaskStatus

from ska_mid_dish_manager.models.fanned_out_command import (
    FannedOutCommandStatus,
    FannedOutTangoLongRunningCommand,
)

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)


@pytest.mark.unit
class TestFannedOutTangoLongRunningCommand:
    """Tests for FannedOutTangoLongRunningCommand."""

    # pylint: disable=protected-access,attribute-defined-outside-init
    def setup_method(self):
        """Set up context."""
        self.device_component_manager = mock.MagicMock(
            _component_state={},
        )

        self.command = FannedOutTangoLongRunningCommand(
            logger=LOGGER,
            device="test/device/01",
            command_name="TestCommand",
            device_component_manager=self.device_component_manager,
        )

        self.command.executed_cmd_message = "command_id_123"

    def teardown_method(self):
        """Tear down context."""
        return

    @pytest.mark.unit
    def test_is_command_in_lrc_queued_returns_true(self):
        """Test queued command detection."""
        self.device_component_manager.read_attribute_value.return_value = (
            json.dumps({"uid": "command_id_123"}),
        )

        result = self.command._is_command_in_lrc_queued()

        assert result is True

        self.device_component_manager.read_attribute_value.assert_called_with(
            "lrcqueue",
            log_read=False,
        )

    @pytest.mark.unit
    def test_is_command_in_lrc_queued_returns_false_when_not_found(self):
        """Test queued command detection when command not found."""
        self.device_component_manager.read_attribute_value.return_value = (
            json.dumps({"uid": "another_command"}),
        )

        result = self.command._is_command_in_lrc_queued()

        assert result is False

    @pytest.mark.unit
    def test_is_command_in_lrc_queued_returns_false_for_non_tuple(self):
        """Test queued command detection with invalid attribute type."""
        self.device_component_manager.read_attribute_value.return_value = "bad_value"

        result = self.command._is_command_in_lrc_queued()

        assert result is False

    @pytest.mark.unit
    def test_is_command_in_lrc_executing_returns_true(self):
        """Test executing command detection."""
        self.device_component_manager.read_attribute_value.return_value = (
            json.dumps({"uid": "command_id_123"}),
        )

        result = self.command._is_command_in_lrc_executing()

        assert result is True

        self.device_component_manager.read_attribute_value.assert_called_with(
            "lrcexecuting",
            log_read=False,
        )

    @pytest.mark.unit
    def test_is_command_in_lrc_executing_returns_false_when_not_found(self):
        """Test executing command detection when command not found."""
        self.device_component_manager.read_attribute_value.return_value = (
            json.dumps({"uid": "another_command"}),
        )

        result = self.command._is_command_in_lrc_executing()

        assert result is False

    @pytest.mark.unit
    def test_get_command_lrc_finished_dict_returns_dict(self):
        """Test finished command detection."""
        expected_result = {
            "uid": "command_id_123",
            "result": "some result",
            "status": TaskStatus.COMPLETED.name,
        }

        self.device_component_manager.read_attribute_value.return_value = (
            json.dumps(expected_result),
        )

        result = self.command._get_command_lrc_finished_dict()

        assert result == expected_result

        self.device_component_manager.read_attribute_value.assert_called_with(
            "lrcfinished",
            log_read=False,
        )

    @pytest.mark.unit
    def test_get_command_lrc_finished_dict_returns_none_when_not_found(self):
        """Test finished command detection when command not found."""
        self.device_component_manager.read_attribute_value.return_value = (
            json.dumps(
                {
                    "uid": "another_command",
                    "result": "some result",
                    "status": TaskStatus.COMPLETED.name,
                }
            ),
        )

        result = self.command._get_command_lrc_finished_dict()

        assert result is None

    @pytest.mark.unit
    def test_get_command_lrc_finished_dict_returns_none_for_invalid_json(self):
        """Test finished command detection with invalid json."""
        self.device_component_manager.read_attribute_value.return_value = ("not-json",)

        result = self.command._get_command_lrc_finished_dict()

        assert result is None

    @pytest.mark.unit
    def test_update_status_sets_in_progress_when_executing(self):
        """Test update status sets IN_PROGRESS."""
        self.command._status = FannedOutCommandStatus.QUEUED
        self.command.is_lrc_finished = False

        self.command._get_command_lrc_finished_dict = mock.MagicMock(return_value=None)
        self.command._is_command_in_lrc_executing = mock.MagicMock(return_value=True)
        self.command._is_command_in_lrc_queued = mock.MagicMock(return_value=False)

        self.command._update_status(mock.MagicMock())

        assert self.command._status == FannedOutCommandStatus.IN_PROGRESS

    @pytest.mark.unit
    def test_update_status_sets_queued_when_still_queued(self):
        """Test update status remains QUEUED."""
        self.command._status = FannedOutCommandStatus.QUEUED
        self.command.is_lrc_finished = False

        self.command._get_command_lrc_finished_dict = mock.MagicMock(return_value=None)
        self.command._is_command_in_lrc_executing = mock.MagicMock(return_value=False)
        self.command._is_command_in_lrc_queued = mock.MagicMock(return_value=True)

        self.command._update_status(mock.MagicMock())

        assert self.command._status == FannedOutCommandStatus.QUEUED

    @pytest.mark.unit
    def test_update_status_sets_completed_when_lrc_finished(self):
        """Test update status sets COMPLETED."""
        self.command._status = FannedOutCommandStatus.IN_PROGRESS
        self.command.is_lrc_finished = True

        self.command.component_state = {}
        self.command.awaited_component_state = {}

        self.command._update_status(mock.MagicMock())

        assert self.command._status == FannedOutCommandStatus.COMPLETED

    @pytest.mark.unit
    def test_update_status_stays_in_progress_when_component_not_ready(self):
        """Test update status remains IN_PROGRESS when component state is not ready."""
        self.command._status = FannedOutCommandStatus.IN_PROGRESS
        self.command.is_lrc_finished = True

        self.command.component_state = {}
        self.command.awaited_component_state = {"some_attr": 123}

        self.command._update_status(mock.MagicMock())

        assert self.command._status == FannedOutCommandStatus.IN_PROGRESS

    @pytest.mark.unit
    def test_update_status_stays_in_progress_when_lrc_not_finished(self):
        """Test update status remains IN_PROGRESS when LRC is not finished."""
        self.command._status = FannedOutCommandStatus.IN_PROGRESS
        self.command.is_lrc_finished = False

        self.command._get_command_lrc_finished_dict = mock.MagicMock(return_value=None)
        self.command._is_command_in_lrc_executing = mock.MagicMock(return_value=True)
        self.command._is_command_in_lrc_queued = mock.MagicMock(return_value=False)

        self.command._update_status(mock.MagicMock())

        assert self.command._status == FannedOutCommandStatus.IN_PROGRESS

    @pytest.mark.unit
    def test_update_status_sets_failed_when_lrc_failed(self):
        """Test update status sets FAILED."""
        self.command._status = FannedOutCommandStatus.IN_PROGRESS
        self.command.is_lrc_finished = False

        self.command._get_command_lrc_finished_dict = mock.MagicMock(
            return_value={
                "uid": "command_id_123",
                "result": "command failed",
                "status": TaskStatus.FAILED.name,
            }
        )

        self.command._update_status(mock.MagicMock())

        assert self.command._status == FannedOutCommandStatus.FAILED
        assert self.command.executed_cmd_response == "command failed"

    @pytest.mark.unit
    def test_update_status_sets_rejected_when_lrc_rejected(self):
        """Test update status sets REJECTED."""
        self.command._status = FannedOutCommandStatus.IN_PROGRESS
        self.command.is_lrc_finished = False

        self.command._get_command_lrc_finished_dict = mock.MagicMock(
            return_value={
                "uid": "command_id_123",
                "result": "command rejected",
                "status": TaskStatus.REJECTED.name,
            }
        )

        self.command._update_status(mock.MagicMock())

        assert self.command._status == FannedOutCommandStatus.REJECTED
        assert self.command.executed_cmd_response == "command rejected"

    @pytest.mark.unit
    def test_update_status_sets_aborted_when_lrc_aborted(self):
        """Test update status sets ABORTED."""
        self.command._status = FannedOutCommandStatus.IN_PROGRESS
        self.command.is_lrc_finished = False

        self.command._get_command_lrc_finished_dict = mock.MagicMock(
            return_value={
                "uid": "command_id_123",
                "result": "command aborted",
                "status": TaskStatus.ABORTED.name,
            }
        )

        self.command._update_status(mock.MagicMock())

        assert self.command._status == FannedOutCommandStatus.ABORTED
        assert self.command.executed_cmd_response == "command aborted"

    @pytest.mark.unit
    def test_update_status_sets_timed_out_when_timeout_exceeded(self):
        """Test update status sets TIMED_OUT when timeout exceeded."""
        self.command._status = FannedOutCommandStatus.IN_PROGRESS
        self.command.is_lrc_finished = False

        self.command.timeout_s = 5
        self.command.start_time = 100

        self.command._get_command_lrc_finished_dict = mock.MagicMock(return_value=None)
        self.command._is_command_in_lrc_executing = mock.MagicMock(return_value=False)
        self.command._is_command_in_lrc_queued = mock.MagicMock(return_value=False)

        with mock.patch("time.time", return_value=106):
            self.command._update_status(mock.MagicMock())

        assert self.command._status == FannedOutCommandStatus.TIMED_OUT
