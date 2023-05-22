@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-6270 @XTP-811 @L2-4700 @XTP-16286
    Scenario: LMC Reports DSH Capability Configure
        Given dish_manager dishMode reports STANDBY-FP
        When I issue ConfigureBand2 on dish_manager
        Then dish_manager dishMode should have reported CONFIG briefly
        And spf b2CapabilityState should report OPERATE-FULL
        And spfrx b2CapabilityState should report OPERATE or CONFIGURE
        And dish_manager b2CapabilityState should have reported CONFIGURING briefly
