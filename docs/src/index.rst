==================================
SKA Mid Dish Manager Documentation
==================================

Description
-----------

This device provides master control and rolled-up monitoring of dish. When
commanded, it propagates the associated command to the relevant sub-systems
and updates its related attributes based on the aggregation of progress
reported by those sub-systems. It also exposes attributes which directly
relate to certain states of the sub-systems without making a proxy to
those sub-element devices.

.. image:: images/DishLMC.png
  :width: 100%
  :alt: Dish LMC diagram

Developer Guide
---------------

.. toctree::
  :maxdepth: 1

   Design<guide/dish_manager_design>
   Component Managers<guide/component_managers>
   Abort Commands<guide/abort_commands>
   Models<guide/dish_manager_models>
   API<api/index>

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
