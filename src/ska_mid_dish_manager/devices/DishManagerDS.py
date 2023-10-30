# pylint: disable=invalid-name
# pylint: disable=C0302,W0212
"""
This module implements the dish manager device for DishLMC.

It exposes the attributes and commands which control the dish
and the subservient devices
"""

import json
import logging
import os
import weakref
from functools import reduce
from typing import List, Optional, Tuple

import tango
from ska_control_model import CommunicationStatus, ResultCode
from ska_tango_base import SKAController
from ska_tango_base.commands import SlowCommand, SubmittedSlowCommand
from tango import (
    AttrWriteType,
    Database,
    DbDevInfo,
    DebugIt,
    DevFloat,
    DevVarDoubleArray,
    DispLevel,
)
from tango.server import attribute, command, device_property, run

from ska_mid_dish_manager.component_managers.dish_manager_cm import DishManagerComponentManager
from ska_mid_dish_manager.models.dish_enums import (
    Band,
    CapabilityStates,
    DishMode,
    PointingState,
    PowerState,
    TrackInterpolationMode,
    TrackProgramMode,
    TrackTableLoadMode,
)

DevVarLongStringArrayType = Tuple[List[ResultCode], List[Optional[str]]]


# pylint: disable=too-many-instance-attributes
# pylint: disable=too-many-public-methods
class DishManager(SKAController):
    """
    The Dish Manager of the Dish LMC subsystem
    """

    # Access instances for debugging
    instances = weakref.WeakValueDictionary()

    # -----------------
    # Device Properties
    # -----------------
    # these values will be overwritten by values in
    # /charts/ska-mid-dish-manager/data in k8s deployment
    DSDeviceFqdn = device_property(dtype=str, default_value="ska001/ds/manager")
    SPFDeviceFqdn = device_property(dtype=str, default_value="ska001/spf/simulator")
    SPFRxDeviceFqdn = device_property(dtype=str, default_value="ska001/spfrx/simulator")
    DishId = device_property(dtype=str, default_value="SKA001")

    def create_component_manager(self):
        """Create the component manager for DishManager

        :return: Instance of DishManagerComponentManager
        :rtype: DishManagerComponentManager
        """
        return DishManagerComponentManager(
            self.logger,
            self._command_tracker,
            self._update_connection_state_attrs,
            self.DSDeviceFqdn,
            self.SPFDeviceFqdn,
            self.SPFRxDeviceFqdn,
            communication_state_callback=None,
            component_state_callback=self._component_state_changed,
        )

    def init_command_objects(self) -> None:
        """Initialise the command handlers"""
        super().init_command_objects()

        for command_name, method_name in [
            ("SetStandbyLPMode", "set_standby_lp_mode"),
            ("SetOperateMode", "set_operate_mode"),
            ("SetStandbyFPMode", "set_standby_fp_mode"),
            ("Track", "track_cmd"),
            ("TrackStop", "track_stop_cmd"),
            ("ConfigureBand1", "configure_band_cmd"),
            ("ConfigureBand2", "configure_band_cmd"),
            ("SetStowMode", "set_stow_mode"),
            ("SetKValue", "set_kvalue"),
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

        self.register_command_object(
            "AbortCommands",
            self.AbortCommandsCommand(self.component_manager, self.logger),
        )

    def _update_connection_state_attrs(self, attribute_name: str):
        """
        Push change events on connection state attributes for
        subservient devices communication state changes.
        """

        if not hasattr(self, "component_manager"):
            self.logger.warning("Init not completed, but communication state is being updated")
            return
        if attribute_name == "spfConnectionState":
            self.push_change_event(
                "spfConnectionState",
                self.component_manager.sub_component_managers["SPF"].communication_state,
            )
        if attribute_name == "spfrxConnectionState":
            self.push_change_event(
                "spfrxConnectionState",
                self.component_manager.sub_component_managers["SPFRX"].communication_state,
            )
        if attribute_name == "dsConnectionState":
            self.push_change_event(
                "dsConnectionState",
                self.component_manager.sub_component_managers["DS"].communication_state,
            )

    # pylint: disable=unused-argument
    def _component_state_changed(self, *args, **kwargs):
        if not hasattr(self, "_component_state_attr_map"):
            self.logger.warning("Init not completed, but state is being updated [%s]", kwargs)
            return

        def change_case(attr_name):
            """Convert camel case string to snake case

            The snake case output is prefixed by an underscore to
            match the naming convention of the attribute variables.

            Example:
            dishMode > _dish_mode
            capture > _capture
            b3CapabilityState > _b3_capability_state

            Source: https://www.geeksforgeeks.org/
            python-program-to-convert-camel-case-string-to-snake-case/
            """
            # pylint: disable=line-too-long
            return f"_{reduce(lambda x, y: x + ('_' if y.isupper() else '') + y, attr_name).lower()}"  # noqa: E501

        for comp_state_name, comp_state_value in kwargs.items():
            attribute_name = self._component_state_attr_map.get(comp_state_name, comp_state_name)
            attribute_variable = change_case(attribute_name)
            setattr(self, attribute_variable, comp_state_value)
            self.push_change_event(attribute_name, comp_state_value)

    class InitCommand(SKAController.InitCommand):  # pylint: disable=too-few-public-methods
        """
        A class for the Dish Manager's init_device() method
        """

        # pylint: disable=invalid-name
        # pylint: disable=too-many-statements
        # pylint: disable=arguments-differ
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
            device._dish_mode = DishMode.UNKNOWN
            device._dsh_max_short_term_power = 13.5
            device._dsh_power_curtailment = True
            device._frequency_response = [[], []]
            device._noise_diode_config = []
            device._pointing_buffer_size = 0
            device._pointing_state = PointingState.UNKNOWN
            device._poly_track = []
            device._power_state = PowerState.LOW
            device._program_track_table = []
            device._track_interpolation_mode = TrackInterpolationMode.NEWTON
            device._track_program_mode = TrackProgramMode.TABLEA
            device._track_table_load_mode = TrackTableLoadMode.ADD

            device._b1_capability_state = CapabilityStates.UNKNOWN
            device._b2_capability_state = CapabilityStates.UNKNOWN
            device._b3_capability_state = CapabilityStates.UNKNOWN
            device._b4_capability_state = CapabilityStates.UNKNOWN
            device._b5a_capability_state = CapabilityStates.UNKNOWN
            device._b5b_capability_state = CapabilityStates.UNKNOWN

            device._spf_connection_state = CommunicationStatus.NOT_ESTABLISHED
            device._spfrx_connection_state = CommunicationStatus.NOT_ESTABLISHED
            device._ds_connection_state = CommunicationStatus.NOT_ESTABLISHED

            device.op_state_model.perform_action("component_standby")

            # push change events, needed to use testing library

            device._component_state_attr_map = {
                "dishmode": "dishMode",
                "pointingstate": "pointingState",
                "configuredband": "configuredBand",
                "achievedtargetlock": "achievedTargetLock",
                "healthstate": "healthState",
                "b1capabilitystate": "b1CapabilityState",
                "b2capabilitystate": "b2CapabilityState",
                "b3capabilitystate": "b3CapabilityState",
                "b4capabilitystate": "b4CapabilityState",
                "b5acapabilitystate": "b5aCapabilityState",
                "b5bcapabilitystate": "b5bCapabilityState",
                "achievedpointing": "achievedPointing",
                "band2pointingmodelparams": "band2PointingModelParams",
                "attenuationpolh": "attenuationPolH",
                "attenuationpolv": "attenuationPolV",
                "kvalue": "kValue",
            }
            for attr in device._component_state_attr_map.values():
                device.set_change_event(attr, True, False)

            # configure change events for the connection state attributes
            for attr in (
                "spfConnectionState",
                "spfrxConnectionState",
                "dsConnectionState",
            ):
                device.set_change_event(attr, True, False)

            device.instances[device.get_name()] = device
            (result_code, message) = super().do()
            device.component_manager.start_communicating()
            return (ResultCode(result_code), message)

    # ----------
    # Attributes
    # ----------

    # pylint: disable=invalid-name
    @attribute(
        dtype=CommunicationStatus,
        access=AttrWriteType.READ,
        doc="Displays connection status to SPF device",
    )
    def spfConnectionState(self):
        """Returns the spf connection state"""
        return self.component_manager.sub_component_managers["SPF"].communication_state

    @attribute(
        dtype=CommunicationStatus,
        access=AttrWriteType.READ,
        doc="Displays connection status to SPFRx device",
    )
    def spfrxConnectionState(self):
        """Returns the spfrx connection state"""
        return self.component_manager.sub_component_managers["SPFRX"].communication_state

    @attribute(
        dtype=CommunicationStatus,
        access=AttrWriteType.READ,
        doc="Displays connection status to DS device",
    )
    def dsConnectionState(self):
        """Returns the ds connection state"""
        return self.component_manager.sub_component_managers["DS"].communication_state

    @attribute(
        max_dim_x=3,
        dtype=(float,),
        doc="[0] Timestamp\n[1] Azimuth\n[2] Elevation",
    )
    def achievedPointing(self):
        """Returns the achievedPointing"""
        return self._achieved_pointing

    @attribute(
        dtype=bool,
        doc="Indicates whether the Dish is on target or not based on the "
        "pointing error and time period parameters defined in "
        "configureTargetLock.",
    )
    def achievedTargetLock(self):
        """Returns the achievedTargetLock"""
        return self._achieved_target_lock

    @attribute(
        dtype=DevFloat,
        access=AttrWriteType.READ_WRITE,
        doc="Indicates the SPFRx attenuation in the horizontal "
        "signal chain for the configuredband.",
    )
    def attenuationPolH(self):
        """Returns the attenuationPolH"""
        return self._attenuation_pol_h

    @attenuationPolH.write
    def attenuationPolH(self, value):
        """Set the attenuationPolH"""
        # pylint: disable=attribute-defined-outside-init
        self._attenuation_pol_h = value
        spfrx_cm = self.component_manager.sub_component_managers["SPFRX"]
        spfrx_cm.write_attribute_value("attenuationPolH", value)

    @attribute(
        dtype=DevFloat,
        access=AttrWriteType.READ_WRITE,
        doc="Indicates the SPFRx attenuation in the vertical "
        "signal chain for the configuredband.",
    )
    def attenuationPolV(self):
        """Returns the attenuationPolV"""
        return self._attenuation_pol_v

    @attenuationPolV.write
    def attenuationPolV(self, value):
        """Set the attenuationPolV("""
        # pylint: disable=attribute-defined-outside-init
        self._attenuation_pol_v = value
        spfrx_cm = self.component_manager.sub_component_managers["SPFRX"]
        spfrx_cm.write_attribute_value("attenuationPolV", value)

    @attribute(
        dtype=int,
        access=AttrWriteType.READ,
        doc="Returns the kValue for SPFRX",
    )
    def kvalue(self):
        """Returns the kValue for SPFRX"""
        return self.component_manager.component_state["kvalue"]

    @attribute(
        dtype=bool,
        doc="Indicates that the Dish has moved beyond an azimuth wrap limit.",
    )
    def azimuthOverWrap(self):
        """Returns the azimuthOverWrap"""
        return self._azimuth_over_wrap

    @attribute(
        dtype=(DevFloat,),
        max_dim_x=5,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 1 pointing models used by Dish to do "
        "pointing corrections.",
    )
    def band1PointingModelParams(self):
        """Returns the band1PointingModelParams"""
        return self._band1_pointing_model_params

    @band1PointingModelParams.write
    def band1PointingModelParams(self, value):
        """Set the band1PointingModelParams"""
        # pylint: disable=attribute-defined-outside-init
        self._band1_pointing_model_params = value

    @attribute(
        dtype=(DevFloat,),
        max_dim_x=20,
        access=AttrWriteType.READ_WRITE,
        doc="""
            Parameters for (local) Band 2 pointing models used by Dish to do pointing corrections.

            Band 2 pointing model parameters are:
            [0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
            [9] ABA, [10] ABphi, [11] CAobs, [12] IE, [13] ECEC, [14] ECES, [15] HECE4,
            [16] HESE4, [17] HECE8, [18] HESE8, [19] Eobs

            When writing we expect a list of 2 values. Namely, CAobs and Eobs. Only those two
            values will be updated.
        """,
    )
    def band2PointingModelParams(self):
        """Returns the band2PointingModelParams"""
        return self._band2_pointing_model_params

    @band2PointingModelParams.write
    def band2PointingModelParams(self, value):
        """Set the band2PointingModelParams"""
        self.logger.debug("band2PointingModelParams write method called with params %s", value)

        # The argument value is a list of two floats: [off_xel, off_el]
        if len(value) != 2:
            raise ValueError(f"Length of argument ({len(value)}) is not as expected (2).")

        ds_proxy = tango.DeviceProxy(self.DSDeviceFqdn)
        ds_proxy.band2PointingModelParams = value

    @attribute(
        dtype=(DevFloat,),
        max_dim_x=5,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 3 pointing models used by Dish to do "
        "pointing corrections.",
    )
    def band3PointingModelParams(self):
        """Returns the band3PointingModelParams"""
        return self._band3_pointing_model_params

    @band3PointingModelParams.write
    def band3PointingModelParams(self, value):
        """Set the band3PointingModelParams"""
        # pylint: disable=attribute-defined-outside-init
        self._band3_pointing_model_params = value

    @attribute(
        dtype=(DevFloat,),
        max_dim_x=5,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 4 pointing models used by Dish to do "
        "pointing corrections.",
    )
    def band4PointingModelParams(self):
        """Returns the band4PointingModelParams"""
        return self._band4_pointing_model_params

    @band4PointingModelParams.write
    def band4PointingModelParams(self, value):
        """Set the band4PointingModelParams"""
        # pylint: disable=attribute-defined-outside-init
        self._band4_pointing_model_params = value

    @attribute(
        dtype=(DevFloat,),
        max_dim_x=5,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 5a pointing models used by Dish to "
        "do pointing corrections.",
    )
    def band5aPointingModelParams(self):
        """Returns the band5aPointingModelParams"""
        return self._band5a_pointing_model_params

    @band5aPointingModelParams.write
    def band5aPointingModelParams(self, value):
        """Set the band5aPointingModelParams"""
        # pylint: disable=attribute-defined-outside-init
        self._band5a_pointing_model_params = value

    @attribute(
        dtype=(DevFloat,),
        max_dim_x=5,
        access=AttrWriteType.READ_WRITE,
        doc="Parameters for (local) Band 5b pointing models used by Dish to "
        "do pointing corrections.",
    )
    def band5bPointingModelParams(self):
        """Returns the band5bPointingModelParams"""
        return self._band5b_pointing_model_params

    @band5bPointingModelParams.write
    def band5bPointingModelParams(self, value):
        """Set the band5bPointingModelParams"""
        # pylint: disable=attribute-defined-outside-init
        self._band5b_pointing_model_params = value

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND1 absolute sampler clock frequency (base plus offset).",
    )
    def band1SamplerFrequency(self):
        """Returns the band1SamplerFrequency"""
        return self._band1_sampler_frequency

    @band1SamplerFrequency.write
    def band1SamplerFrequency(self, value):
        """Set the band1SamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band1_sampler_frequency = value

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND2 absolute sampler clock frequency (base plus offset).",
    )
    def band2SamplerFrequency(self):
        """Returns the band2SamplerFrequency"""
        return self._band2_sampler_frequency

    @band2SamplerFrequency.write
    def band2SamplerFrequency(self, value):
        """Set the band2SamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band2_sampler_frequency = value

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND3 absolute sampler clock frequency (base plus offset).",
    )
    def band3SamplerFrequency(self):
        """Returns the band3SamplerFrequency"""
        return self._band3_sampler_frequency

    @band3SamplerFrequency.write
    def band3SamplerFrequency(self, value):
        """Set the band3SamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band3_sampler_frequency = value

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND4 absolute sampler clock frequency (base plus offset).",
    )
    def band4SamplerFrequency(self):
        """Returns the band4SamplerFrequency"""
        return self._band4_sampler_frequency

    @band4SamplerFrequency.write
    def band4SamplerFrequency(self, value):
        """Set the band4SamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band4_sampler_frequency = value

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND5a absolute sampler clock frequency (base plus offset).",
    )
    def band5aSamplerFrequency(self):
        """Returns the band5aSamplerFrequency"""
        return self._band5a_sampler_frequency

    @band5aSamplerFrequency.write
    def band5aSamplerFrequency(self, value):
        """Set the band5aSamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band5a_sampler_frequency = value

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="BAND5b absolute sampler clock frequency (base plus offset).",
    )
    def band5bSamplerFrequency(self):
        """Returns the band5bSamplerFrequency"""
        return self._band5b_sampler_frequency

    @band5bSamplerFrequency.write
    def band5bSamplerFrequency(self, value):
        """Set the band5bSamplerFrequency"""
        # pylint: disable=attribute-defined-outside-init
        self._band5b_sampler_frequency = value

    @attribute(
        dtype=bool,
        doc="Indicates whether Dish is capturing data in the configured band " "or not.",
    )
    def capturing(self):
        """Returns the capturing"""
        return self._capturing

    @attribute(
        dtype=Band,
        doc="The frequency band that the Dish is configured to capture data " "in.",
    )
    def configuredBand(self):
        """Returns the configuredBand"""
        return self._configured_band

    @attribute(
        dtype=(float,),
        max_dim_x=2,
        access=AttrWriteType.WRITE,
        doc="[0] Pointing error\n[1] Time period",
    )
    def configureTargetLock(self):
        """Returns the configureTargetLock"""
        return self._configure_target_lock

    @configureTargetLock.write
    def configureTargetLock(self, value):
        """Set the configureTargetLock"""
        # pylint: disable=attribute-defined-outside-init
        self._configure_target_lock = value

    @attribute(max_dim_x=3, dtype=(float,), access=AttrWriteType.READ_WRITE)
    def desiredPointing(self):
        """Returns the desiredPointing"""
        return self._desired_pointing

    @desiredPointing.write
    def desiredPointing(self, value):
        """Set the desiredPointing"""
        # pylint: disable=attribute-defined-outside-init
        self._desired_pointing = value
        ds_cm = self.component_manager.sub_component_managers["DS"]
        ds_cm.write_attribute_value("desiredPointing", value)

    @attribute(
        dtype=DishMode,
        doc="Dish rolled-up operating mode in Dish Control Model (SCM) notation",
    )
    def dishMode(self):
        """Returns the dishMode"""
        return self._dish_mode

    @attribute(
        dtype=float,
        access=AttrWriteType.WRITE,
        doc="Configures the Max Short Term Average Power (5sec‐10min) in "
        "kilowatt that the DSH instance is curtailed to while "
        "dshPowerCurtailment is [TRUE]. The default value is 13.5.",
    )
    def dshMaxShortTermPower(self):
        """Returns the dshMaxShortTermPower"""
        return self._dsh_max_short_term_power

    @dshMaxShortTermPower.write
    def dshMaxShortTermPower(self, value):
        """Set the dshMaxShortTermPower"""
        # pylint: disable=attribute-defined-outside-init
        self._dsh_max_short_term_power = value

    @attribute(
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
    def dshPowerCurtailment(self):
        """Returns the dshPowerCurtailment"""
        return self._dsh_power_curtailment

    @dshPowerCurtailment.write
    def dshPowerCurtailment(self, value):
        """Set the dshPowerCurtailment"""
        # pylint: disable=attribute-defined-outside-init
        self._dsh_power_curtailment = value

    @attribute(dtype=(((float),),), max_dim_x=1024, max_dim_y=1024)
    def frequencyResponse(self):
        """Returns the frequencyResponse"""
        return self._frequency_response

    @attribute(dtype=(DevFloat,), access=AttrWriteType.WRITE)
    def noiseDiodeConfig(self):
        """Returns the noiseDiodeConfig"""
        return self._noise_diode_config

    @noiseDiodeConfig.write
    def noiseDiodeConfig(self, value):
        """Set the noiseDiodeConfig"""
        # pylint: disable=attribute-defined-outside-init
        self._noise_diode_config = value

    @attribute(dtype=PointingState)
    def pointingState(self):
        """Returns the pointingState"""
        return self._pointing_state

    @attribute(
        dtype=(float,),
        max_dim_x=150,
        access=AttrWriteType.READ_WRITE,
        doc="Timestamp of i‐th coordinate in table (max 50 coordinates) given "
        "in milliseconds since UNIX epoch, UTC, representing time at which "
        "Dish should track i‐th coordinate.\n Azimuth of i‐th coordinate in "
        "table (max 50 coordinates) given in degrees.\n Elevation of i‐th "
        "coordinate in table (max 50 coordinates) given in degrees",
    )
    def programTrackTable(self):
        """Returns the programTrackTable"""
        return self._program_track_table

    @programTrackTable.write
    def programTrackTable(self, value):
        """Set the programTrackTable"""
        # pylint: disable=attribute-defined-outside-init
        self._program_track_table = value

    @attribute(
        dtype=int,
        doc="Number of desiredPointing write values that the buffer has space "
        "for.\nNote: desiredPointing write values are stored by Dish in a "
        "buffer for application at the time specified in each desiredPointing "
        "record.",
    )
    def pointingBufferSize(self):
        """Returns the pointingBufferSize"""
        return self._pointing_buffer_size

    @attribute(
        dtype=(float,),
        max_dim_x=9,
        access=AttrWriteType.WRITE,
        doc="[0] Timestamp\n[1] Azimuth\n[2] Elevation\n[3] Azimuth speed\n"
        "[4] Elevation speed\n[5] Azimuth acceleration\n"
        "[6] Elevation acceleration\n[7] Azimuth jerk\n[8] Elevation jerk",
    )
    def polyTrack(self):
        """Returns the polyTrack"""
        return self._poly_track

    @polyTrack.write
    def polyTrack(self, value):
        """Set the polyTrack"""
        # pylint: disable=attribute-defined-outside-init
        self._poly_track = value

    @attribute(dtype=PowerState)
    def powerState(self):
        """Returns the powerState"""
        return self._power_state

    @attribute(
        dtype=TrackInterpolationMode,
        access=AttrWriteType.READ_WRITE,
        doc="Selects the type of interpolation to be used in program " "tracking.",
    )
    def trackInterpolationMode(self):
        """Returns the trackInterpolationMode"""
        return self._track_interpolation_mode

    @trackInterpolationMode.write
    def trackInterpolationMode(self, value):
        """Set the trackInterpolationMode"""
        # pylint: disable=attribute-defined-outside-init
        self._track_interpolation_mode = value

    @attribute(
        dtype=TrackProgramMode,
        access=AttrWriteType.READ_WRITE,
        doc="Selects the track program source (table A, table B, polynomial "
        "stream) used in the ACU for tracking. Coordinates given in the "
        "programTrackTable attribute are loaded in ACU in the selected table.",
    )
    def trackProgramMode(self):
        """Returns the trackProgramMode"""
        return self._track_program_mode

    @trackProgramMode.write
    def trackProgramMode(self, value):
        """Set the trackProgramMode"""
        # pylint: disable=attribute-defined-outside-init
        self._track_program_mode = value

    @attribute(
        dtype=TrackTableLoadMode,
        access=AttrWriteType.READ_WRITE,
        doc="Selects track table load mode.\nWith ADD selected, Dish will "
        "add the coordinate set given in programTrackTable attribute to the "
        "list of pointing coordinates already loaded in ACU.\nWith NEW "
        "selected, Dish will delete the list of pointing coordinates "
        "previously loaded in ACU when new coordinates are given in the "
        "programTrackTable attribute.",
    )
    def trackTableLoadMode(self):
        """Returns the trackTableLoadMode"""
        return self._track_table_load_mode

    @trackTableLoadMode.write
    def trackTableLoadMode(self, value):
        """Set the trackTableLoadMode"""
        # pylint: disable=attribute-defined-outside-init
        self._track_table_load_mode = value

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b1CapabilityState",
    )
    def b1CapabilityState(self):
        """Returns the b1CapabilityState"""
        return self._b1_capability_state

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b2CapabilityState",
    )
    def b2CapabilityState(self):
        """Returns the b2CapabilityState"""
        return self._b2_capability_state

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b3CapabilityState",
    )
    def b3CapabilityState(self):
        """Returns the b3CapabilityState"""
        return self._b3_capability_state

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b4CapabilityState",
    )
    def b4CapabilityState(self):
        """Returns the b4CapabilityState"""
        return self._b4_capability_state

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b5aCapabilityState",
    )
    def b5aCapabilityState(self):
        """Returns the b5aCapabilityState"""
        return self._b5a_capability_state

    @attribute(
        dtype=CapabilityStates,
        access=AttrWriteType.READ,
        doc="Report the device b5bCapabilityState",
    )
    def b5bCapabilityState(self):
        """Returns the b5aCapabilityState"""
        return self._b5b_capability_state

    # --------
    # Commands
    # --------

    # pylint: disable=too-few-public-methods
    class AbortCommandsCommand(SlowCommand):
        """The command class for the AbortCommand command."""

        def __init__(
            self,
            component_manager: DishManagerComponentManager,
            logger: Optional[logging.Logger] = None,
        ) -> None:
            """
            Initialise a new AbortCommandsCommand instance.

            :param component_manager: contains the queue manager which
                manages the worker thread and the LRC attributes
            :param logger: the logger to be used by this Command. If not
                provided, then a default module logger will be used.
            """
            self._component_manager = component_manager
            super().__init__(None, logger=logger)

        # pylint: disable=arguments-differ
        def do(self) -> Tuple[ResultCode, str]:  # type: ignore[override]
            """
            Abort long running commands.

            Abort the currently executing LRC and remove all enqueued
            LRCs.

            :return: A tuple containing a return code and a string
                message indicating status. The message is for
                information purpose only.
            """
            # abort the task on dish manager
            self._component_manager.abort_commands()
            # abort the task on the subservient devices
            for cm in self._component_manager.sub_component_managers.values():
                cm.abort_commands()

            return (ResultCode.STARTED, "Aborting commands")

    @command(
        doc_in="Abort currently executing long running command on "
        "DishManager and subservient devices. Empties out the queue "
        "on DishManager and rejects any scheduled commands. For "
        "details consult DishManager documentation",
        display_level=DispLevel.OPERATOR,
        dtype_out="DevVarLongStringArray",
    )
    @DebugIt()
    def AbortCommands(self) -> DevVarLongStringArrayType:
        """
        Empty out long running commands in queue.

        :return: A tuple containing a return code and a string
            message indicating status. The message is for
            information purpose only.
        """
        handler = self.get_command_object("AbortCommands")
        (return_code, message) = handler()
        return ([return_code], [message])

    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand1(self, synchronise) -> DevVarLongStringArrayType:
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 1. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("ConfigureBand1")

        result_code, unique_id = handler("1", synchronise)
        return ([result_code], [unique_id])

    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand2(self, synchronise) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 2. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("ConfigureBand2")

        result_code, unique_id = handler("2", synchronise)
        return ([result_code], [unique_id])

    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand3(self, synchronise):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 3. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        raise NotImplementedError

    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand4(self, synchronise):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 4. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        raise NotImplementedError

    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand5a(self, synchronise):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 5a. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        raise NotImplementedError

    @command(
        dtype_in=bool,
        doc_in="If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise "
        "its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band "
        "being configured, and the band counters are reset. (Should be default to False).",
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def ConfigureBand5b(self, synchronise):  # pylint: disable=unused-argument
        """
        This command triggers the Dish to transition to the CONFIG Dish
        Element Mode, and returns to the caller. To configure the Dish to
        operate in frequency band 5b. On completion of the band
        configuration, Dish will automatically revert to the previous Dish
        mode (OPERATE or STANDBY‐FP).
        """
        raise NotImplementedError

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def FlushCommandQueue(self):
        """Flushes the queue of time stamped commands."""
        raise NotImplementedError

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def Scan(self):
        """
        The Dish is tracking the commanded pointing positions within the
        specified SCAN pointing accuracy. (TBC14)
        NOTE: This pointing state is currently proposed and there are
        currently no requirements for this functionality.
        """
        raise NotImplementedError

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
        raise NotImplementedError

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def SetOperateMode(self) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

        This command triggers the Dish to transition to the OPERATE Dish
        Element Mode, and returns to the caller. This mode fulfils the main
        purpose of the Dish, which is to point to designated directions while
        capturing data and transmitting it to CSP. The Dish will automatically
        start capturing data after entering OPERATE mode.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("SetOperateMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def SetStandbyLPMode(self) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

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

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("SetStandbyLPMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def SetStandbyFPMode(self) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

        This command triggers the Dish to transition to the STANDBY‐FP Dish
        Element Mode, and returns to the caller.
        To prepare all subsystems for active observation, once a command is
        received by TM to go to the FULL_POWER mode.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("SetStandbyFPMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def SetStowMode(self) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

        This command triggers the Dish to transition to the STOW Dish Element
        Mode, and returns to the caller. To point the dish in a direction that
        minimises the wind loads on the structure, for survival in strong wind
        conditions. The Dish is able to observe in the STOW position, for the
        purpose of transient detection.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("SetStowMode")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

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
        raise NotImplementedError

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def Synchronise(self):
        """
        Reset configured band sample counters. Command only valid in
        SPFRx Data_Capture mode.
        """
        raise NotImplementedError

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def Track(self) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

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
        1. trackInterpolationMode: to select type of
        interpolation, Newton (default) or Spline.
        2. programTrackTable: to load program table data
        (Az,El,timestamp sets) on selected ACU table
        3. trackTableLoadMode: to add/append new track table data

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("Track")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @command(
        dtype_in=None,
        dtype_out="DevVarLongStringArray",
        display_level=DispLevel.OPERATOR,
    )
    def TrackStop(self) -> DevVarLongStringArrayType:
        """
        Implemented as a Long Running Command

        When the TrackStop command Is received the Dish will stop tracking
        but will not apply brakes.

        :return: A tuple containing a return code and a string
            message indicating status.
        """
        handler = self.get_command_object("TrackStop")
        result_code, unique_id = handler()

        return ([result_code], [unique_id])

    @command(
        dtype_in="DevLong64",
        dtype_out="DevVoid",
        display_level=DispLevel.OPERATOR,
    )
    def SetKValue(self, value):
        """
        This command sets the kValue on SPFRx
        """
        spfrx_cm = self.component_manager.sub_component_managers["SPFRX"]
        spfrx_cm.write_attribute_value("kValue", value)

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def StopCommunication(self):
        """Stop communicating with monitored devices"""
        self.component_manager.stop_communicating()

    @command(dtype_in=None, dtype_out=None, display_level=DispLevel.OPERATOR)
    def StartCommunication(self):
        """Start communicating with monitored devices"""
        self.component_manager.start_communicating()

    @command(
        dtype_in=None,
        dtype_out=str,
        display_level=DispLevel.OPERATOR,
        doc_out=("Retrieve the states of SPF, SPFRx" " and DS as DishManager sees it."),
    )
    def GetComponentStates(self):
        """
        Get the current component states of subservient devices.

        Subservient devices constiture SPF, SPFRx and DS. Used for debugging.
        """
        component_states = {}
        for (
            device,
            component_state,
        ) in self.component_manager.sub_component_managers.items():
            component_states[device] = component_state._component_state
        component_states["DM"] = self.component_manager._component_state
        return json.dumps(str(component_states))

    @command(
        dtype_in=None,
        dtype_out=None,
        display_level=DispLevel.OPERATOR,
    )
    def SyncComponentStates(self) -> None:
        """
        Sync each subservient device component state with its tango device
        to refresh the dish manager component state.
        """
        if hasattr(self, "component_manager"):
            self.component_manager.sync_component_states()


def main(args=None, **kwargs):
    """Launch a DishManager device."""
    return run((DishManager,), args=args, **kwargs)


if __name__ == "__main__":
    db = Database()
    test_device = DbDevInfo()
    if "DEVICE_NAME" in os.environ:
        # DEVICE_NAME should be in the format domain/family/member
        test_device.name = os.environ["DEVICE_NAME"]
    else:
        # fall back to default name
        test_device.name = "ska001/elt/master"
    test_device._class = "DishManager"
    test_device.server = "DishManagerDS/01"
    db.add_server(test_device.server, test_device, with_dserver=True)
    main()
