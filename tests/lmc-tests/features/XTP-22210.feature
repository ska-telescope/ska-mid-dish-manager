@L2-5128
Feature: Dish LMC handle track stop command
	
	@XTP-22210
	Scenario: Test Dish TrackStop command
		Given dish_manager dishMode reports OPERATE
		And dish_manager pointingState reports TRACK or SLEW
		And dish_structure pointingState reports TRACK or SLEW
		When I issue TrackStop on dish_manager
		Then dish_manager pointingState should transition to READY
		And dish_structure pointingState should transition to READY
