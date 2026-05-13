==================================
Capability State Aggregation Rules
==================================

The Dish Manager derives the aggregated capability state from the dish mode,
DS operating state, DS indexer position, and the capability states reported
by the SPF and SPFRx devices.

.. note::

   * For the case where devices are `set to ignored`, the conditions below are evaluated with the ignored device(s) removed from consideration.

    * Devices that can be ignored are SPF and/or SPFRX by setting dish manager attributes `ignoreSpf` and/or `ignoreSpfrx` to `True`.  

   * Conditions are evaluated in `order of precedence`, with the first matching condition determining the capability state.
   * If none of the conditions below are met, the capability state is reported as ``UNKNOWN``. 

**Rule Overview**

.. list-table::
   :header-rows: 1
   :widths: 10 25 85

   * - Order
     - Capability State
     - Condition

   * - 1
     - ``UNAVAILABLE``
     - Dish structure is in startup or emergency stop, and all
       subdevices report unavailable capability:

       * ``DS.operatingmode == STARTUP`` or ``ESTOP``
       * ``SPF.capabilitystate == UNAVAILABLE``
       * ``SPFRX.capabilitystate == UNAVAILABLE``

   * - 2
     - ``STANDBY``
     - Dish is in standby mode and subsystem capability states are standby or operate:

       * ``DM.dishmode == STANDBY_LP`` or ``STANDBY_FP``
       * ``SPF.capabilitystate`` is one of:

         * ``STANDBY``
         * ``OPERATE_DEGRADED``
         * ``OPERATE_FULL``

       * ``SPFRX.capabilitystate`` is one of:

         * ``STANDBY``
         * ``OPERATE``

   * - 3
     - ``STANDBY``
     - Dish is stowed with the indexer stationary:

       * ``DM.dishmode == STOW``
       * ``DS.indexerposition != MOVING``
       * ``SPF.capabilitystate == STANDBY``
       * ``SPFRX.capabilitystate`` is either:

         * ``STANDBY``
         * ``OPERATE``

   * - 4
     - ``STANDBY``
     - Dish is in maintenance mode:

       * ``DM.dishmode == MAINTENANCE``
       * ``SPF.capabilitystate`` is either:

         * ``STANDBY``
         * ``OPERATE_DEGRADED``
         * ``OPERATE_FULL``

       * ``SPFRX.capabilitystate == STANDBY``

   * - 5
     - ``OPERATE_FULL``
     - Dish is stowed or operating, and all subsystems report full operational capability:

       * ``DM.dishmode`` is either:

         * ``STOW``
         * ``OPERATE``

       * ``SPF.capabilitystate == OPERATE_FULL``
       * ``SPFRX.capabilitystate == OPERATE``

   * - 6
     - ``CONFIGURING``
     - Dish is configuring:

       * ``DM.dishmode == CONFIG``
       * ``SPF.capabilitystate`` is either:

         * ``OPERATE_DEGRADED``
         * ``OPERATE_FULL``

       * ``SPFRX.capabilitystate`` is either:

         * ``CONFIGURE``
         * ``OPERATE``

   * - 7
     - ``OPERATE_DEGRADED``
     - Dish is stowed or pointing with a stationary indexer, and SPF reports degraded operation:

       * ``DS.indexerposition != MOVING``
       * ``DS.operatingmode`` is either:

         * ``STOW``
         * ``POINT``

       * ``SPF.capabilitystate == OPERATE_DEGRADED``
       * ``SPFRX.capabilitystate == OPERATE``