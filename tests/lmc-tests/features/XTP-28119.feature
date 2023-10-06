@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-28119 @XTP-811 @XTP-16286
    Scenario Outline: LMC reports static pointing parameters
        Given dish_manager has an attribute <pointing_model_parameter>
        Then <pointing_model_parameter> is a list containing 20 float parameters

            Examples:
                | pointing_model_parameter |
                | band2PointingModelParams |