@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-5703 @XTP-811 @L2-4621
    Scenario Outline: Test dish lmc band selection
        Given dish_manager dishMode reports <dish_mode>
        When I issue ConfigureBand<band_number> on dish_manager
        Then dish_manager dishMode should report CONFIG briefly
        And dish_structure indexerPosition should report <band_number>
        And spf bandInFocus should report <band_number>
        And spfrx operatingMode should report DATA_CAPTURE
        And spfrx configuredBand should report <band_number>
        And dish_manager configuredBand should report <band_number>
        And dish_manager should report its initial dishMode

            Examples:
                | dish_mode  | band_number |
                | STANDBY_FP | 2           |
                | OPERATE    | 2           |
                | STOW       | 2           |
