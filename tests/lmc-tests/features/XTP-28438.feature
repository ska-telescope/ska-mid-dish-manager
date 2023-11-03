@VTS-226
Feature: Dish LMC acceptance tests
    @XTP-28438 @XTP-811  @XTP-16286
    Scenario Outline: LMC Reports on the success of Tracking with programTrackTable
        Given dish_manager dishMode reports <dish_mode>
        And dish_manager ConfiguredBand reports B<band_number>
        And I have issued programTrackTable on dish_manager
        When I call command <dm_command> on dish Manager 
        Then pointingState should report <pointing_state>

            Examples:
               | dish_mode | band_number | dm_command | pointing_state |
               | OPERATE   | 2           |Track       | TRACK          |
               | OPERATE   | 2           | TrackStop  | READY          |