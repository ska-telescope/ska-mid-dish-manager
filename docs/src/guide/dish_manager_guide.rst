===========================
DishManager Design Overview
===========================
This is a walkthrough on the design and implementation of the dish manager with LRC feature ska-tango-base.
The DishManager receives commands from the TMC and then goes on to the respective commands on the subservient
devices. This interaction is managed through the component managers of the DishManager through the model and
a rules engine and finally to the subservient devices through their component managers.

Component Managers
------------------
There are two main component managers in the DishManager device:

* A generic component manager: which is specialised for the SPF, SPFRx and DS devices to maintain the connection to the tango device, monitor attributes for state changes and execute commands on the device.
* The DishManager component manager which manages the subservient devices and updates the device attributes as well as the execution of the tango commands.

All component managers at every point in time are a reflection of the underlying running tango device with the DishManager reporting an aggregate mode from the subservient.
The aggregation is based on rules which have been baked into the model to inform what the final transition will be anytime there is a fresh update from the subservient devices or the
DishManager requests a command. See image below summarising the design behind the DishManager implementation:

.. image:: ../images/DishManagerDesign.jpg
  :width: 50%
  :alt: Dish Manager Design

DishManager Model
-----------------
Every transition is managed by DishManager's component manager through the model. The model is a mode transition network
specifying:

* the allowed modes Dish has to be in to execute a command.
* the respective values the attributes in the underlying devices should report to reflect a particular value and the aggregated attributes on Dish.

.. image:: ../images/DishModeTransition.png
  :width: 50%
  :height: 600
  :alt: Dish Mode Transitions

Testing
-------
Since the component managers manage the interactions with the devices, we are able to check the robustness of our DishManager
device and the business rules without spinning up any tango infrastructure. In addition, there are tests in the pipeline which
tests the same cases with live tango devices, especially for the events and reporting of attributes when underlying devices die.
For this purpose, dummy devices with limited api and functionality for SPF, SPFRx and DS devices have been included for the `k8-test`.
