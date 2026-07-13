========================
DishManager Tango Device
========================
The Dish Manager of the Dish LMC subsystem.

Properties
----------
.. index::
	single: B5DCDeviceFqdn; DishManager.B5DCDeviceFqdn

.. py:attribute:: B5DCDeviceFqdn
	:module: DishManager

	:data type: DevString

.. index::
	single: DSDeviceFqdn; DishManager.DSDeviceFqdn

.. py:attribute:: DSDeviceFqdn
	:module: DishManager

	:data type: DevString
	:default value: mid-dish/ds-manager/SKA001

.. index::
	single: DefaultActionTimeoutSeconds; DishManager.DefaultActionTimeoutSeconds

.. py:attribute:: DefaultActionTimeoutSeconds
	:module: DishManager

	The default timeout value (in seconds) for each fanned out action.

	:data type: DevDouble
	:default value: 120

.. index::
	single: DefaultWatchdogTimeout; DishManager.DefaultWatchdogTimeout

.. py:attribute:: DefaultWatchdogTimeout
	:module: DishManager

	:data type: DevDouble

.. index::
	single: DishId; DishManager.DishId

.. py:attribute:: DishId
	:module: DishManager

	:data type: DevString
	:default value: SKA001

.. index::
	single: GroupDefinitions; DishManager.GroupDefinitions

.. py:attribute:: GroupDefinitions
	:module: DishManager

	:data type: DevVarStringArray

.. index::
	single: LoggingLevelDefault; DishManager.LoggingLevelDefault

.. py:attribute:: LoggingLevelDefault
	:module: DishManager

	:data type: DevUShort
	:default value: 4

.. index::
	single: LoggingTargetsDefault; DishManager.LoggingTargetsDefault

.. py:attribute:: LoggingTargetsDefault
	:module: DishManager

	:data type: DevVarStringArray
	:default value: ['tango::logger']

.. index::
	single: MaxCapabilities; DishManager.MaxCapabilities

.. py:attribute:: MaxCapabilities
	:module: DishManager

	:data type: DevVarStringArray

.. index::
	single: MeanWindSpeedThreshold; DishManager.MeanWindSpeedThreshold

.. py:attribute:: MeanWindSpeedThreshold
	:module: DishManager

	Threshold value for mean wind speed (in m/s) used to trigger stow.

	:data type: DevDouble
	:default value: 11.1

.. index::
	single: SPFDeviceFqdn; DishManager.SPFDeviceFqdn

.. py:attribute:: SPFDeviceFqdn
	:module: DishManager

	:data type: DevString
	:default value: mid-dish/simulator-spfc/SKA001

.. index::
	single: SPFRxDeviceFqdn; DishManager.SPFRxDeviceFqdn

.. py:attribute:: SPFRxDeviceFqdn
	:module: DishManager

	:data type: DevString
	:default value: mid-dish/simulator-spfrx/SKA001

.. index::
	single: SkaLevel; DishManager.SkaLevel

.. py:attribute:: SkaLevel
	:module: DishManager

	:data type: DevShort
	:default value: 4

.. index::
	single: WMSDeviceNames; DishManager.WMSDeviceNames

.. py:attribute:: WMSDeviceNames
	:module: DishManager

	:data type: DevVarStringArray

.. index::
	single: WindGustThreshold; DishManager.WindGustThreshold

.. py:attribute:: WindGustThreshold
	:module: DishManager

	Threshold value for wind gust speed (in m/s) used to trigger stow.

	:data type: DevDouble
	:default value: 16.9

Attributes
----------
.. index::
	single: State; DishManager.State

.. py:attribute:: State
	:module: DishManager

	The operational state of the device as enumeration.

	:access: READ
	:data type: DevState
	:data format: SCALAR

.. index::
	single: Status; DishManager.Status

.. py:attribute:: Status
	:module: DishManager

	More detailed textual information about the device's status.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: achievedPointing; DishManager.achievedPointing

.. py:attribute:: achievedPointing
	:module: DishManager

	[0] Timestamp
	[1] Azimuth
	[2] Elevation

	:access: READ
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 3

.. index::
	single: achievedTargetLock; DishManager.achievedTargetLock

.. py:attribute:: achievedTargetLock
	:module: DishManager

	Indicates whether the Dish is on target or not based on the pointing error and time period parameters defined in configureTargetLock.

	:access: READ
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: actStaticOffsetValueEl; DishManager.actStaticOffsetValueEl

.. py:attribute:: actStaticOffsetValueEl
	:module: DishManager

	Actual elevation static offset (arcsec)

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: actStaticOffsetValueXel; DishManager.actStaticOffsetValueXel

.. py:attribute:: actStaticOffsetValueXel
	:module: DishManager

	Actual cross-elevation static offset (arcsec)

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: actionTimeoutSeconds; DishManager.actionTimeoutSeconds

.. py:attribute:: actionTimeoutSeconds
	:module: DishManager

	Timeout (in seconds) to be used for each action. On each action DishManager will wait
	for the timeout duration for expected subservient device attribute updates. A value
	<= 0 will disable waiting and no monitoring will occur, commands will be fanned out to
	their respective subsevient devices and then the DishManager command will return as
	COMPLETED immediately.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: adminMode; DishManager.adminMode

.. py:attribute:: adminMode
	:module: DishManager

	Read the Admin Mode of the device.

	It may interpret the current device condition and condition of all managed
	devices to set this. Most possibly an aggregate attribute.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: attenuation1PolHX; DishManager.attenuation1PolHX

.. py:attribute:: attenuation1PolHX
	:module: DishManager

	The current attenuation value for attenuator 1 on the
	H/X polarization.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: attenuation1PolVY; DishManager.attenuation1PolVY

.. py:attribute:: attenuation1PolVY
	:module: DishManager

	The current attenuation value for attenuator 1 on the
	V/Y polarization.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: attenuation2PolHX; DishManager.attenuation2PolHX

.. py:attribute:: attenuation2PolHX
	:module: DishManager

	The current attenuation value for attenuator 2 on the
	H/X polarization.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: attenuation2PolVY; DishManager.attenuation2PolVY

.. py:attribute:: attenuation2PolVY
	:module: DishManager

	The current attenuation value for attenuator 2 on the
	V/Y polarization.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: attenuationPolHX; DishManager.attenuationPolHX

.. py:attribute:: attenuationPolHX
	:module: DishManager

	The current total attenuation value across both attenuators on the
	H/X polarization.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: attenuationPolVY; DishManager.attenuationPolVY

