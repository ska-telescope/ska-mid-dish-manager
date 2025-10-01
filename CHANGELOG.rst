###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

## unreleased
*************
- Upgraded ska-mid-dish-simulators chart to v5.2.0
- The following band agnostic attenuation attributes are reflected from the updated SPFRx interface;
  - attenuation1PolH/X
  - attenuation1PolV/Y
  - attenuation2PolH/X
  - attenuation2PolV/Y

Version 8.4.2
*************
- Upgraded ska-mid-wms chart to v1.0.1
- Upgraded ska-mid-dish-simulators chart to v5.0.1
- Upgraded ska-mid-dish-ds-manger chart to v6.4.0
- Added in a new attribute, dscCtrlState (DSC Control State), propagated from DSManager.

Version 8.4.1
*************
- Upgraded ska-mid-dish-ds-manager chart to v6.3.1

  - Fixed ska-mid-dish-ds-manager memory leak with an upgrade of PyTango to v10.0.3

Version 8.4.0
*************
- Upgraded ska-mid-dish-ds-manager chart to v6.3.0

Version 8.3.0
*************
- Added `dishmanager.wms.station_id` helm value to build up `wmsDeviceNames` property for WMS component manager.
- Updated `ska-mid-dish-ds-manger` chart to v6.2.0.


Version 8.2.0
*************
- Added docker compose deployment for local development.

Version 8.1.0
*************
- Added new attribute `dscCmdAuth` that holds who has authority.
- Upgraded ska-mid-dish-ds-manager chart to v6.1.0.

Version 8.0.0
*************
- Added functionality to stow dish when watchdog timer is enabled and the timer expires.

  - Added new command `ResetWatchdogTimer()` to reset the watchdog timer.
  - Added new attribute `watchdogtimeout` to enable or disable the watchdog timer.
  - Added new attribute `lastwatchdogreset` to report the last time the watchdog timer was reset.

- Extended interface to expose monitoring points for mean wind speed and wind gust.

  - Added new attribute `autoWindStowEnabled` to enable or disable reaction to strong winds.
  - Added new attribute `meanWindSpeed` to report the average wind speed of the last 10 minutes.
  - Added new attribute `windGust` to report the max wind speed of the last 3 seconds.

- Upgraded ska-mid-wms sub chart to v1.0.0

Version 7.5.0
*************
- Added connection workaround for SPFRx attributes that have invalid quality on startup
- Partial SetMaintenanceMode implementation. It may not work as expected until SPFRx implements the changes to adminMode
- Add test_track_pattern acceptance test to run tracking test with track table input from csv files

  - Add manual job (k8s-test-runner-track-patterns) to gitlab pipeline to run test_track_pattern acceptance test

- Updated periodicNoiseDiodePars and pseudoRandomNoiseDiodePars to be DevVarLong64Array - (DevLong64,)
- Upgraded ska-mid-dish-simulators chart to v4.5.1
- Upgraded ska-mid-dish-ds-manager chart to v6.0.0

Version 7.4.0
*************
- Added SetMaintenanceMode implementation logic to dish manager component manager
- Upgraded ska-mid-dish-simulators chart to v4.4.3
- Upgraded ska-mid-dish-ds-manager chart to v5.0.0
- Upgraded ska-tango-util to v0.4.21
- Upgraded ska-tango-base to v0.4.21

Version 7.3.0
*************
- Upgraded ska-mid-dish-simulators chart to v4.4.2

  - Removed intermediate `READY` PointingState to align with PLC and resolve SKB-768
  
- Upgraded ska-mid-dish-ds-manager chart to v4.2.1
- Upgraded ska-tango-util to v0.4.19
- Upgraded ska-tango-base to v0.4.19
- Updated build state logic to update `buildState` on connection of subservient devices

Version 7.2.1
*************
- Updated `Abort` to handle dish slew movement
- Upgraded ska-mid-dish-simulators chart to v4.4.1
- Updated `versionID` to report the package version of the dish manager
- Extended functionality to handle `powerState` attribute updates
- Upgraded ska-mid-dish-ds-manager chart to v4.2.0

