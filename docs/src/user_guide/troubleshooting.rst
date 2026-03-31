===============
Troubleshooting
===============


**Operator Logs**

Dish manager logs are tagged for filtering purposes. Operator related logs are tagged 
with ``user=operator``. In Kibana, one can filter for operator logs by using the following query:

.. code-block:: none

   ska_tags_field.user : "operator"
