@VTS-226
Feature: Dish LMC acceptance tests

    @XTP-813 @XTP-811
    Scenario Outline: Test dish lmc mode transitions
        Given dish_manager dishMode reports <initial_dish_mode>
        When I issue <command_name> on dish_manager
        Then dish_manager dishMode and state should report desired_dish_mode and <dish_state>
        And dish_structure operatingMode and powerState should report <ds_operating_mode> and <ds_power_state>
        And spf operatingMode and powerState should report <spf_operating_mode> and <spf_power_state>
        And spfrx operatingMode should report <spfrx_operating_mode>

            Examples:
                | initial_dish_mode | command_name     | dish_state | ds_operating_mode | ds_power_state | spf_operating_mode | spf_power_state | spfrx_operating_mode |
                | STANDBY_LP        | SetStowMode      | DISABLE    | STOW              | LOW_POWER      | STANDBY_LP         | LOW_POWER       | STANDBY              |
                | STOW              | SetStandbyLPMode | STANDBY    | STANDBY_LP        | LOW_POWER      | STANDBY_LP         | LOW_POWER       | STANDBY              |
                | STANDBY_LP        | SetStandbyFPMode | STANDBY    | STANDBY_FP        | FULL_POWER     | OPERATE            | FULL_POWER      | DATA_CAPTURE         |
                | STANDBY_FP        | SetOperateMode   | ON         | POINT             | FULL_POWER     | OPERATE            | FULL_POWER      | DATA_CAPTURE         |
                | OPERATE           | SetStandbyFPMode | STANDBY    | STANDBY_FP        | FULL_POWER     | OPERATE            | FULL_POWER      | DATA_CAPTURE         |
