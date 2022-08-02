===========================
DishManager Design Overview
===========================

This is a walkthrough on the design and implementation of the dish manager with LRC featured in ska-tango-base.
The DishManager receives commands from the TMC and then goes on to the respective commands on the subservient
devices. This interaction is managed through the component managers of the DishManager through the model and
a rules engine and finally to the subservient devices through their component managers.

See image below summarising the design behind the DishManager implementation:

.. image:: ../images/DishManagerDesign.jpg
  :width: 50%
  :alt: Dish Manager Design


Testing
-------

Since the component managers manage the interactions with the devices, we are able to check the robustness of our DishManager
device and the business rules captured in our model without spinning up any tango infrastructure. These unit tests are captured in the `python-test` job.

In addition, there are tests in the pipeline which run against live tango devices, especially for the events and reporting of attributes.
For this purpose, dummy devices with limited api and functionality for SPF, SPFRx and DS devices. These acceptance tests are captured in the `k8-test` job.