.. py:attribute:: attenuationPolVY
	:module: DishManager

	The current total attenuation value across both attenuators on the
	V/Y polarization.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: autoWindStowEnabled; DishManager.autoWindStowEnabled

.. py:attribute:: autoWindStowEnabled
	:module: DishManager

	Flag to enable or disable auto wind stow on wind speed
	or wind gust for values exeeding the configured threshold.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: availableCapabilities; DishManager.availableCapabilities

.. py:attribute:: availableCapabilities
	:module: DishManager

	A list of available number of instances of each capability type, e.g. 'CORRELATOR:512', 'PSS-BEAMS:4'.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 20

.. index::
	single: azimuthOverWrap; DishManager.azimuthOverWrap

.. py:attribute:: azimuthOverWrap
	:module: DishManager

	Indicates that the Dish has moved beyond an azimuth wrap limit.

	:access: READ
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: b1CapabilityState; DishManager.b1CapabilityState

.. py:attribute:: b1CapabilityState
	:module: DishManager

	Report the device b1CapabilityState

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: b1LnaHPowerState; DishManager.b1LnaHPowerState

.. py:attribute:: b1LnaHPowerState
	:module: DishManager

	Status of the Band 1 SPFC LNA H polarization power state.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: b1LnaVPowerState; DishManager.b1LnaVPowerState

.. py:attribute:: b1LnaVPowerState
	:module: DishManager

	Status of the Band 1 SPFC LNA V polarization power state.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: b2CapabilityState; DishManager.b2CapabilityState

.. py:attribute:: b2CapabilityState
	:module: DishManager

	Report the device b2CapabilityState

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: b2LnaHPowerState; DishManager.b2LnaHPowerState

.. py:attribute:: b2LnaHPowerState
	:module: DishManager

	Status of the Band 2 SPFC LNA H polarization power state.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: b2LnaVPowerState; DishManager.b2LnaVPowerState

.. py:attribute:: b2LnaVPowerState
	:module: DishManager

	Status of the Band 2 SPFC LNA V polarization power state.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: b3CapabilityState; DishManager.b3CapabilityState

.. py:attribute:: b3CapabilityState
	:module: DishManager

	Report the device b3CapabilityState

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: b3LnaPowerState; DishManager.b3LnaPowerState

.. py:attribute:: b3LnaPowerState
	:module: DishManager

	Status of the Band 3 SPFC LNA polarization power state.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: b4CapabilityState; DishManager.b4CapabilityState

.. py:attribute:: b4CapabilityState
	:module: DishManager

	Report the device b4CapabilityState

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: b4LnaPowerState; DishManager.b4LnaPowerState

.. py:attribute:: b4LnaPowerState
	:module: DishManager

	Status of the Band 4 SPFC LNA H & V polarization power state.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: b5aCapabilityState; DishManager.b5aCapabilityState

.. py:attribute:: b5aCapabilityState
	:module: DishManager

	Report the device b5aCapabilityState

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: b5aLnaPowerState; DishManager.b5aLnaPowerState

.. py:attribute:: b5aLnaPowerState
	:module: DishManager

	Status of the Band 5a SPFC LNA H & V polarization power state.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: b5bCapabilityState; DishManager.b5bCapabilityState

.. py:attribute:: b5bCapabilityState
	:module: DishManager

	Report the device b5bCapabilityState

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: b5bLnaPowerState; DishManager.b5bLnaPowerState

.. py:attribute:: b5bLnaPowerState
	:module: DishManager

	Status of the SPFC LNA H & V polarization power state.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: b5dcConnectionState; DishManager.b5dcConnectionState

.. py:attribute:: b5dcConnectionState
	:module: DishManager

	Return the status of the connection to the B5DC proxy.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: b5dcServerConnectionState; DishManager.b5dcServerConnectionState

.. py:attribute:: b5dcServerConnectionState
	:module: DishManager

	Return the status of the connection of the B5dc Proxy device to the B5dc server.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: band0PointingModelParams; DishManager.band0PointingModelParams

