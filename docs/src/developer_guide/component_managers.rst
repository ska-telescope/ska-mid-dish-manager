==============================
DishManager Component Managers
==============================

There are three main component managers in the DishManager device:

* A generic component manager: which is specialised for the SPF, SPFRx and DS
  devices to maintain the connection to the tango device, monitor attributes for
  state changes and execute commands on the device.
* A specialised component manager to enable monitoring of 1 or more instances
  of the weather monitoring system (WMS) Tango device. This component makes use
  an internal Tango group to execute read and write requests against monitored
  WMS devices.
* The DishManager component manager which manages the subservient devices and
  updates the device attributes as well as the execution of the tango commands.

The state represented by subservient device component managers for SPF, SPFRx and
DS at every point in time are a reflection of the underlying running tango device. 

The DishManager reflects the respective attribute value or computes it based on
the aggregation of the subservient states. The aggregation is based on rules which
have been baked into the model to inform what the final transition will be anytime
there is a fresh update from the subservient devices or the DishManager requests 
a command.

The specialised component manager for the WMS device(s) presents the consolidated 
weather data from all monitored weather station devices, providing both the average
wind speed and wind gust reading. This data is then reflected by the DishManager
on the respective attributes

.. note:: The fanned out command to the subservient device can fail immediately or
  at a later stage during the execution. DishManager does not bail out on the
  requested command if a failure occurs during the execution of the sub commands.
  It continues to watch and report on the progress of fanned out commands. The
  client will need to watch the LRC progress attribute to take appropriate action.
