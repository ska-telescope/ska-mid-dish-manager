===================
Dish Manager Alarms
===================

Overview
--------
Dish manager has alarm events configured on all attributes. The alarm events are setup so that an alarm 
event is raised when an attribute value exceeds the warning or alarm thresholds. Tango currently
only supports numeric types for alarm events - thus alarm events for non-numeric attributes will not be raised.

Usage
-----
This code block below illustrates how to setup the alarm thresholds for an attribute and subscribe to the alarm events.

.. code-block:: ipython

    In [1]: dm = DeviceProxy("mid-dish/dish-manager/SKA001")
    In [2]: dm.hPolRfPowerOut
    Out[2]: 0.0

    # Get the attribute configuration for hPolRfPowerOut and set the thresholds
    In [7]: attr_config = dm.get_attribute_config("hPolRfPowerOut")
    In [8]: attr_config.alarms.min_warning = "-5"
    In [9]: attr_config.alarms.max_warning = "15"
    In [10]: attr_config.alarms.min_alarm = "-10"
    In [11]: attr_config.alarms.max_alarm = "20"
    In [12]: dm.set_attribute_config(attr_config)

    # Subscribe to the ALARM_EVENT to get notified when the attribute value exceeds the warning or alarm thresholds.
    In [23]: dm.subscribe_event("hPolRfPowerOut", tango.EventType.ALARM_EVENT, tango.utils.EventCallback())
    2026-07-23 10:09:19.005183 MID-DISH/DISH-MANAGER/SKA001 HPOLRFPOWEROUT ALARM SUBSUCCESS [ATTR_VALID] 0.0
    Out[23]: 2

    # When numeric value exceeds the warning or alarm thresholds, an ALARM_EVENT will be raised and the callback function will be called.