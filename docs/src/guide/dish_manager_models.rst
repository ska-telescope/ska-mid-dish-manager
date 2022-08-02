=================
DishManager Model
=================

Every transition is managed by DishManager's component manager through the model. The model is a mode transition network
specifying:

* the allowed modes Dish has to be in to execute a command.
* the respective values the attributes in the underlying devices should report to reflect a particular value and the aggregated attributes on Dish.

The image below is a dishMode transition diagram showing the mode transitions from their respective commands.

.. image:: ../images/DishModeTransition.png
  :width: 50%
  :height: 600
  :alt: Dish Mode Transitions
