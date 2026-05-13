=================================
Configured Band Aggregation Rules
=================================

The Dish Manager derives the aggregated configured band from the DS indexer
position, the SPFRx configured band, and the SPF band in focus.

.. note::

   * For the case where devices are `set to ignored`, the conditions below are evaluated with the ignored device(s) removed from consideration.

    * Devices that can be ignored are SPF and/or SPFRX by setting dish manager attributes `ignoreSpf` and/or `ignoreSpfrx` to `True`.  

   * Conditions are evaluated in `order of precedence`, with the first matching condition determining the configured band. 
   * If none of the conditions below are met, the configured band is reported as ``UNKNOWN``.

**Rule Overview**

.. list-table::
   :header-rows: 1
   :widths: 10 25 65

   * - Order
     - Configured Band
     - Condition

   * - 1
     - ``NONE``
     - No band is configured:

       * ``SPFRX.configuredband == NONE``

   * - 2
     - ``B1``
     - All subsystems indicate Band 1:

       * ``DS.indexerposition == B1``
       * ``SPFRX.configuredband == B1``
       * ``SPF.bandinfocus == B1``

   * - 3
     - ``B2``
     - All subsystems indicate Band 2:

       * ``DS.indexerposition == B2``
       * ``SPFRX.configuredband == B2``
       * ``SPF.bandinfocus == B2``

   * - 4
     - ``B3``
     - All subsystems indicate Band 3:

       * ``DS.indexerposition == B3``
       * ``SPFRX.configuredband == B3``
       * ``SPF.bandinfocus == B3``

   * - 5
     - ``B4``
     - All subsystems indicate Band 4:

       * ``DS.indexerposition == B4``
       * ``SPFRX.configuredband == B4``
       * ``SPF.bandinfocus == B4``

   * - 6
     - ``B5a``
     - All subsystems indicate Band 5a:

       * ``DS.indexerposition == B5a``
       * ``SPFRX.configuredband == B5a``
       * ``SPF.bandinfocus == B5a``

   * - 7
     - ``B5b``
     - DS and SPF indicate Band 5b while SPFRx reports Band 1:

       * ``DS.indexerposition == B5b``
       * ``SPFRX.configuredband == B1``
       * ``SPF.bandinfocus == B5b``