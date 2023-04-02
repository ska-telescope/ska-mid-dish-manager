###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

Version 2.1.2
*************
- Use ska-mid-dish-simulators v0.0.9 with updates to capturingData attribute
- Apply SPFRx operatingMode `DATA-CAPTURE` updates according to fan-out requirements

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
- Helm chart does not install SPF and SPFRx by default
  - enable with `--set "ska-mid-dish-simulators.enabled=true"`

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

The first release of the DishManager rewrites DishLMC DishMaster in
python:

- Device interface conforms to spec
- Commands implemented as LRC with no functionality
- Subservient devices managed by component manager
- DishMode model to handle commands requests on DishManager
