===============
Troubleshooting
===============


**Operator Logs**

Dish manager logs are tagged for filtering purposes. Operator related logs are tagged 
with ``user=operator``. This allows operators to filter logs to find relevant information 
when troubleshooting. In Kibana, you can use the following query to filter for operator logs:
.. code-block:: none

   ska_tags_field.user : "operator"
