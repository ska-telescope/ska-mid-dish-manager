@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-28120 @XTP-811 @XTP-16286
    Scenario Outline: LMC accepts write to static pointing parameters
        Given dish_manager has an attribute <pointing_model_parameter>
        When I write <value> to <pointing_model_parameter>
        Then the dish_structure static pointing model parameters are updated
        And <pointing_model_parameter> should report <new_value>

            Examples:
                | pointing_model_parameter | value      | new_value |
                | band2PointingModelParams | [1.2, 2.3] | [0.0 , 0.0 , 0.0 , 0.0 , 0.0 , 0.0 , 0.0 , 0.0 , 0.0 , 0.0 , 0.0 , 1.2, 0.0 ,0.0 , 0.0 , 0.0 , 0.0 , 0.0 , 0.0 , 2.3] |
