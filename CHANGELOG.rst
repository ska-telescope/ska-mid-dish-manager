###########
Change Log
###########

All notable changes to this project will be documented in this file.
This project adheres to `Semantic Versioning <http://semver.org/>`_.

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
