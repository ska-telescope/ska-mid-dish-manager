@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-5414 @XTP-811
    Scenario: Test dish pointing request
        Given dish_manager dishMode reports OPERATE
        And dish_manager pointingState reports READY
        When I issue Track on dish_manager to move azimuth and elevation by 10 degrees each
        Then the difference between actual and desired azimuth should be less than or equal to the configured threshold
        And the difference between actual and desired elevation should be less than or equal to the configured threshold
        And dish_manager pointingState should transition to TRACK on target
        And dish_manager and dish_structure should report the same achieved pointing position
