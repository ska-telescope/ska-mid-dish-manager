@VTS-226
Feature: Dish LMC acceptance tests
    @XTP-28438 @XTP-811  @XTP-16286
    Scenario Outline: LMC Reports on the success of Tracking with programTrackTable
        Given dish_manager dishMode reports OPERATE
        And dish_manager configuredBand reports B2
        And I write to programTrackTable on dish_manager
        When I issue Track on dish_manager 
        Then pointingState should report TRACK
        When I issue TrackStop on dish_manager 
        Then pointingState should report READY
