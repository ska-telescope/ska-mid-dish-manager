@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-3090 @XTP-811
    Scenario: Test dish stow request
        Given dish_manager dishMode reports any allowed dishMode for SetStowMode command
        When I issue SetStowMode on dish_manager
        Then dish_manager dishMode should report STOW
        And dish_structure operatingMode should report STOW
        And dish_manager and dish_structure elevation should be greater than or equal to 85
        And dish_manager and dish_structure azimuth should remain in the same position
        And dish_manager pointingState should be NONE
        And dish_manager dish state should be DISABLE
        And dish_manager and dish_structure should report the same achieved elevation position
