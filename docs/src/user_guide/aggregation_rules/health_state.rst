==============================
Health State Aggregation Rules
==============================

The Dish Manager derives the aggregated health state from the health states and connection states
reported by the DS, SPF and SPFRx devices.

.. note::

   * For the case where devices are `set to ignored`, the conditions below are evaluated with the ignored device(s) removed from consideration.

    * Devices that can be ignored are SPF and/or SPFRX by setting dish manager attributes `ignoreSpf` and/or `ignoreSpfrx` to `True`.  

   * Conditions are evaluated in `order of precedence`, with the first matching condition determining the health state.
   * If none of the conditions below are met, the health state defaults to ``UNKNOWN``. 

**Rule Overview**

.. list-table::
   :header-rows: 1
   :widths: 10 25 85

   * - Order
     - Health State
     - Condition

   * - 1
     - ``DEGRADED``
     - At least one subdevice reports ``DEGRADED`` health state,
       while the remaining subdevices are in one of:

       * ``OK`` or ``NORMAL``
       * ``DEGRADED``
       * ``UNKNOWN``

   * - 2
     - ``FAILED``
     - Any subdevice reports a ``FAILED`` health state:

       * ``DS.healthstate == FAILED``
       * ``SPF.healthstate == FAILED``
       * ``SPFRX.healthstate == FAILED``

   * - 3
     - ``OK``
     - All subdevices report healthy operation:

       * ``DS.healthstate == OK``
       * ``SPF.healthstate == NORMAL``
       * ``SPFRX.healthstate == OK``

   * - 4
     - ``UNKNOWN``
     - Any subdevice reports an unknown health state:

       * ``DS.healthstate == UNKNOWN``
       * ``SPF.healthstate == UNKNOWN``
       * ``SPFRX.healthstate == UNKNOWN``

**HealthState FAILED on component disconnection**

Should any of the devices that Dish Manager is configured to monitor and control become unavailable or disconnected,
as shown by their respective connection state attributes transitioning to `DISABLED` or `NOT_ESTABLISHED`, the aggregated Dish Manager
healthState will be overwritten to report `FAILED`.

The table below shows the connection state attributes that are taken into account when the dish `healthState` is computed, and the conditions
under which their states will not be considered.

.. list-table::
   :header-rows: 1
   :widths: 33 33 33

   * - Attribute
     - Connection represented by the attribute
     - Condition where the state of the connection is ignored

   * - `dsConnectionState`
     - `Dish Manager` to/from `DS Manager`
     - Cannot be ignored
  
   * - `dscConnectionState`
     - `DS Manager` to/from `Dish structure controller`
     - Cannot be ignored
  
   * - `spfConnectionState`
     - `Dish Manager` to/from `SPF controller`
     - `ignoreSpf` == `True`
  
   * - `spfrxConnectionState`
     - `Dish Manager` to/from `SPFRx`
     - `ignoreSpfrx` == `True`

   * - `b5dcConnectionState`
     - `Dish Manager` to/from `B5dc Proxy`
     - `ignoreB5dc` == `True`
  
   * - `b5dcServerConnectionState`
     - `B5dc Proxy` to/from `B5dc Server`
     - `ignoreB5dc` == `True`