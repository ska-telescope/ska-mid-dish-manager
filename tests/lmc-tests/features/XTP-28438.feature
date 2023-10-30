@VTS-226
Feature: Dish LMC acceptance tests
    @XTP-28438 @XTP-811  @XTP-16286
    Scenario Outline: LMC Reports on the success of Tracking with programTrackTable
        Given dish_manager dishMode reports OPERATE
        And dish_manager ConfiguredBand reports B2
        And I have set the programTrackTable on dish_manager
        When I call command <dm_command> on dish Manager 
        Then pointingState should report <pointing_state>

            Examples:
                 | dm_command | pointing_state |
                 | Track      | TRACK          |
                 | TrackStop  | READY          |