"""
This module implements the dish manager device for DishLMC.

It exposes the attributes and commands which control the dish
and the subservient devices
"""

import weakref
import re

from ska_tango_base import SKAController
from ska_tango_base.commands import SubmittedSlowCommand
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
)


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class DishManager(SKAController):
    """
    The Dish Manager of the Dish LMC subsystem
    """

    # Access instances for debugging
    instances = weakref.WeakValueDictionary()

    def create_component_manager(self):
        """Create the component manager for DishManager

        :return: Instance of DishManagerComponentManager
        :rtype: DishManagerComponentManager
        """
        return DishManagerComponentManager(
            self.logger,
            communication_state_callback=None,
            component_state_callback=self._component_state_changed,
        )

    def init_command_objects(self) -> None:
        """Initialise the command handlers"""
        super().init_command_objects()

        for (command_name, method_name) in [
            ("SetStandbyLPMode", "set_standby_lp_mode"),
            ("SetOperateMode", "set_operate_mode"),
            ("SetStandbyFPMode", "set_standby_fp_mode"),
        ]:
            self.register_command_object(
                command_name,
                SubmittedSlowCommand(
                    command_name,
                    self._command_tracker,
                    self.component_manager,
                    method_name,
                    callback=None,
                    logger=self.logger,
                ),
            )

    # pylint: disable=unused-argument
    def _component_state_changed(self, *args, **kwargs):
        for dish_attr in kwargs:
            # pylint: disable=attribute-defined-outside-init
            setattr(self, f"_{dish_attr}", kwargs[dish_attr])
            # convert variable to attribute: e.g. dish_mode > dishMode
            attr = re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), dish_attr)
            self.push_change_event(attr, kwargs[dish_attr])

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
            device: DishManager = self._device
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
            device.op_state_model.perform_action("component_standby")

            # push change events for dishMode: needed to use testing library
            device.set_change_event("dishMode", True, False)
            device.set_change_event("pointingState", True, False)
            device.instances[device.get_name()] = device
            device.component_manager.start_communicating()
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
        doc="Indicates whether Dish is capturing data in the configured band "
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

    # Attribute's methods
    # pylint: disable=invalid-name
    def read_achievedPointing(self):
        """Attribute read handler for DishManager achievedPointing"""
        return self._achieved_pointing

    def read_achievedTargetLock(self):
        """Attribute read handler for DishManager achievedTargetLock"""
        return self._achieved_target_lock

    def read_attenuationPolH(self):
        """Attribute read handler for DishManager attenuationPolH"""
        return self._attenuation_pol_h

    def read_attenuationPolV(self):
        """Attribute read handler for DishManager attenuationPolV"""
        return self._attenuation_pol_v

    def read_azimuthOverWrap(self):
        """Attribute read handler for DishManager azimuthOverWrap"""
        return self._azimuth_over_wrap

    def read_band1PointingModelParams(self):
        """Attribute read handler for DishManager band1PointingModelParams"""
        return self._band1_pointing_model_params

    def read_band2PointingModelParams(self):
        """Attribute read handler for DishManager band2PointingModelParams"""
        return self._band2_pointing_model_params

    def read_band3PointingModelParams(self):
        """Attribute read handler for DishManager band3PointingModelParams"""
        return self._band3_pointing_model_params

    def read_band4PointingModelParams(self):
        """Attribute read handler for DishManager band4PointingModelParams"""
        return self._band4_pointing_model_params

    def read_band5aPointingModelParams(self):
        """Attribute read handler for DishManager band5aPointingModelParams"""
        return self._band5a_pointing_model_params

    def read_band5bPointingModelParams(self):
        """Attribute read handler for DishManager band5bPointingModelParams"""
        return self._band5b_pointing_model_params

    def read_trackProgramMode(self):
        """Attribute read handler for DishManager trackProgramMode"""
        return self._track_program_mode

    def read_trackTableLoadMode(self):
        """Attribute read handler for DishManager trackTableLoadMode"""
        return self._track_table_load_mode

    def read_synchronised(self):
        """Attribute read handler for DishManager synchronised"""
        return self._synchronised

    def read_usageStatus(self):
        """Attribute read handler for DishManager usageStatus"""
        return self._usage_status

    def read_band1SamplerFrequency(self):
        """Attribute read handler for DishManager band1SamplerFrequency"""
        return self._band1_sampler_frequency

    def read_band2SamplerFrequency(self):
        """Attribute read handler for DishManager band2SamplerFrequency"""
        return self._band2_sampler_frequency

    def read_band3SamplerFrequency(self):
        """Attribute read handler for DishManager band3SamplerFrequency"""
        return self._band3_sampler_frequency

    def read_band4SamplerFrequency(self):
        """Attribute read handler for DishManager band4SamplerFrequency"""
        return self._band4_sampler_frequency

    def read_band5aSamplerFrequency(self):
        """Attribute read handler for DishManager band5aSamplerFrequency"""
        return self._band5a_sampler_frequency

    def read_band5bSamplerFrequency(self):
        """Attribute read handler for DishManager band5bSamplerFrequency"""
        return self._band5b_sampler_frequency

    def read_capturing(self):
        """Attribute read handler for DishManager capturing"""
        return self._capturing

    def read_configuredBand(self):
        """Attribute read handler for DishManager configuredBand"""
        return self._configured_band

    def read_configureTargetLock(self):
        """Attribute read handler for DishManager configureTargetLock"""
        return self._configure_target_lock

    def read_trackInterpolationMode(self):
        """Attribute read handler for DishManager trackInterpolationMode"""
        return self._track_interpolation_mode

    def read_desiredPointing(self):
        """Attribute read handler for DishManager desiredPointing"""
        return self._desired_pointing

    def read_dishMode(self):
        """Attribute read handler for DishManager dishMode"""
        return self._dish_mode

    def read_dshMaxShortTermPower(self):
        """Attribute read handler for DishManager dshMaxShortTermPower"""
        return self._dsh_max_short_term_power

    def read_dshPowerCurtailment(self):
        """Attribute read handler for DishManager dshPowerCurtailment"""
        return self._dsh_power_curtailment

    def read_frequencyResponse(self):
        """Attribute read handler for DishManager frequencyResponse"""
        return self._frequency_response

    def read_noiseDiodeConfig(self):
        """Attribute read handler for DishManager noiseDiodeConfig"""
        return self._noise_diode_config

    def read_pointingState(self):
        """Attribute read handler for DishManager pointingState"""
        return self._pointing_state

    def read_pointingBufferSize(self):
        """Attribute read handler for DishManager pointingBufferSize"""
        return self._pointing_buffer_size

    def read_polyTrack(self):
        """Attribute read handler for DishManager polyTrack"""
        return self._poly_track

    def read_powerState(self):
        """Attribute read handler for DishManager powerState"""
        return self._power_state

    def read_programTrackTable(self):
        """Attribute read handler for DishManager programTrackTable"""
        return self._program_track_table

    def write_trackProgramMode(self, value):
        """Attribute write handler for DishManager trackProgramMode"""
        # pylint: disable=attribute-defined-outside-init
        self._track_program_mode = value

    def write_attenuationPolH(self, value):
        """Attribute write handler for DishManager attenuationPolH"""
        # pylint: disable=attribute-defined-outside-init
        self._attenuation_pol_h = value

    def write_attenuationPolV(self, value):
        """Attribute write handler for DishManager attenuationPolV("""
        # pylint: disable=attribute-defined-outside-init
        self._attenuation_pol_v = value

    def write_band1PointingModelParams(self, value):
        """Attribute write handler for DishManager band1PointingModelParams"""
        # pylint: disable=attribute-defined-outside-init
        self._band1_pointing_model_params = value

    def write_band2PointingModelParams(self, value):
        """Attribute write handler for DishManager band2PointingModelParams"""
        # pylint: disable=attribute-defined-outside-init
        self._band2_pointing_model_params = value

    def write_band3PointingModelParams(self, value):
        """Attribute write handler for DishManager band3PointingModelParams"""
        # pylint: disable=attribute-defined-outside-init
        self._band3_pointing_model_params = value

    def write_band4PointingModelParams(self, value):
        """Attribute write handler for DishManager band4PointingModelParams"""
        # pylint: disable=attribute-defined-outside-init
        self._band4_pointing_model_params = value

    def write_band5aPointingModelParams(self, value):
        """Attribute write handler for DishManager band5aPointingModelParams"""
        # pylint: disable=attribute-defined-outside-init
        self._band5a_pointing_model_params = value

    def write_band5bPointingModelParams(self, value):
        """Attribute write handler for DishManager band5bPointingModelParams"""
        # pylint: disable=attribute-defined-outside-init
        self._band5b_pointing_model_params = value

    def write_band1SamplerFrequency(self, value):
        """Attribute write handler for DishManager band1SamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band1_sampler_frequency = value

    def write_band2SamplerFrequency(self, value):
        """Attribute write handler for DishManager band2SamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band2_sampler_frequency = value

    def write_band3SamplerFrequency(self, value):
        """Attribute write handler for DishManager band3SamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band3_sampler_frequency = value

    def write_band4SamplerFrequency(self, value):
        """Attribute write handler for DishManager band4SamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band4_sampler_frequency = value

    def write_band5aSamplerFrequency(self, value):
        """Attribute write handler for DishManager band5aSamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band5a_sampler_frequency = value

    def write_band5bSamplerFrequency(self, value):
        """Attribute write handler for DishManager band5bSamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band5b_sampler_frequency = value

    def write_configureTargetLock(self, value):
        """Attribute write handler for DishManager configureTargetLock"""
        # pylint: disable=attribute-defined-outside-init
        self._configure_target_lock = value

    def write_desiredPointing(self, value):
        """Attribute write handler for DishManager desiredPointing"""
        # pylint: disable=attribute-defined-outside-init
        self._desired_pointing = value

    def write_dshMaxShortTermPower(self, value):
        """Attribute write handler for DishManager dshMaxShortTermPower"""
        # pylint: disable=attribute-defined-outside-init
        self._dsh_max_short_term_power = value

    def write_noiseDiodeConfig(self, value):
        """Attribute write handler for DishManager noiseDiodeConfig"""
        # pylint: disable=attribute-defined-outside-init
        self._noise_diode_config = value

    def write_dshPowerCurtailment(self, value):
        """Attribute write handler for DishManager dshPowerCurtailment"""
        # pylint: disable=attribute-defined-outside-init
        self._dsh_power_curtailment = value

    def write_polyTrack(self, value):
        """Attribute write handler for DishManager polyTrack"""
        # pylint: disable=attribute-defined-outside-init
        self._poly_track = value

    def write_programTrackTable(self, value):
        """Attribute write handler for DishManager programTrackTable"""
        # pylint: disable=attribute-defined-outside-init
        self._program_track_table = value

    def write_trackInterpolationMode(self, value):
        """Attribute write handler for DishManager trackInterpolationMode"""
        # pylint: disable=attribute-defined-outside-init
        self._track_interpolation_mode = value

    def write_trackTableLoadMode(self, value):
        """Attribute write handler for DishManager trackTableLoadMode"""
        # pylint: disable=attribute-defined-outside-init
        self._track_table_load_mode = value

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

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def SetOperateMode(self):
        """
        This command triggers the Dish to transition to the OPERATE Dish
        Element Mode, and returns to the caller. This mode fulfils the main
        purpose of the Dish, which is to point to designated directions while
        capturing data and transmitting it to CSP. The Dish will automatically
        start capturing data after entering OPERATE mode.
        """
        handler = self.get_command_object("SetOperateMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def SetStandbyLPMode(self):
        """
        This command triggers the Dish to transition to the STANDBY‐LP Dish
        Element Mode, and returns to the caller. Standby_LP is the default
        mode when the Dish is configured for low power consumption, and is
        the mode wherein Dish ends after a start-up procedure.
        All subsystems go into a low power state to power only the essential
        equipment. Specifically the Helium compressor will be set to a low
        power consumption, and the drives will be disabled. When issued a
        STOW command while in LOW power, the DS controller should be
        able to turn the drives on, stow the dish and turn the drives off
        again. The purpose of this mode is to enable the observatory to
        perform power management (load curtailment), and also to conserve
        energy for non‐operating dishes.
        """
        handler = self.get_command_object("SetStandbyLPMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def SetStandbyFPMode(self):
        """
        This command triggers the Dish to transition to the STANDBY‐FP Dish
        Element Mode, and returns to the caller.
        To prepare all subsystems for active observation, once a command is
        received by TM to go to the FULL_POWER mode.
        """
        handler = self.get_command_object("SetStandbyFPMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def SetStowMode(self):
        """
        This command triggers the Dish to transition to the STOW Dish Element
        Mode, and returns to the caller. To point the dish in a direction that
        minimises the wind loads on the structure, for survival in strong wind
        conditions. The Dish is able to observe in the STOW position, for the
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
        """Capture data from the CBF"""
        return

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def StopCapture(self):
        """Stop capturing data"""
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
        Track data source (TABLE-A, TABLE-B, POLY) used for tracking is pre‐
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
    """Launch an DishManager device."""
    return run((DishManager,), args=args, **kwargs)


if __name__ == "__main__":
    main()
