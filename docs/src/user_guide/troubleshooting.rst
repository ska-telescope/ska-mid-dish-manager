===============
Troubleshooting
===============


**Operator Logs**

Dish manager logs are tagged for filtering purposes. Operator related logs are tagged 
with ``user=operator``. In Kibana, one can filter for operator logs by using the following query:

.. code-block:: none

   ska_tags_field.user : "operator"


**Tango command to force reconnection**

If communication with one or more sub-devices is lost or becomes unstable, operators can 
manually trigger a reconnection using the ``ResetComponentConnection`` Tango command.

Command
-------

.. code-block:: none

   ResetComponentConnection(device_name: DevString)


Description
-----------

This command stops and restarts communication with the specified sub-devices. It is useful 
for recovering from transient communication failures or reinitializing device subscriptions.


Valid device names
------------------

The following sub-devices are supported:

- ``SPF``
- ``SPFRX``
- ``DS``
- ``B5DC``


Example usage (tango)
----------------------

.. code-block:: python

   device_proxy.ResetComponentConnection("SPF")