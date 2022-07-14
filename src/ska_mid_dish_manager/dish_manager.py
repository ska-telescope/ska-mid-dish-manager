# pylint: disable=abstract-method
# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring

from ska_tango_base import SKAController
from tango import AttrWriteType, DevFloat, DevVarDoubleArray, DispLevel
from tango.server import attribute, command, run

from ska_mid_dish_manager.component_managers.dish_manager_cm import (
    DishManagerComponentManager,
)
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    DishMode,
    PointingState,
    PowerState,
    TrackInterpolationMode,
    TrackProgramMode,
    TrackTableLoadMode,
    UsageStatus,
)


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class DishManager(SKAController):
    """
    The Dish Manager of the Dish LMC subsystem
    """

    def create_component_manager(self):
        """Create the component manager for DishManager

        :return: Instance of DishManagerComponentManager
        :rtype: DishManagerComponentManager
        """
        return DishManagerComponentManager(
            logger=self.logger,
            communication_state_callback=None,
            component_state_callback=self._component_state_changed,
        )

    # pylint: disable=unused-argument
    def _component_state_changed(self, *args, **kwargs):
        if not hasattr(self, "_dish_mode"):
            return
        if "dish_mode" in kwargs:
            # rules might be here
            # pylint: disable=attribute-defined-outside-init
            self._dish_mode = kwargs["dish_mode"]
            self.push_change_event("dishMode", self._dish_mode)

    class InitCommand(
        SKAController.InitCommand
    ):  # pylint: disable=too-few-public-methods
        """
        A class for the Dish Manager's init_device() method
        """

        def do(self):
            """
            Initializes the attributes and properties of the DishManager
            """
            device = self._device
            # pylint: disable=protected-access
            device._achieved_pointing = [0.0, 0.0, 0.0]
            device._achieved_target_lock = False
            device._attenuation_pol_h = 0.0
            device._attenuation_pol_v = 0.0
            device._azimuth_over_wrap = False
            device._band1_pointing_model_params = []
            device._band2_pointing_model_params = []
            device._band3_pointing_model_params = []
            device._band4_pointing_model_params = []
            device._band5a_pointing_model_params = []
            device._band5b_pointing_model_params = []
            device._band1_sampler_frequency = 0.0
            device._band2_sampler_frequency = 0.0
            device._band3_sampler_frequency = 0.0
            device._band4_sampler_frequency = 0.0
            device._band5a_sampler_frequency = 0.0
            device._band5b_sampler_frequency = 0.0
            device._capturing = False
            device._configured_band = Band.NONE
            device._configure_target_lock = []
            device._desired_pointing = [0.0, 0.0, 0.0]
            device._dish_mode = DishMode.STARTUP
            device._dsh_max_short_term_power = 13.5
            device._dsh_power_curtailment = True
            device._frequency_response = [[], []]
            device._noise_diode_config = []
            device._pointing_buffer_size = 0
            device._pointing_state = PointingState.UNKNOWN
            device._poly_track = []
            device._power_state = PowerState.LOW
            device._program_track_table = []
            device._synchronised = False
            device._track_interpolation_mode = TrackInterpolationMode.NEWTON
            device._track_program_mode = TrackProgramMode.TABLEA
            device._track_table_load_mode = TrackTableLoadMode.ADD
            device._usage_status = UsageStatus.IDLE
            device.op_state_model.perform_action("component_standby")

            # push change events for dishMode: needed to use testing library
            device.set_change_event("dishMode", True, False)
            super().do()

    # Attributes

    achievedPointing = attribute(
        max_dim_x=3,
        dtype=(float,),
        doc="[0] Timestamp\n[1] Azimuth\n[2] Elevation",
    )
    achievedTargetLock = attribute(
        dtype=bool,
        doc="Indicates whether the Dish is on target or not based on the "
        "pointing error and time period parameters defined in "
        "configureTargetLock.",
    )
    attenuationPolH = attribute(
        dtype=DevFloat, access=AttrWriteType.READ_WRITE
    )
    attenuationPolV = attribute(
        dtype=DevFloat, access=AttrWriteType.READ_WRITE
    )
    azimuthOverWrap = attribute(
        dtype=bool,
        doc="Indicates that the Dish has moved beyond an azimuth wrap limit.",
    )
    band1PointingModelParams = attribute(
        dtype=(DevFloat,),
        max_dim_x=5,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 1 pointing models used by Dish to do "
        "pointing corrections.",
    )
    band2PointingModelParams = attribute(
        dtype=(DevFloat,),
        max_dim_x=5,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 2 pointing models used by Dish to do "
        "pointing corrections.",
    )
    band3PointingModelParams = attribute(
        dtype=(DevFloat,),
        max_dim_x=5,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 3 pointing models used by Dish to do "
        "pointing corrections.",
    )
    band4PointingModelParams = attribute(
        dtype=(DevFloat,),
        max_dim_x=5,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 4 pointing models used by Dish to do "
        "pointing corrections.",
    )
    band5aPointingModelParams = attribute(
        dtype=(DevFloat,),
        max_dim_x=5,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 5a pointing models used by Dish to "
        "do pointing corrections.",
    )
    band5bPointingModelParams = attribute(
        dtype=(DevFloat,),
        max_dim_x=5,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 5b pointing models used by Dish to "
        "do pointing corrections.",
    )
    band1SamplerFrequency = attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND1 absolute sampler clock frequency (base plus offset).",
    )
    band2SamplerFrequency = attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND2 absolute sampler clock frequency (base plus offset).",
    )
    band3SamplerFrequency = attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND3 absolute sampler clock frequency (base plus offset).",
    )
    band4SamplerFrequency = attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND4 absolute sampler clock frequency (base plus offset).",
    )
    band5aSamplerFrequency = attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND5a absolute sampler clock frequency (base plus offset).",
    )
    band5bSamplerFrequency = attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND5b absolute sampler clock frequency (base plus offset).",
    )
    capturing = attribute(
        dtype=bool,
        doc="Indicates whether Dish is capturing data inthe configured band "
        "or not.",
    )
    configuredBand = attribute(
        dtype=Band,
        doc="The frequency band that the Dish is configured to capture data "
        "in.",
    )
    configureTargetLock = attribute(
        dtype=(float,),
        max_dim_x=2,
        access=AttrWriteType.WRITE,
        doc="[0] Pointing error\n[1] Time period",
    )
    desiredPointing = attribute(
        max_dim_x=3, dtype=(float,), access=AttrWriteType.READ_WRITE
    )
    dishMode = attribute(
        dtype=DishMode,
        access=AttrWriteType.WRITE,
        doc="Dish rolled-up operating mode in Dish Control Model (SCM) "
        "notation",
    )
    dshMaxShortTermPower = attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="Configures the Max Short Term Average Power (5sec‐10min) in "
        "kilowatt that the DSH instance is curtailed to while "
        "dshPowerCurtailment is [TRUE]. The default value is 13.5.",
    )
    dshPowerCurtailment = attribute(
        dtype=bool,
        access=AttrWriteType.READ_WRITE,
        doc="The Max Short Term Average Power (5sec‐10min) of each DSH "
        "instance is curtailed to the value configured in "
        "dshMaxShortTermPower. The default condition is [TRUE] ‐ "
        "power curtailment is on. With power curtailment [TRUE], all DSH "
        "functionality is available but at reduced performance (for example "
        "reduced slew rates). With power curtailment [FALSE], all DSH "
        "functionality is available at full performance (for example "
        "maximum slew rates).",
    )
    frequencyResponse = attribute(
        dtype=(((float),),), max_dim_x=1024, max_dim_y=1024
    )
    noiseDiodeConfig = attribute(dtype=(DevFloat,), access=AttrWriteType.WRITE)
    pointingState = attribute(dtype=PointingState)
    programTrackTable = attribute(
        dtype=(float,),
        max_dim_x=150,
        access=AttrWriteType.READ_WRITE,
        doc="Timestamp of i‐th coordinate in table (max 50 coordinates) given "
        "in milliseconds since UNIX epoch, UTC, representing time at which "
        "Dish should track i‐th coordinate.\n Azimuth of i‐th coordinate in "
        "table (max 50 coordinates) given in degrees.\n Elevation of i‐th "
        "coordinate in table (max 50 coordinates) given in degrees",
    )

    pointingBufferSize = attribute(
        dtype=int,
        doc="Number of desiredPointing write values that the buffer has space "
        "for.\nNote: desiredPointing write values are stored by Dish in a "
        "buffer for application at the time specified in each desiredPointing "
        "record.",
    )
    polyTrack = attribute(
        dtype=(float,),
        max_dim_x=9,
        access=AttrWriteType.WRITE,
        doc="[0] Timestamp\n[1] Azimuth\n[2] Elevation\n[3] Azimuth speed\n"
        "[4] Elevation speed\n[5] Azimuth acceleration\n"
        "[6] Elevation acceleration\n[7] Azimuth jerk\n[8] Elevation jerk",
    )
    powerState = attribute(dtype=PowerState)
    trackInterpolationMode = attribute(
        dtype=TrackInterpolationMode,
        access=AttrWriteType.READ_WRITE,
        doc="Selects the type of interpolation to be used in program "
        "tracking.",
    )
    trackProgramMode = attribute(
        dtype=TrackProgramMode,
        access=AttrWriteType.READ_WRITE,
        doc="Selects the track program source (table A, table B, polynomial "
        "stream) used in the ACU for tracking. Coordinates given in the "
        "programTrackTable attribute are loaded in ACU in the selected table.",
    )
    trackTableLoadMode = attribute(
        dtype=TrackTableLoadMode,
        access=AttrWriteType.READ_WRITE,
        doc="Selects track table load mode.\nWith ADD selected, Dish will "
        "add the coordinate set given in programTrackTable attribute to the "
        "list of pointing coordinates already loaded in ACU.\nWith NEW "
        "selected, Dish will delete the list of pointing coordinates "
        "previously loaded in ACU when new coordinates are given in the "
        "programTrackTable attribute.",
    )

    synchronised = attribute(
        dtype=bool,
        doc="Indicates whether the configured band is synchronised or not.",
    )
    usageStatus = attribute(dtype=UsageStatus)

    # Attribute's methods
    # pylint: disable=invalid-name
    def read_achievedPointing(self):
        return self._achieved_pointing

    def read_achievedTargetLock(self):
        return self._achieved_target_lock

    def read_attenuationPolH(self):
        return self._attenuation_pol_h

    def write_attenuationPolH(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._attenuation_pol_h = value

    def read_attenuationPolV(self):
        return self._attenuation_pol_v

    def write_attenuationPolV(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._attenuation_pol_v = value

    def read_azimuthOverWrap(self):
        return self._azimuth_over_wrap

    def read_band1PointingModelParams(self):
        return self._band1_pointing_model_params

    def write_band1PointingModelParams(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._band1_pointing_model_params = value

    def read_band2PointingModelParams(self):
        return self._band2_pointing_model_params

    def write_band2PointingModelParams(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._band2_pointing_model_params = value

    def read_band3PointingModelParams(self):
        return self._band3_pointing_model_params

    def write_band3PointingModelParams(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._band3_pointing_model_params = value

    def read_band4PointingModelParams(self):
        return self._band4_pointing_model_params

    def write_band4PointingModelParams(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._band4_pointing_model_params = value

    def read_band5aPointingModelParams(self):
        return self._band5a_pointing_model_params

    def write_band5aPointingModelParams(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._band5a_pointing_model_params = value

    def read_band5bPointingModelParams(self):
        return self._band5b_pointing_model_params

    def write_band5bPointingModelParams(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._band5b_pointing_model_params = value

    def read_band1SamplerFrequency(self):
        return self._band1_sampler_frequency

    def write_band1SamplerFrequency(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._band1_sampler_frequency = value

    def read_band2SamplerFrequency(self):
        return self._band2_sampler_frequency

    def write_band2SamplerFrequency(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._band2_sampler_frequency = value

    def read_band3SamplerFrequency(self):
        return self._band3_sampler_frequency

    def write_band3SamplerFrequency(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._band3_sampler_frequency = value

    def read_band4SamplerFrequency(self):
        return self._band4_sampler_frequency

    def write_band4SamplerFrequency(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._band4_sampler_frequency = value

    def read_band5aSamplerFrequency(self):
        return self._band5a_sampler_frequency

    def write_band5aSamplerFrequency(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._band5a_sampler_frequency = value

    def read_band5bSamplerFrequency(self):
        return self._band5b_sampler_frequency

    def write_band5bSamplerFrequency(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._band5b_sampler_frequency = value

    def read_capturing(self):
        return self._capturing

    def read_configuredBand(self):
        return self._configured_band

    def read_configureTargetLock(self):
        return self._configure_target_lock

    def write_configureTargetLock(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._configure_target_lock = value

    def read_desiredPointing(self):
        return self._desired_pointing

    def write_desiredPointing(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._desired_pointing = value

    def read_dishMode(self):
        return self._dish_mode

    def write_dishMode(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._dish_mode = value
        # pylint: disable=protected-access
        self.component_manager._update_component_state(dish_mode=value)

    def read_dshMaxShortTermPower(self):
        return self._dsh_max_short_term_power

    def write_dshMaxShortTermPower(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._dsh_max_short_term_power = value

    def read_dshPowerCurtailment(self):
        return self._dsh_power_curtailment

    def write_dshPowerCurtailment(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._dsh_power_curtailment = value

    def read_frequencyResponse(self):
        return self._frequency_response

    def read_noiseDiodeConfig(self):
        return self._noise_diode_config

    def write_noiseDiodeConfig(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._noise_diode_config = value

    def read_pointingState(self):
        return self._pointing_state

    def read_pointingBufferSize(self):
        return self._pointing_buffer_size

    def read_polyTrack(self):
        return self._poly_track

    def write_polyTrack(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._poly_track = value

    def read_powerState(self):
        return self._power_state

    def read_programTrackTable(self):
        return self._program_track_table

    def write_programTrackTable(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._program_track_table = value

    def read_trackInterpolationMode(self):
        return self._track_interpolation_mode

    def write_trackInterpolationMode(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._track_interpolation_mode = value

    def read_trackProgramMode(self):
        return self._track_program_mode

    def write_trackProgramMode(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._track_program_mode = value

    def read_trackTableLoadMode(self):
        return self._track_table_load_mode

    def write_trackTableLoadMode(self, value):
        # pylint: disable=attribute-defined-outside-init
        self._track_table_load_mode = value

    def read_synchronised(self):
        return self._synchronised

    def read_usageStatus(self):
        return self._usage_status

    # Commands
    # pylint: disable=no-self-use
    @command(
        dtype_in=str,
        doc_in="Indicates the time, in UTC, at which command execution "
        "should start.",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand1(self, timestamp):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 1. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        return

    @command(
        dtype_in=str,
        doc_in="Indicates the time, in UTC, at which command execution "
        "should start.",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand2(self, timestamp):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 2. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        return

    @command(
        dtype_in=str,
        doc_in="Indicates the time, in UTC, at which command execution "
        "should start.",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand3(self, timestamp):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 3. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        return

    @command(
        dtype_in=str,
        doc_in="Indicates the time, in UTC, at which command execution "
        "should start.",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand4(self, timestamp):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 4. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        return

    @command(
        dtype_in=str,
        doc_in="Indicates the time, in UTC, at which command execution "
        "should start.",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand5a(self, timestamp):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 5a. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        return

    @command(
        dtype_in=str,
        doc_in="Indicates the time, in UTC, at which command execution "
        "should start.",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand5b(self, timestamp):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 5b. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        return

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def FlushCommandQueue(self):
        """Flushes the queue of time stamped commands."""
        return

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def Scan(self):
        """
        The Dish is tracking the commanded pointing positions within the
        specified SCAN pointing accuracy. (TBC14)
        NOTE: This pointing state is currently proposed and there are
        currently no requirements for this functionality.
        """
        return

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def SetMaintenanceMode(self):
        """
        This command triggers the Dish to transition to the MAINTENANCE
        Dish Element Mode, and returns to the caller. To go into a state
        that is safe to approach the Dish by a maintainer, and to enable the
        Engineering interface to allow direct access to low level control and
        monitoring by engineers and maintainers. This mode will also enable
        engineers and maintainers to upgrade SW and FW. Dish also enters this
        mode when an emergency stop button is pressed.
        """
        return

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def SetOperateMode(self):
        """
        This command triggers the Dish to transition to the OPERATE Dish
        Element Mode, and returns to the caller. This mode fulfils the main
        purpose of the Dish, which is to point to designated directions while
        capturing data and transmitting it to CSP. The Dish will automatically
        start capturing data after entering OPERATE mode.
        """
        return

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def SetStandbyLPMode(self):
        """
        This command triggers the Dish to transition to the STANDBY‐LP Dish
        Element Mode, and returns to the caller. Standby_LP is the default
        mode when the Dish is configured for low power consumption, and is
        the mode wherein Dish ends after a start up procedure.
        All subsystems go into a low power state to power only the essential
        equipment. Specifically the Helium compressor will be set to a low
        power consumption, and the drives will be disabled. When issued a
        STOW command while in LOW power, the DS controller should be
        able to turn the drives on, stow the dish and turn the drives off
        again. The purpose of this mode is to enable the observatory to
        perform power management (load curtailment), and also to conserve
        energy for non‐operating dishes.
        """
        self.component_manager.set_standby_lp_mode()

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def SetStandbyFPMode(self):
        """
        This command triggers the Dish to transition to the STANDBY‐FP Dish
        Element Mode, and returns to the caller.
        To prepare all subsystems for active observation, once a command is
        received by TM to go to the FULL_POWER mode.
        """
        return

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def SetStowMode(self):
        """
        This command triggers the Dish to transition to the STOW Dish Element
        Mode, and returns to the caller. To point the dish in a direction that
        minimises the wind loads on the structure, for survival in strong wind
        conditions. The Dish is able to observe in the stow position, for the
        purpose of transient detection.
        """
        return

    @command(
        dtype_in=DevVarDoubleArray,
        doc_in="[0]: Azimuth\n[1]: Elevation",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def Slew(self, az_el_coordinates):  # pylint: disable=unused-argument
        """
        When the Slew command is received the Dish will start moving at
        maximum speed to the commanded (Az,El) position given as
        command argument. No pointing accuracy requirements are
        applicable in this state, and the pointingState attribute will report
        SLEW.
        """
        return

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def StartCapture(self):
        return

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def StopCapture(self):
        return

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def Synchronise(self):
        """
        Reset configured band sample counters. Command only valid in
        SPFRx Data_Capture mode.
        """
        return

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def Track(self):
        """
        When the Track command is received the Dish will start tracking the
        commanded positions.
        The pointingState attribute will report SLEW while the Dish is settling
        onto a target and is still not within the specified pointing accuracy.
        As soon as the pointing accuracy is within specifications, the
        pointingState attribute will report TRACK.
        Track data source (TABLEA, TABLEB, POLY) used for tracking is pre‐
        configured using trackProgramMode attribute.
        Tracking using program table (A, B) is pre‐configured using the
        following attributes:
            1. trackInterpolationMode: to select type of interpolation,
                Newton (default) or Spline.
            2. programTrackTable: to load program table data
                (Az,El,timestamp sets) on selected ACU table
            3. trackTableLoadMode: to add/append new track table data
        """
        return

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def TrackStop(self):
        """
        When the TrackStop command Is received the Dish will stop tracking
        but will not apply brakes.
        """
        return


def main(args=None, **kwargs):
    return run((DishManager,), args=args, **kwargs)


if __name__ == "__main__":
    main()
