@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-6269 @XTP-811 @L2-4697
    Scenario: LMC Report DSH Capability Standby when dishMode is STANDBY_LP
        Given dish_manager dishMode reports STANDBY_LP
        And spfrx b2CapabilityState reports STANDBY
        And spf b2CapabilityState reports STANDBY
        Then dish_manager b2CapabilityState should report STANDBY

    @XTP-6269 @XTP-811 @L2-4697
    Scenario: LMC Report DSH Capability Standby when dishMode is STANDBY_FP
        Given dish_manager dishMode reports STANDBY_FP
        When I issue ConfigureBand2 on dish_manager
        Then spfrx b2CapabilityState should report OPERATE
        And spf b2CapabilityState should report OPERATE
        And dish_manager b2CapabilityState should report STANDBY
