@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-6269 @XTP-15470 @XTP-811 @L2-4697 @XTP-16286
    Scenario: LMC Reports DSH Capability Standby in LP Mode
        Given dish_manager dishMode reports STANDBY-LP
        And spfrx b2CapabilityState reports STANDBY
        And spf b2CapabilityState reports STANDBY
        Then dish_manager b2CapabilityState should report STANDBY
