@VTS-226
Feature: Dish LMC acceptance tests
    @XTP-28438 @XTP-811  @XTP-16286
    Scenario Outline: LMC Reports on the success of Tracking with programTrackTable
        Given dish_manager dishMode reports OPERATE
        And dish_manager ConfiguredBand reports B2
        And I wrote to programTrackTable on dish_manager
        When I call command Track on dish Manager 
        Then pointingState should report TRACK
        When I call command TrackStop on dish Manager 
        Then pointingState should report READY
        