Version 7.2.0
*************
- Use TAIoffset as reported by DSManager when validating track table and for testing
- Upgraded ska-mid-dish-simulators chart to v4.4.0
- Upgraded ska-mid-dish-ds-manager chart to v4.1.0

Version 7.1.0
*************
- Upgraded ska-tango-util to v0.4.18
- Upgraded ska-tango-base to v0.4.18
- Upgraded ska-mid-dish-ds-manager chart to v4.0.0
- Block clients from sending commands when the dish state is DISABLED

  - `StartCommunication` should be called before any other command

Version 7.0.1
*************
- Address SKB-809:

  - DishLMC warns client when command is issued during lost communication to a component and continues anyway.
  - Device State reports ALARM when communication is lost.

- Device State reports ON when device is started.
- Periodic calls to `MonitorPing` on SPFRx is handled by component manager instead of polled command.
- Upgraded ska-mid-dish-ds-manager chart to v3.1.2

Version 7.0.0
*************
- Updated ska-mid-dish-simulators to v4.3.0
- Provided fix for SKB-751
- Added a factory class to manage device proxy creation
- Added some major improvements and refactoring
- Updated dockerfile to use new base images and improved docker image build
- Implemented Band0PointingModelParams attribute
- Updated ska-tango-util to v0.4.15
- Updated ska-tango-base to v0.4.15
- Upgraded ska-mid-dish-ds-manager chart to v3.1.0

  - Replaced component manager with a new implementation using sculib

Version 6.0.1
*************
- Added validation check with appropriate reply for `value` and `units` keys for the `ApplyPointingModel` command.
- Added `trackTableCurrentIndex` and `trackTableEndIndex` attributes that reflect track table indexes
- Upgraded ska-mid-dish-ds-manager chart to v3.0.1

  - Added attributes to reflect track table indexes

- Upgraded ska-mid-dish-simulators to v4.2.2

  - Exposed track table buffer indexes
  - Excluded zero-padded track table entries from being copied into internal buffer

Version 6.0.0
*************
- Added unit and range verification checks to `ApplyPointingModel` command
- Added in Read/Write dscPowerLimitKw attribute to be used when SetStandbyFPMode, SetStandbyLPMode and Slew are invoked.
- Upgraded ska-mid-dish-ds-manager chart to v3.0.0
- Upgraded ska-mid-dish-simulators to v4.2.1
- Upgraded to ska-tango-util and ska-tango-base to v0.4.13
- Updated SPFRx operatingMode from DATA_CAPTURE to OPERATE to match Rev 4 ICD
- Added in Read/Write dscPowerLimitKw attribute to be used when FP, LP and Slew are invoked.
- Updated periodicNoiseDiodePars and pseudoRandomNoiseDiodePars to be DevULong
- Added `Abort` tango command which cancels any task and restores the dish to FP mode

  - `AbortCommmands` implements the same handler as `Abort`

Version 5.0.1
*************
- Fixed MonitoringPing bug on DishManager


Version 5.0.0
*************
- Upgraded ska-mid-dish-simulators to v4.1.2

  - Servo loops simulator implemented to represent dish movement

- Upgraded ska-mid-dish-ds-manger chart to v2.1.1

  - DSC states and modes updated to align with ITF PLC

- Added in a command called `ApplyPointingModel` that updates bands using a json input
- Added Slew command execution preconditions on DishMode and PointingState

  - `DishMode` required to be in `OPERATE` and `PointingState` required to be `READY`

- Updated ska-tango-base and ska-tango-util to version 0.4.12
- Added an atrtribute called `last_commanded_pointing_params` that reports the last updated pointing parameters. 


Version 4.0.0
*************
- Updated `buildState` attribute to include version information of dish manager and subservient devices
- Upgraded ska-mid-dish-simulators chart to v4.0.1
- Upgraded ska-mid-ds-manager version to v2.0.0
- Added actStaticOffsetValueXel and actStaticOffsetValueEl attributes
- Updated band<N>PointingModelParams usage
- Added `lastCommandedMode` attribute to record the last mode change request
- Removed achievedPointingAz and achievedPointingEl
- Fixed missing events from sub-devices on the event consumer thread
- Exposed noide diode attributes from SPFRx:

  - noiseDiodeMode, periodicNoiseDiodePars, pseudoRandomNoiseDiodePars

