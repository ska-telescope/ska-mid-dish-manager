@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-3090 @XTP-811 @XTP-16286
    Scenario: Test dish stow request
        Given dish_manager dishMode reports any allowed dishMode for SetStowMode command
        When I issue SetStowMode on dish_manager
        Then dish_manager dishMode should report STOW
        And dish_structure operatingMode should report STOW
        And dish_manager and dish_structure should report the same achieved elevation position
