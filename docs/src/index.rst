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

.. toctree::
   :maxdepth: 1
   :caption: DishManager Guide

   guide/dish_manager_design
   guide/component_managers
   guide/abort_commands
   guide/dish_manager_models

.. toctree::
   :maxdepth: 1
   :caption: API

   api/index

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