Version 3.0.1
*************
- Updated the Stow Command to execute immediately when triggered and to abort all queued LRC tasks afterwards
- Upgraded ska-mid-dish-simulators chart to v3.1.0
- Upgraded ska-mid-dish-ds-manager chart to v1.5.0

  - WARNING: writes to `band[X]PointingModelParams` fails due to data type mismatch in current OPCUA nodeset file

Version 3.0.0
*************
- Updated component manager to check "command_allowed" on dequeue
- Overrode creation of lrc attributes to increase max_dim_x of `longRunningCommandInProgress`
- Updated package dependencies

  - Updated PyTango to v9.5.0
  - Updated ska-tango-base to v1.0.0

Version 2.7.0
*************
- Implement dedicated thread for tango_device_cm event_handler
- Added more exhaustive per command logging
- Updated to use SKA epoch for TAI timestamps

Version 2.6.1
*************
- Updated dish simulators version to v2.0.4
- Updated ds-manager version to v1.3.1

Version 2.6.0
*************
- Removed lmc tests and its manual job trigger
- Disabled default deployment of DSManager to use helm flag
- Added ignoreSpf and ignoreSpfrx attributes to conform to ADR-93
- Updated command map and transition state rules for when ignoring spf/spfrx to conform to ADR-93
- Removed azimuth and elevation speed arguments from Slew command
- Added quality state callback to publish change event on subservient device attribute quality changes
- Resolved a bug raised on setting the kValue on the SPFRx
- Added configureTargetLock implementation
- Updated implementation of pointing model parameters for bands 1, 3 and 4
- Added testing of aborting of long running commands 

Version 2.5.0
*************
- Enabled change and archive events on all Dish Manager attributes
- Removed placeholder implementation for `Scan` command
- Extended the device server interface: added `EndScan` command
- Exposed desiredPointingAz and desiredPointingEl attributes
- Removed desiredPointing attribute

Version 2.4.0
*************
- Updated docs to demonstrate running devices as nodb
- Added MonitoringPing command to the device server API
- Implemented a workaround to fix segfault errors in python-test job
- Updated dish simulators version to v1.6.6 
- Updated ds-manager version to v1.2.7
- Applies bug fix which causes intermittent failures in the test run

Version 2.3.6
*************
- Updated dish manager tango device name to conform to ADR-9
- Updated dish simulators version to v1.6.5 
- Updated ds-manager version to v1.2.6
- Updated ska-tango-base to v0.4.9
- Added track table time conversion and input validation

Version 2.3.5
*************
- Include ResultCode in updates sent to longRunningCommandResult
- Upgraded ska-mid-dish-simulators chart to v1.6.4
- Upgraded ska-mid-dish-ds-manager chart to v1.2.5

Version 2.3.4
*************
- Update ds-manager to version v1.2.4
- Update ska-tango-util to version v0.4.10
- Update ska-tango-base to version v0.4.8
- Update simulators to version v1.6.3

Version 2.3.3
*************
- Fix dish naming when dish IDs 100 or more
- Update simulators to version v1.6.2
- Update ds-manager to version v1.2.3
- Push archive events for attributes

Version 2.3.2
*************
- Use ska-ser-sphinx-theme for documentation
- Expand docs to include user guide with example usage
- Implement placeholder long running command for scan command
- Explicitly convert dish IDs to strings in template

Version 2.3.1
*************
- Fixed a bug where bandinfocus was not used correctly to calculate the bands
- Upgraded ska-mid-dish-ds-manager chart to v1.2.1

Version 2.3.0
*************
- Upgraded ska-mid-dish-simulators chart to v1.6.0
- Upgraded ska-mid-dish-ds-manager chart to v1.2.0
- Upgraded ska tango utils chart to v0.4.7
- Not deploying ska-tango-base(Database DS) by default anymore
- Extended device server interface

  - Implemented `Slew`, `TrackLoadStaticOff`, `SetKValue` commands
  - Implemented `band2PointingModelParams`, `kValue`, `programTracktable` attributes

