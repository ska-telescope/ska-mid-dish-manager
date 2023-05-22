@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-6439 @XTP-811 @L2-4698 @XTP-16286
    Scenario Outline: LMC Reports DSH Capability Operate Degraded
        Given dish_manager dishMode reports <dish_mode> for band<band_number> configuration
        And dish_structure operatingMode reports <operating_mode>
        When I issue ConfigureBand<band_number> on dish_manager
        Then dish_structure indexerPosition should report <band_number>
        And spf b<band_number>CapabilityState should have reported OPERATE-DEGRADED briefly
        And spfrx b<band_number>CapabilityState should report OPERATE
        And dish_manager b<band_number>CapabilityState should have reported OPERATE-DEGRADED briefly

            Examples:
                | dish_mode | operating_mode | band_number |
                | OPERATE   | POINT          | 2           |
                | STOW      | STOW           | 2           |
