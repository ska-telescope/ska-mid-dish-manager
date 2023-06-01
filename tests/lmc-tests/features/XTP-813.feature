@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-813 @XTP-811 @XTP-15464 @XTP-3310 @XTP-3392 @XTP-5773 @XTP-16286
    Scenario Outline: Test STANDBY-LP to STOW
        Given dish_manager dishMode reports <initial_dish_mode>
        When I issue <command_name> on dish_manager
        Then dish_manager dishMode should report <desired_dish_mode>
        And dish_structure operatingMode and powerState should report <ds_operating_mode> and <ds_power_state>
        And spf operatingMode and powerState should report <spf_operating_mode> and <spf_power_state>
        And spfrx operatingMode should report <spfrx_operating_mode>
        
            Examples:
                | initial_dish_mode | command_name     | desired_dish_mode | ds_operating_mode | ds_power_state | spf_operating_mode | spf_power_state | spfrx_operating_mode |
                | STANDBY-LP        | SetStowMode      | STOW              | STOW              | LOW-POWER      | STANDBY-LP         | LOW-POWER       | STANDBY              |
                | STOW              | SetStandbyLPMode | STANDBY-LP        | STANDBY-LP        | LOW-POWER      | STANDBY-LP         | LOW-POWER       | STANDBY              |