Version 2.2.9
*************
- Upgrade ska-mid-dish-simulators chart to v1.3.1
- Upgrade ska tango utils chart to v0.4.6

Version 2.2.8
*************
- Fix bug in component manager for dishMode computation

Version 2.2.7
*************
- Revert ska-tango-util upgrade in 2.2.6
- Upgrade ska-mid-dish-simulators chart to v1.2.2

Version 2.2.6
*************
- Upgraded ska-tango-util to v0.4.6
- Upgraded dsconfig docker image to v1.5.11
- Upgraded ska-mid-dish-simulators chart to v1.2.1
- Added .readthedocs.yaml for docs build
- Fleshed out TrackStop command implementation
- Updated helm chart to make the sub device names configurable

Version 2.2.5
*************
- Manual job to run lmc test prior to dish manager release
- Bug fixes

  - Refactored capability state updates in _component_state_changed
  - Updated tango_device_cm to use .lower() on monitored attribute names when updating component states

Version 2.2.4
*************
- Updated helm chart to make the spfrx device name configurable
- Installing ska-tango-base from a release

Version 2.2.3
*************
- Bump the simulators dependency chart up to 1.2.0

Version 2.2.2
*************
- Updated DishManager command fanout to SPFRx to support removal of CaptureData command
- Bug fixes and improvements
- Use ska-mid-dish-simulators v0.2.0 with simulator log forwarding towards TLS

Version 2.1.2
*************
- Updated DishManager configureBand interface: configureBandx(timestamp) > configureBandx(boolean)
- Use ska-mid-dish-simulators v0.1.0 with updates to SPFRx device SetStandbyMode cmd

Version 2.1.1
*************
- Use ska-mid-dish-simulators v0.0.8 with SPFRx interface change
- Update fanout for SPFRx to remove `CaptureData` and references to it

Version 2.1.0
*************
- Conform to ADR-32 Dish ID format e.g. mid_d0001/elt/master -> ska001/elt/master

Version 2.0.1
*************
- Increment python package version to match helm chart version
- Increment simulator chart to 0.0.6
- Added synchronise boolean parameter to SPFRx configureBand function call
- Increment ska-tango-util chart to 0.4.2

Version 2.0.0
*************
- Updated Python to 3.8
- Updated PyTango to 3.6.6
- Added DS, SPF, SPFRx connection state attributes

Version 1.8.1
*************
- Use version 0.0.4 simulators
- Updated DishModeModel to trigger CONFIG when commanded from STOW
- Updated DishManager API docs reference

Version 1.8.0
*************
- Use version 0.0.3 simulators

Version 1.7.0
*************
- Added GetComponentStates command

Version 1.6.0
*************
- Updated to latest ska-mid-dish-simulators chart
- Updated capabilitystates accordingly

Version 1.5.0
*************
- Updated helm to only deploy the DS device when specifically asked for and not by default

Version 1.4.0
*************
- Updated DS device to not be asyncio based

Version 1.3.0
*************
- Removed SPF and SPFRx devices from codebase and helm charts
- Helm chart does not install SPF and SPFRx by default (enable with `--set "ska-mid-dish-simulators.enabled=true"`)

Version 1.2.0
*************
- Synced DishManager's achievedPointing reading with the DSManager's reading (same attribute name)
- Added functionality to indicate that dish is capturing data
- Pinned poetry to version 1.1.13

Version 1.1.0
*************
- Added CapabilityState attributes
- Added configuredBand checks when calling SetOperateMode

Version 1.0.0
*************
- Implementation details for commands fleshed out
- DishMode model updated with rules engine
- Documentation added

Version 0.0.1
*************
- The first release of the DishManager rewrites DishLMC DishMaster in python:

  - Device interface conforms to spec
  - Commands implemented as LRC with no functionality
  - Subservient devices managed by component manager
  - DishMode model to handle commands requests on DishManager
