@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-6270 @XTP-811 @L2-4700
    Scenario: LMC Report DSH Capability Configure
        Given dish_manager dishMode reports STANDBY_FP
        When I issue ConfigureBand2 on dish_manager
        Then dish_manager dishMode should have reported CONFIG briefly
        And spf b2CapabilityState should report OPERATE
        And spfrx b2CapabilityState should report OPERATE or CONFIGURE
        And dish_manager b2CapabilityState should have reported CONFIGURE briefly