.. py:attribute:: band0PointingModelParams
	:module: DishManager

	Parameters for (local) Band 0 pointing models used by Dish to do pointing corrections.

	When writing to this attribute, the selected band for correction will be set to B0.

	Band pointing model parameters are:
	[0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
	[9] ABA, [10] ABphi, [11] IE, [12] ECEC, [13] ECES, [14] HECE4,
	[15] HESE4, [16] HECE8, [17] HESE8

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 18

.. index::
	single: band1PointingModelParams; DishManager.band1PointingModelParams

.. py:attribute:: band1PointingModelParams
	:module: DishManager

	Parameters for (local) Band 1 pointing models used by Dish to do pointing corrections.

	When writing to this attribute, the selected band for correction will be set to B1.

	Band pointing model parameters are:
	[0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
	[9] ABA, [10] ABphi, [11] IE, [12] ECEC, [13] ECES, [14] HECE4,
	[15] HESE4, [16] HECE8, [17] HESE8

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 18

.. index::
	single: band1SamplerFrequency; DishManager.band1SamplerFrequency

.. py:attribute:: band1SamplerFrequency
	:module: DishManager

	BAND1 absolute sampler clock frequency (base plus offset).

	:access: WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: band2PointingModelParams; DishManager.band2PointingModelParams

.. py:attribute:: band2PointingModelParams
	:module: DishManager

	Parameters for (local) Band 2 pointing models used by Dish to do pointing corrections.

	When writing to this attribute, the selected band for correction will be set to B2.

	Band pointing model parameters are:
	[0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
	[9] ABA, [10] ABphi, [11] IE, [12] ECEC, [13] ECES, [14] HECE4,
	[15] HESE4, [16] HECE8, [17] HESE8

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 18

.. index::
	single: band2SamplerFrequency; DishManager.band2SamplerFrequency

.. py:attribute:: band2SamplerFrequency
	:module: DishManager

	BAND2 absolute sampler clock frequency (base plus offset).

	:access: WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: band3PointingModelParams; DishManager.band3PointingModelParams

.. py:attribute:: band3PointingModelParams
	:module: DishManager

	Parameters for (local) Band 3 pointing models used by Dish to do pointing corrections.

	When writing to this attribute, the selected band for correction will be set to B3.

	Band pointing model parameters are:
	[0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
	[9] ABA, [10] ABphi, [11] IE, [12] ECEC, [13] ECES, [14] HECE4,
	[15] HESE4, [16] HECE8, [17] HESE8

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 18

.. index::
	single: band3SamplerFrequency; DishManager.band3SamplerFrequency

.. py:attribute:: band3SamplerFrequency
	:module: DishManager

	BAND3 absolute sampler clock frequency (base plus offset).

	:access: WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: band4PointingModelParams; DishManager.band4PointingModelParams

.. py:attribute:: band4PointingModelParams
	:module: DishManager

	Parameters for (local) Band 4 pointing models used by Dish to do pointing corrections.

	When writing to this attribute, the selected band for correction will be set to B4.

	Band pointing model parameters are:
	[0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
	[9] ABA, [10] ABphi, [11] IE, [12] ECEC, [13] ECES, [14] HECE4,
	[15] HESE4, [16] HECE8, [17] HESE8

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 18

.. index::
	single: band4SamplerFrequency; DishManager.band4SamplerFrequency

.. py:attribute:: band4SamplerFrequency
	:module: DishManager

	BAND4 absolute sampler clock frequency (base plus offset).

	:access: WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: band5aPointingModelParams; DishManager.band5aPointingModelParams

.. py:attribute:: band5aPointingModelParams
	:module: DishManager

	Parameters for (local) Band 5a pointing models used by Dish to do pointing corrections.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 18

.. index::
	single: band5aSamplerFrequency; DishManager.band5aSamplerFrequency

.. py:attribute:: band5aSamplerFrequency
	:module: DishManager

	BAND5a absolute sampler clock frequency (base plus offset).

	:access: WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: band5bPointingModelParams; DishManager.band5bPointingModelParams

.. py:attribute:: band5bPointingModelParams
	:module: DishManager

	Parameters for (local) Band 5b pointing models used by Dish to do pointing corrections.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 18

.. index::
	single: band5bSamplerFrequency; DishManager.band5bSamplerFrequency

.. py:attribute:: band5bSamplerFrequency
	:module: DishManager

	BAND5b absolute sampler clock frequency (base plus offset).

	:access: WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: buildState; DishManager.buildState

.. py:attribute:: buildState
	:module: DishManager

	Read the Build State of the device.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: capturing; DishManager.capturing

.. py:attribute:: capturing
	:module: DishManager

	Indicates whether Dish is capturing data in the configured band or not.

	:access: READ
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: clkPhotodiodeCurrent; DishManager.clkPhotodiodeCurrent

.. py:attribute:: clkPhotodiodeCurrent
	:module: DishManager

	Reports the current flowing through the clock photodiode in the B5DC. Value is in milliamperes (mA).

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: commandedState; DishManager.commandedState

.. py:attribute:: commandedState
	:module: DishManager

	Read the last commanded operating state of the device.

	Initial string is "None". Only other strings it can change to is "OFF",
	"STANDBY" or "ON", following the start of the Off(), Standby(), On() or Reset()
	long running commands.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: configureTargetLock; DishManager.configureTargetLock

.. py:attribute:: configureTargetLock
	:module: DishManager

	[0] Pointing error
	[1] Time period

	:access: WRITE
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: configuredBand; DishManager.configuredBand

.. py:attribute:: configuredBand
	:module: DishManager

	The frequency band that the Dish is configured to capture data in.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: controlMode; DishManager.controlMode

.. py:attribute:: controlMode
	:module: DishManager

	Read the Control Mode of the device.

	The control mode of the device are REMOTE, LOCAL
	Tango Device accepts only from a ‘local’ client and ignores commands and
	queries received from TM or any other ‘remote’ clients. The Local clients
	has to release LOCAL control before REMOTE clients can take control again.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: desiredPointingAz; DishManager.desiredPointingAz

.. py:attribute:: desiredPointingAz
	:module: DishManager

	Azimuth axis desired pointing as reported by the dish structure controller's Tracking.TrackStatus.p_desired_Az field.

	:access: READ
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: desiredPointingEl; DishManager.desiredPointingEl

.. py:attribute:: desiredPointingEl
	:module: DishManager

	Elevation axis desired pointing as reported by the dish structure controller's Tracking.TrackStatus.p_desired_El field.

	:access: READ
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: dishMode; DishManager.dishMode

.. py:attribute:: dishMode
	:module: DishManager

	Dish rolled-up operating mode in Dish Control Model (SCM) notation

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: dsConnectionState; DishManager.dsConnectionState

.. py:attribute:: dsConnectionState
	:module: DishManager

	Displays connection status to DS device

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: dscCmdAuth; DishManager.dscCmdAuth

.. py:attribute:: dscCmdAuth
	:module: DishManager

	Indicates who has command authority

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: dscConnectionState; DishManager.dscConnectionState

.. py:attribute:: dscConnectionState
	:module: DishManager

	Return the status of the connection of the DSManager device to the dish controller.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: dscCtrlState; DishManager.dscCtrlState

.. py:attribute:: dscCtrlState
	:module: DishManager

	DSC Control State - an aggregation of DSC Command Authority and DSC State

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: dscErrorStatuses; DishManager.dscErrorStatuses

.. py:attribute:: dscErrorStatuses
	:module: DishManager

	Report the current DSC errors as a semicolon-delimited list. Reports 'OK' if no errors are present.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: dscPowerLimitKw; DishManager.dscPowerLimitKw

.. py:attribute:: dscPowerLimitKw
	:module: DishManager

	DSC Power Limit (kW). Note that this attribute can also be set by calling
	SetPowerMode. This value does not reflect the power limit in reality because
	the current PowerLimit(kW) is not reported as it cannot be read from the DSC.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: dshMaxShortTermPower; DishManager.dshMaxShortTermPower

.. py:attribute:: dshMaxShortTermPower
	:module: DishManager

	Configures the Max Short Term Average Power (5sec‐10min) in kilowatt that the DSH instance is curtailed to while dshPowerCurtailment is [TRUE]. The default value is 13.5.

	:access: WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: dshPowerCurtailment; DishManager.dshPowerCurtailment

.. py:attribute:: dshPowerCurtailment
	:module: DishManager

	The Max Short Term Average Power (5sec‐10min) of each DSH instance is curtailed to the value configured in dshMaxShortTermPower. The default condition is [TRUE] ‐ power curtailment is on. With power curtailment [TRUE], all DSH functionality is available but at reduced performance (for example reduced slew rates). With power curtailment [FALSE], all DSH functionality is available at full performance (for example maximum slew rates).

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: elementAlarmAddress; DishManager.elementAlarmAddress

.. py:attribute:: elementAlarmAddress
	:module: DishManager

	FQDN of Element Alarm Handlers

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: elementDatabaseAddress; DishManager.elementDatabaseAddress

.. py:attribute:: elementDatabaseAddress
	:module: DishManager

	FQDN of Element Database device

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: elementLoggerAddress; DishManager.elementLoggerAddress

.. py:attribute:: elementLoggerAddress
	:module: DishManager

	FQDN of Element Logger

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: elementTelStateAddress; DishManager.elementTelStateAddress

.. py:attribute:: elementTelStateAddress
	:module: DishManager

	FQDN of Element TelState device

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: spectrumSample; DishManager.spectrumSample

.. py:attribute:: spectrumSample
	:module: DishManager

	Note: This attribute maps to the spectrum sample attribute from the SPFRxReport the SPFRX spectrum sample data Spectrum sample data from the spectrometer as a packed DevFloat array. The array contains a UTC timestamp followed by multiple spectral datasets. Index layout: [0-1]: UTC timestamp in seconds, [2-1026]: P_on,X (1025 floats), [1027-2051]: P_on,Y (1025 floats), [2052-3076]: P_on,XY real (1025 floats), [3077-4101]: P_on,XY imaginary (1025 floats), [4102-5126]: P_off,X (1025 floats), [5127-6151]: P_off,Y (1025 floats), [6152-7176]: P_off,XY real (1025 floats), [7177-8201]: P_off,XY imaginary (1025 floats).

	:access: READ
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 8202

.. index::
	single: hPolRfPowerIn; DishManager.hPolRfPowerIn

.. py:attribute:: hPolRfPowerIn
	:module: DishManager

	Reports the input RF power level for the Horizontal (H) polarization measured at the B5DC RF Control Module (RFCM). Value is in dBm.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: hPolRfPowerOut; DishManager.hPolRfPowerOut

.. py:attribute:: hPolRfPowerOut
	:module: DishManager

	Reports the output RF power level for the Horizontal (H) polarization measured at the B5DC RF Control Module (RFCM). Value is in dBm.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: healthInfo; DishManager.healthInfo

.. py:attribute:: healthInfo
	:module: DishManager

	Report the reason for healthstate failures.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM

.. index::
	single: healthState; DishManager.healthState

.. py:attribute:: healthState
	:module: DishManager

	Read the Health State of the device.

	It interprets the current device condition and condition of
	all managed devices to set this. Most possibly an aggregate attribute.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: ignoreB5dc; DishManager.ignoreB5dc

.. py:attribute:: ignoreB5dc
	:module: DishManager

	Flag to disable B5DC device communication. When ignored, no commands will be issued to the device, it will be excluded from state aggregation, and no device related attributes will be updated.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: ignoreSpf; DishManager.ignoreSpf

.. py:attribute:: ignoreSpf
	:module: DishManager

	Flag to disable SPF device communication. When ignored, no commands will be issued to the device, it will be excluded from state aggregation, and no device related attributes will be updated.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: ignoreSpfrx; DishManager.ignoreSpfrx

.. py:attribute:: ignoreSpfrx
	:module: DishManager

	Flag to disable SPFRx device communication. When ignored, no commands will be issued to the device, it will be excluded from state aggregation, and no device related attributes will be updated.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: isKLocked; DishManager.isKLocked

.. py:attribute:: isKLocked
	:module: DishManager

	Check the SAT.RM module to see if
	the k- value is locked. If not false is returned.

	:access: READ
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: kValue; DishManager.kValue

.. py:attribute:: kValue
	:module: DishManager

	Returns the kValue for SPFRX

	:access: READ
	:data type: DevLong64
	:data format: SCALAR

.. index::
	single: lastCommandInvoked; DishManager.lastCommandInvoked

.. py:attribute:: lastCommandInvoked
	:module: DishManager

	Stores the name and timestamp (in UNIX UTC format) of the last invoked command.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: lastCommandedMode; DishManager.lastCommandedMode

.. py:attribute:: lastCommandedMode
	:module: DishManager

	Reports when and which was the last commanded mode change (not when completed). Time is a UNIX UTC timestamp.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: lastCommandedPointingParams; DishManager.lastCommandedPointingParams

.. py:attribute:: lastCommandedPointingParams
	:module: DishManager

	Default empty string when not set, and is a JSON stringof the last requested global pointing model when set.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: lastWatchdogReset; DishManager.lastWatchdogReset

.. py:attribute:: lastWatchdogReset
	:module: DishManager

	Returns the timestamp of the last watchdog reset in unix seconds.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: loggingLevel; DishManager.loggingLevel

.. py:attribute:: loggingLevel
	:module: DishManager

	Read the logging level of the device.

	Initialises to LoggingLevelDefault on startup.
	See :py:class:`~ska_control_model.LoggingLevel`

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: loggingTargets; DishManager.loggingTargets

.. py:attribute:: loggingTargets
	:module: DishManager

	Read the additional logging targets of the device.

	Note that this excludes the handlers provided by the ska_ser_logging
	library defaults - initialises to LoggingTargetsDefault on startup.

	:access: READ_WRITE
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 4
.. index::
	single: longRunningCommandIDsInQueue; DishManager.longRunningCommandIDsInQueue

.. py:attribute:: longRunningCommandIDsInQueue
	:module: DishManager

	Read the IDs of the long running commands in the queue.

	Every client that executes a command will receive a command ID as response.
	Keep track of IDs currently allocated.
	Entries are removed `self._command_tracker._removal_time` seconds
	after they have finished.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 66

.. index::
	single: longRunningCommandInProgress; DishManager.longRunningCommandInProgress

.. py:attribute:: longRunningCommandInProgress
	:module: DishManager

	Read the name(s) of the currently executing long running command(s).

	Name(s) of command and possible abort in progress or empty string(s).

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: longRunningCommandProgress; DishManager.longRunningCommandProgress

.. py:attribute:: longRunningCommandProgress
	:module: DishManager

	Read the progress of the currently executing long running command(s).

	ID, progress of the currently executing command(s).
	Clients can subscribe to on_change event and wait
	for the ID they are interested in.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 4

.. index::
	single: longRunningCommandResult; DishManager.longRunningCommandResult

.. py:attribute:: longRunningCommandResult
	:module: DishManager

	Read the result of the completed long running command.

	Reports unique_id, json-encoded result.
	Clients can subscribe to on_change event and wait for
	the ID they are interested in.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: longRunningCommandStatus; DishManager.longRunningCommandStatus

.. py:attribute:: longRunningCommandStatus
	:module: DishManager

	Read the status of the currently executing long running commands.

	ID, status pairs of the currently executing commands.
	Clients can subscribe to on_change event and wait for the
	ID they are interested in.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 132

.. index::
	single: longRunningCommandsInQueue; DishManager.longRunningCommandsInQueue

.. py:attribute:: longRunningCommandsInQueue
	:module: DishManager

	Read the long running commands in the queue.

	Keep track of which commands are that are currently known about.
	Entries are removed `self._command_tracker._removal_time` seconds
	after they have finished.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 66

.. index::
	single: lrcExecuting; DishManager.lrcExecuting

.. py:attribute:: lrcExecuting
	:module: DishManager

	Read info of the currently executing long running commands.

	Returns a list of info JSON blobs of the currently executing commands.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 3

.. index::
	single: lrcFinished; DishManager.lrcFinished

.. py:attribute:: lrcFinished
	:module: DishManager

	Read info of the finished long running commands.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 100

.. index::
	single: lrcProtocolVersions; DishManager.lrcProtocolVersions

.. py:attribute:: lrcProtocolVersions
	:module: DishManager

	Return supported protocol versions.

	:access: READ
	:data type: DevLong64
	:data format: SPECTRUM
	:max_dim_x: 2

.. index::
	single: lrcQueue; DishManager.lrcQueue

.. py:attribute:: lrcQueue
	:module: DishManager

	Read info of the long running commands in queue.

	Returns a list of info JSON blobs of the commands in queue.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 66

.. index::
	single: maxCapabilities; DishManager.maxCapabilities

.. py:attribute:: maxCapabilities
	:module: DishManager

	Maximum number of instances of each capability type, e.g. 'CORRELATOR:512', 'PSS-BEAMS:4'.

	:access: READ
	:data type: DevString
	:data format: SPECTRUM
	:max_dim_x: 20

.. index::
	single: meanWindSpeed; DishManager.meanWindSpeed

.. py:attribute:: meanWindSpeed
	:module: DishManager

	The average wind speed in m/s of the last 10 minutes
	calculated from the connected weather stations.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: noiseDiodeConfig; DishManager.noiseDiodeConfig

.. py:attribute:: noiseDiodeConfig
	:module: DishManager

	Returns the noiseDiodeConfig.

	:access: WRITE
	:data type: DevDouble
	:data format: SPECTRUM

.. index::
	single: noiseDiodeMode; DishManager.noiseDiodeMode

.. py:attribute:: noiseDiodeMode
	:module: DishManager

	Noise diode mode.

	0: OFF, 1: PERIODIC, 2: PSEUDO-RANDOM

	Note: This attribute does not persist after a power cycle. A default value is included
	as a device property on the SPFRx.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: periodicNoiseDiodePars; DishManager.periodicNoiseDiodePars

.. py:attribute:: periodicNoiseDiodePars
	:module: DishManager

	Periodic noise diode pars (units are in time quanta).

	[0]: period, [1]: duty cycle, [2]: phase shift

	Note: This attribute does not persist after a power cycle. A default value is included
	as a device property on the SPFRx.

	:access: READ_WRITE
	:data type: DevULong
	:data format: SPECTRUM
	:max_dim_x: 3

.. index::
	single: pointingBufferSize; DishManager.pointingBufferSize

.. py:attribute:: pointingBufferSize
	:module: DishManager

	Number of desiredPointing write values that the buffer has space for.
	Note: desiredPointing write values are stored by Dish in a buffer for application at the time specified in each desiredPointing record.

	:access: READ
	:data type: DevLong64
	:data format: SCALAR

.. index::
	single: pointingState; DishManager.pointingState

.. py:attribute:: pointingState
	:module: DishManager

	Returns the pointingState.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: polyTrack; DishManager.polyTrack

.. py:attribute:: polyTrack
	:module: DishManager

	[0] Timestamp
	[1] Azimuth
	[2] Elevation
	[3] Azimuth speed
	[4] Elevation speed
	[5] Azimuth acceleration
	[6] Elevation acceleration
	[7] Azimuth jerk
	[8] Elevation jerk

	:access: WRITE
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 9

.. index::
	single: powerState; DishManager.powerState

.. py:attribute:: powerState
	:module: DishManager

	Returns the powerState.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: programTrackTable; DishManager.programTrackTable

.. py:attribute:: programTrackTable
	:module: DishManager

	Timestamp of i-th coordinate in table (max 1000 coordinates) given in milliseconds since TAI epoch, representing time at which Dish should track i-th coordinate.
	Azimuth of i-th coordinate in table (max 1000 points) given in degrees.
	Elevation of i-th coordinate in table (max points coordinates) given in degrees

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SPECTRUM
	:max_dim_x: 3000

.. index::
	single: pseudoRandomNoiseDiodePars; DishManager.pseudoRandomNoiseDiodePars

.. py:attribute:: pseudoRandomNoiseDiodePars
	:module: DishManager

	Pseudo random noise diode pars (units are in time quanta).

	[0]: binary polynomial, [1]: seed, [2]: dwell

	Note: This attribute does not persist after a power cycle. A default value is included
	as a device property on the SPFRx.

	:access: READ_WRITE
	:data type: DevULong
	:data format: SPECTRUM
	:max_dim_x: 3

.. index::
	single: rfTemperature; DishManager.rfTemperature

.. py:attribute:: rfTemperature
	:module: DishManager

	Reports the temperature of the B5DC RF Control Module (RFCM) RF Printed Circuit Board (PCB). Value is in degrees Celsius.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: rfcmFrequency; DishManager.rfcmFrequency

.. py:attribute:: rfcmFrequency
	:module: DishManager

	Reports the current output frequency of the B5DC PLL in GHz. The default value is 11.1 GHz.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: rfcmHAttenuation; DishManager.rfcmHAttenuation

.. py:attribute:: rfcmHAttenuation
	:module: DishManager

	Reports the current attenuation setting for the Horizontal (H) polarization on the B5DC RF Control Module (RFCM). Value is in dB.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: rfcmPllLock; DishManager.rfcmPllLock

.. py:attribute:: rfcmPllLock
	:module: DishManager

	Reports the lock status of the B5DC RF Control Module (RFCM) PLL.Returns B5dcPllState enum indicating if locked or lock lost.

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: rfcmPsuPcbTemperature; DishManager.rfcmPsuPcbTemperature

.. py:attribute:: rfcmPsuPcbTemperature
	:module: DishManager

	Reports the temperature of the B5DC RF Control Module (RFCM) Power Supply Unit (PSU) PCB. Value is in degrees Celsius.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: rfcmVAttenuation; DishManager.rfcmVAttenuation

.. py:attribute:: rfcmVAttenuation
	:module: DishManager

	Reports the current attenuation setting for the Vertical (V) polarization on the B5DC RF Control Module (RFCM). Value is in dB.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: scanID; DishManager.scanID

.. py:attribute:: scanID
	:module: DishManager

	Report the scanID for Scan

	:access: READ_WRITE
	:data type: DevString
	:data format: SCALAR

.. index::
	single: simulationMode; DishManager.simulationMode

.. py:attribute:: simulationMode
	:module: DishManager

	Read the Simulation Mode of the device.

	Some devices may implement
	both modes, while others will have simulators that set simulationMode
	to True while the real devices always set simulationMode to False.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: spectralInversion; DishManager.spectralInversion

.. py:attribute:: spectralInversion
	:module: DishManager

	Spectral inversion to correct the frequency sense of the currently
	configured band with respect to the RF signal.

	Logic 0: Output signal in the same frequency sense as input.

	Logic 1: Output signal in the opposite frequency sense as input.

	Setting this attribute to true will set the
	spectrum to be flipped.

	:access: READ_WRITE
	:data type: DevBoolean
	:data format: SCALAR

.. index::
	single: spfConnectionState; DishManager.spfConnectionState

.. py:attribute:: spfConnectionState
	:module: DishManager

	Displays connection status to SPF device

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: spfrxConnectionState; DishManager.spfrxConnectionState

.. py:attribute:: spfrxConnectionState
	:module: DishManager

	Displays connection status to SPFRx device

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: testMode; DishManager.testMode

.. py:attribute:: testMode
	:module: DishManager

	Read the Test Mode of the device.

	Either no test mode or an indication of the test mode.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: trackInterpolationMode; DishManager.trackInterpolationMode

.. py:attribute:: trackInterpolationMode
	:module: DishManager

	Selects the type of interpolation to be used in program tracking.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: trackProgramMode; DishManager.trackProgramMode

.. py:attribute:: trackProgramMode
	:module: DishManager

	Selects the track program source (table A, table B, polynomial stream) used in the ACU for tracking. Coordinates given in the programTrackTable attribute are loaded in ACU in the selected table.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: trackTableCurrentIndex; DishManager.trackTableCurrentIndex

.. py:attribute:: trackTableCurrentIndex
	:module: DishManager

	Actual used index in the track table

	:access: READ
	:data type: DevLong64
	:data format: SCALAR

.. index::
	single: trackTableEndIndex; DishManager.trackTableEndIndex

.. py:attribute:: trackTableEndIndex
	:module: DishManager

	End index in the track table

	:access: READ
	:data type: DevLong64
	:data format: SCALAR

.. index::
	single: trackTableLoadMode; DishManager.trackTableLoadMode

.. py:attribute:: trackTableLoadMode
	:module: DishManager

	Selects track table load mode.
	With ADD selected, Dish will add the coordinate set given in programTrackTable attribute to the list of pointing coordinates already loaded in ACU.
	With NEW selected, Dish will delete the list of pointing coordinates previously loaded in ACU when new coordinates are given in the programTrackTable attribute.

	:access: READ_WRITE
	:data type: DevEnum
	:data format: SCALAR

.. index::
	single: vPolRfPowerIn; DishManager.vPolRfPowerIn

.. py:attribute:: vPolRfPowerIn
	:module: DishManager

	Reports the input RF power level for the Vertical (V) polarization measured at the B5DC RF Control Module (RFCM). Value is in dBm.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: vPolRfPowerOut; DishManager.vPolRfPowerOut

.. py:attribute:: vPolRfPowerOut
	:module: DishManager

	Reports the output RF power level for the Vertical (V) polarization measured at the B5DC RF Control Module (RFCM). Value is in dBm.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: versionId; DishManager.versionId

.. py:attribute:: versionId
	:module: DishManager

	Read the Version Id of the device.

	:access: READ
	:data type: DevString
	:data format: SCALAR

.. index::
	single: watchdogTimeout; DishManager.watchdogTimeout

.. py:attribute:: watchdogTimeout
	:module: DishManager

	Sets dish manager watchdog timeout interval in seconds. By writing a value greater than 0, the watchdog will be enabled. If the watchdog is not reset within this interval, the dish will Stow on expiry of the timer. The watchdog timer can be reset by calling the `ResetWatchdog()` command. The watchdog can be disabled by writing a value less than or equal to 0.

	:access: READ_WRITE
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: windGust; DishManager.windGust

.. py:attribute:: windGust
	:module: DishManager

	The maximum wind speed in m/s of the last 3 seconds
	calculated from the connected weather stations.

	:access: READ
	:data type: DevDouble
	:data format: SCALAR

.. index::
	single: wmsConnectionState; DishManager.wmsConnectionState

.. py:attribute:: wmsConnectionState
	:module: DishManager

	Displays connection status to wms device

	:access: READ
	:data type: DevEnum
	:data format: SCALAR

Commands
--------
.. index::
	single: Abort; DishManager.Abort

.. py:method:: Abort() -> DevVarLongStringArray
	:module: DishManager

	Abort currently executing long running command on DishManager including stopping dish movement and transitioning dishMode to StandbyFP. For details consult DishManager documentation

	:returns: A tuple containing a return code and a string
		message indicating status. The message is for
		information purpose only.

.. index::
	single: AbortCommands; DishManager.AbortCommands

.. py:method:: AbortCommands() -> DevVarLongStringArray
	:module: DishManager

	No input parameter (DevVoid)

	:returns: A tuple containing a return code and a string
		message indicating status. The message is for
		information purpose only.

.. index::
	single: ApplyPointingModel; DishManager.ApplyPointingModel

.. py:method:: ApplyPointingModel(DevString) -> DevVarLongStringArray
	:module: DishManager

	The command accepts a JSON input (value) containing data to update a particular
	band's (b1-b5b). The following 18 coefficients need to be within the JSON object:
	[0] IA, [1] CA, [2] NPAE, [3] AN, [4] AN0, [5] AW, [6] AW0, [7] ACEC, [8] ACES,
	[9] ABA, [10] ABphi, [11] IE, [12] ECEC, [13] ECES, [14] HECE4,
	[15] HESE4, [16] HECE8, [17] HESE8.

	The command only looks for the antenna, band and coefficients
	- everything else is ignored. A typical structure would be:
	"interface": "...",
	"antenna": "....",
	"band": "Band_...",
	"attrs": {...},
	"coefficients": {
	"IA": {...},
	...
	"HESE8":{...}
	},
	"rms_fits": {
	"xel_rms": {...},
	"el_rms": {...},
	"sky_rms": {...}
	}
	}
	
	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: CheckLongRunningCommandStatus; DishManager.CheckLongRunningCommandStatus

.. py:method:: CheckLongRunningCommandStatus(DevString) -> DevString
	:module: DishManager

	argin (None): the command id

	:returns: command status
.. index::
	single: ConfigureBand; DishManager.ConfigureBand

.. py:method:: ConfigureBand(DevString) -> DevVarLongStringArray
	:module: DishManager

	The command accepts a JSON string containing data to configure the SPFRx.
	The JSON structure is as follows:
	{
	"receiver_band": <string>,
	"band5_downconversion_subband or sub_band": <string>,
	"spfrx_processing_parameters": {
	"dishes": List[<string>],
	"sync_pps":  <bool>,
	"attenuation_pol_x": <float>,
	"attenuation_pol_y": <float>,
	"attenuation_1_pol_x": <float>,
	"attenuation_1_pol_y": <float>,
	"attenuation_2_pol_x": <float>,
	"attenuation_2_pol_y": <float>,
	"saturation_threshold": <float>,
	"noise_diode": {
	"pseudo_random": {
	"binary_polynomial": <long>,
	"seed": <long>,
	"dwell": <long>,
	},
	"periodic": {
	"period": <long>,
	"duty_cycle": <long>,
	"phase_shift": <long>,
	}
	}
	}
	}
	where 'receiver_band', 'dishes' and 'sync_pps' are mandatory fields. when 'receiver_band'
	is set to '5b', the 'band5_downconversion_subband or sub_band'field is mandatory.
	The 'dishes' field is a list of dish names that the SPFRx should be configured for,
	if 'all' is specified in the list, the SPFRx will be configured for all dishes.

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: ConfigureBand1; DishManager.ConfigureBand1

.. py:method:: ConfigureBand1(DevBoolean) -> DevVarLongStringArray
	:module: DishManager

	If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band being configured, and the band counters are reset. (Should be default to False).

	:returns: A tuple containing a return code and a string
		message indicating status.

.. index::
	single: ConfigureBand2; DishManager.ConfigureBand2

.. py:method:: ConfigureBand2(DevBoolean) -> DevVarLongStringArray
	:module: DishManager

	If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band being configured, and the band counters are reset. (Should be default to False).

	:returns: A tuple containing a return code and a string
		message indicating status.

.. index::
	single: ConfigureBand3; DishManager.ConfigureBand3

.. py:method:: ConfigureBand3(DevBoolean) -> DevVarLongStringArray
	:module: DishManager

	If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band being configured, and the band counters are reset. (Should be default to False).

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: ConfigureBand4; DishManager.ConfigureBand4

.. py:method:: ConfigureBand4(DevBoolean) -> DevVarLongStringArray
	:module: DishManager

	If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band being configured, and the band counters are reset. (Should be default to False).

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: ConfigureBand5a; DishManager.ConfigureBand5a

.. py:method:: ConfigureBand5a(DevBoolean) -> DevVarLongStringArray
	:module: DishManager

	If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band being configured, and the band counters are reset. (Should be default to False).

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: ConfigureBand5b; DishManager.ConfigureBand5b

.. py:method:: ConfigureBand5b(DevBoolean) -> DevVarLongStringArray
	:module: DishManager

	If the synchronise argument is True, the SPFRx FPGA is instructed to synchronise its internal flywheel 1PPS to the SAT-1PPS for the ADC that is applicable to the band being configured, and the band counters are reset. (Should be default to False).

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: ConfigureBand6; DishManager.ConfigureBand6

.. py:method:: ConfigureBand6() -> DevVarLongStringArray
	:module: DishManager

	Used by DVS for their KU band, sets IndexerPosition.B6 (7) on the DSC.

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: DebugDevice; DishManager.DebugDevice

.. py:method:: DebugDevice() -> DevUShort
	:module: DishManager

	No input parameter (DevVoid)

	:returns: The TCP port the debugger is listening on.

.. index::
	single: EndScan; DishManager.EndScan

.. py:method:: EndScan() -> DevVarLongStringArray
	:module: DishManager

	This command clears out the scanID from DishManager.

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: ExecutePendingOperations; DishManager.ExecutePendingOperations

.. py:method:: ExecutePendingOperations() -> DevVoid
	:module: DishManager

	No input parameter (DevVoid)

	:returns: No output parameter (DevVoid)

.. index::
	single: FlushCommandQueue; DishManager.FlushCommandQueue

.. py:method:: FlushCommandQueue() -> DevVoid
	:module: DishManager

	No input parameter (DevVoid)

	:returns: No output parameter (DevVoid)

.. index::
	single: GetComponentStates; DishManager.GetComponentStates

.. py:method:: GetComponentStates() -> DevString
	:module: DishManager

	No input parameter (DevVoid)

	:returns: Retrieve the states of SPF, SPFRx and DS as DishManager sees it.

.. index::
	single: GetVersionInfo; DishManager.GetVersionInfo

.. py:method:: GetVersionInfo() -> DevVarStringArray
	:module: DishManager

	No input parameter (DevVoid)

	:returns: The result code and the command unique ID

.. index::
	single: Init; DishManager.Init

.. py:method:: Init() -> DevVoid
	:module: DishManager

	Reinitialise the Tango device.

.. index::
	single: InterlockAck; DishManager.InterlockAck

.. py:method:: InterlockAck() -> DevVarLongStringArray
	:module: DishManager

	Clear the interlock status once interlocks or E-Stops have been cleared on the dish structure controller

	:returns: A tuple containing a return code and a string
		message indicating status.

.. index::
	single: IsCapabilityAchievable; DishManager.IsCapabilityAchievable

.. py:method:: IsCapabilityAchievable(DevVarLongStringArray) -> DevBoolean
	:module: DishManager

	[nrInstances][Capability types]

	:returns: (ResultCode, 'Command unique ID')

.. index::
	single: Off; DishManager.Off

.. py:method:: Off() -> DevVarLongStringArray
	:module: DishManager

	Not implemented.

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: On; DishManager.On

.. py:method:: On() -> DevVarLongStringArray
	:module: DishManager

	Not implemented.

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: Reset; DishManager.Reset

.. py:method:: Reset() -> DevVarLongStringArray
	:module: DishManager

	Not implemented.

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: ResetComponentConnection; DishManager.ResetComponentConnection

.. py:method:: ResetComponentConnection(DevString) -> DevVarLongStringArray
	:module: DishManager

	Reset connections between the Dish Manager and a sub-device.

	:param device_name: sub-device to reconnect [SPF, SPFRX, DS, B5DC]

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: ResetTrackTable; DishManager.ResetTrackTable

.. py:method:: ResetTrackTable() -> DevVarLongStringArray
	:module: DishManager

	This command resets the program track table on the controller

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: ResetWatchdogTimer; DishManager.ResetWatchdogTimer

.. py:method:: ResetWatchdogTimer() -> DevVarLongStringArray
	:module: DishManager

	This command resets the watchdog timer. `lastWatchdogReset` attribute will be updated with the unix timestamp. By default, the watchdog timer is disabled and can be enabled by setting the `watchdogTimeout` attribute to a value greater than 0.

	:returns: Returns a DevVarLongStringArray with the return code and message.

.. index::
	single: Scan; DishManager.Scan

.. py:method:: Scan(DevString) -> DevVarLongStringArray
	:module: DishManager

	DishManager records the scanID for an ongoing scan.

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: SetFrequency; DishManager.SetFrequency

.. py:method:: SetFrequency(DevLong64) -> DevVarLongStringArray
	:module: DishManager

	Set the frequency on the band 5 down converter.

	:param frequency: frequency to set [B5dcFrequency.F_11_1_GHZ(1),
	B5dcFrequency.F_13_2_GHZ(2) or B5dcFrequency.F_13_86_GHZ(3)]

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: SetHPolAttenuation; DishManager.SetHPolAttenuation

.. py:method:: SetHPolAttenuation(DevLong64) -> DevVarLongStringArray
	:module: DishManager

	Set the horizontal polarization attenuation on the band 5 down converter.

	:param attenuation_db: value to set in dB [0-31dB]

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: SetKValue; DishManager.SetKValue

.. py:method:: SetKValue(DevLong64) -> DevVarLongStringArray
	:module: DishManager

	Set the K value on the SPFRx.

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: SetMaintenanceMode; DishManager.SetMaintenanceMode

.. py:method:: SetMaintenanceMode() -> DevVarLongStringArray
	:module: DishManager

	This command triggers the Dish to transition to the MAINTENANCE Dishmode.

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: SetOperateMode; DishManager.SetOperateMode

.. py:method:: SetOperateMode() -> DevVarLongStringArray
	:module: DishManager

	SetOperateMode is a deprecated command, it is recommended to use ConfigureBand or ConfigureBand<N> command instead to trigger the transition to OPERATE dish mode.

	:returns: A tuple containing a return code and a string
		message indicating status.

.. index::
	single: SetStandbyFPMode; DishManager.SetStandbyFPMode

.. py:method:: SetStandbyFPMode() -> DevVarLongStringArray
	:module: DishManager

	This command triggers the Dish to transition to the STANDBY‐FP Dishmode.

	:returns: A tuple containing a return code and a string
		message indicating status.

.. index::
	single: SetStandbyLPMode; DishManager.SetStandbyLPMode

.. py:method:: SetStandbyLPMode() -> DevVarLongStringArray
	:module: DishManager

	This command triggers the Dish to transition to the STANDBY‐LP Dishmode.

	:returns: A tuple containing a return code and a string
		message indicating status.

.. index::
	single: SetStowMode; DishManager.SetStowMode

.. py:method:: SetStowMode() -> DevVarLongStringArray
	:module: DishManager

	This command triggers the Dish to transition to STOW.

	:returns: A tuple containing a return code and a string
		message indicating status.

.. index::
	single: SetVPolAttenuation; DishManager.SetVPolAttenuation

.. py:method:: SetVPolAttenuation(DevLong64) -> DevVarLongStringArray
	:module: DishManager

	Set the vertical polarization attenuation on the band 5 down converter.

	:param attenuation_db: value to set in dB [0-31dB]

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: Slew; DishManager.Slew

.. py:method:: Slew(DevVarFloatArray) -> DevVarLongStringArray
	:module: DishManager

	Slew to Az/EL: [0]: Azimuth
	[1]: Elevation

	:returns: A tuple containing a return code and a string
		message indicating status.

.. index::
	single: Standby; DishManager.Standby

.. py:method:: Standby() -> DevVarLongStringArray
	:module: DishManager

	Not implemented.

	:returns: :return: (not documented)
		:rtype: DevVarLongStringArray

.. index::
	single: StartCommunication; DishManager.StartCommunication

.. py:method:: StartCommunication() -> DevVoid
	:module: DishManager

	Starts communication with subdevices and starts the watchdog timer, if it is configured via `watchdogTimeout` attribute.

	:returns: No output parameter (DevVoid)

.. index::
	single: StopCommunication; DishManager.StopCommunication

.. py:method:: StopCommunication() -> DevVoid
	:module: DishManager

	Stops communication with subdevices and stops the watchdog timer, if it is active.

	:returns: No output parameter (DevVoid)

.. index::
	single: SyncComponentStates; DishManager.SyncComponentStates

.. py:method:: SyncComponentStates() -> DevVoid
	:module: DishManager

	Sync each subservient device componentstate with the dish manager component state.

	:returns: No output parameter (DevVoid)

.. index::
	single: Synchronise; DishManager.Synchronise

.. py:method:: Synchronise() -> DevVoid
	:module: DishManager

	Not Implemented.

	:returns: No output parameter (DevVoid)

.. index::
	single: Track; DishManager.Track

.. py:method:: Track() -> DevVarLongStringArray
	:module: DishManager

	Executes TrackStart on the DSC.

	:returns: A tuple containing a return code and a string
		message indicating status.

.. index::
	single: TrackLoadStaticOff; DishManager.TrackLoadStaticOff

.. py:method:: TrackLoadStaticOff(DevVarDoubleArray) -> DevVarLongStringArray
	:module: DishManager

	Load (global) static tracking offsets.

	The offset is loaded immediately and is not cancelled
	between tracks. The static offset introduces a positional adjustment to facilitate
	reference pointing and the five-point calibration. The static offsets are added the
	output of the interpolator before the correction of the static pointing model.

	Note: If the static pointing correction is switched off, the static offsets remain as
	an offset to the Azimuth and Elevation positions and need to be set to zero manually.

	Static offset parameters are:
	[0] Off_Xel, [1] Off_El

	:returns: A tuple containing a return code and a string
		message indicating status.

.. index::
	single: TrackStop; DishManager.TrackStop

.. py:method:: TrackStop() -> DevVarLongStringArray
	:module: DishManager

	Executes TrackStop on the DSC.

	:returns: A tuple containing a return code and a string
		message indicating status.
