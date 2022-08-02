==============================
DishManager Component Managers
==============================

There are two main component managers in the DishManager device:

* A generic component manager: which is specialised for the SPF, SPFRx and DS devices to maintain the connection to the tango device, monitor attributes for state changes and execute commands on the device.
* The DishManager component manager which manages the subservient devices and updates the device attributes as well as the execution of the tango commands.

All component managers at every point in time are a reflection of the underlying running tango device with the DishManager reporting an aggregate mode from the subservient.
The aggregation is based on rules which have been baked into the model to inform what the final transition will be anytime there is a fresh update from the subservient devices or the
DishManager requests a command.
