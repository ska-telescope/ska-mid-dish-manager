==============================
Health State Aggregation Rules
==============================

The Dish Manager derives the aggregated health state from the health states
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

