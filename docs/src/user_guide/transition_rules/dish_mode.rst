===========================
Dish Mode Aggregation Rules
===========================

The Dish Manager derives the aggregated dish mode from the operating modes
and states of the DS, SPF and SPFRx devices.

.. note::

   * ``MAINTENANCE`` mode is not aggregated from subdevice operating modes. It is commanded directly on the Dish Manager.
   * For the case where devices are `set to ignored`, the conditions below are evaluated with the ignored device(s) removed from consideration.
    * Devices that can be ignored are SPF and/or SPFRX by setting dish manager attributes `ignoreSpf` and/or `ignoreSpfrx` to `True`.  
   * Conditions are evaluated in `order of precedence`, with the first matching condition determining the dish mode. 

**Rule Overview**

.. list-table::
   :header-rows: 1
   :widths: 20 100

   * - Dish Mode
     - Condition
   * - ``STARTUP``
     - Any subdevice is in startup:

       * ``DS.operatingmode == STARTUP``
       * ``SPF.operatingmode == STARTUP``
       * ``SPFRX.operatingmode == STARTUP``

   * - ``STOW``
     - ``DS.operatingmode == STOW``

   * - ``CONFIG``
     - Either:

       * ``SPFRX.operatingmode == CONFIGURE``
       * ``DS.indexerposition == MOVING``

   * - ``OPERATE``
     - All required devices:

       * ``DS.operatingmode == POINT``
       * ``SPF.operatingmode == OPERATE``
       * ``SPFRX.operatingmode == OPERATE``

   * - ``STANDBY_LP``
     - Dish structure is in standby low power and SPF is not in OPERATE:

       * ``DS.operatingmode == STANDBY``
       * ``DS.powerstate == LOW_POWER``
       * ``SPF.operatingmode != OPERATE``

   * - ``STANDBY_FP``
     - Dish structure is in standby and full power:

       * ``DS.operatingmode == STANDBY``
       * ``DS.powerstate == FULL_POWER``
