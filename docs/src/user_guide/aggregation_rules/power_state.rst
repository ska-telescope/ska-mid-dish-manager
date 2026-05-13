=============================
Power State Aggregation Rules
=============================

The Dish Manager derives the aggregated power state from the power states
reported by the DS and SPF devices.

.. note::

   * For the case where devices are `set to ignored`, the conditions below are evaluated with the ignored device(s) removed from consideration.

    * Devices that can be ignored are SPF and/or SPFRX by setting dish manager attributes `ignoreSpf` and/or `ignoreSpfrx` to `True`.  

   * Conditions are evaluated in `order of precedence`, with the first matching condition determining the power state. 
   * If none of the conditions below are met, the power state is reported as ``LOW``.

**Rule Overview**

.. list-table::
   :header-rows: 1
   :widths: 10 20 70

   * - Order
     - Power State
     - Condition

   * - 1
     - ``UPS``
     - DS reports either UPS or OFF:

       * ``DS.powerstate == UPS``
       * ``DS.powerstate == OFF``

   * - 2
     - ``LOW``
     - DS reports low power:

       * ``DS.powerstate == LOW_POWER``

   * - 3
     - ``FULL``
     - DS reports full power:

       * ``DS.powerstate == FULL_POWER``

   * - 4
     - ``LOW``
     - DS power state is unknown, but SPF reports low power:

       * ``DS.powerstate == UNKNOWN``
       * ``SPF.powerstate == LOW_POWER``

   * - 5
     - ``FULL``
     - DS power state is unknown, but SPF reports full power:

       * ``DS.powerstate == UNKNOWN``
       * ``SPF.powerstate == FULL_POWER``

   * - 6
     - ``LOW``
     - Both DS and SPF report unknown power state:

       * ``DS.powerstate == UNKNOWN``
       * ``SPF.powerstate == UNKNOWN``