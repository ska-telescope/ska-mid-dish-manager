@VTS-226
Feature: Dish LMC acceptance tests
	
	@XTP-15468 @XTP-15467 @XTP-811 @L2-5125 @XTP-16286
	Scenario: LMC does not capture data in STANDBY-FP mode with no band
		Given dish_manager has no configuredBand
		And dish_manager reports STANDBY-FP
		Then spfrx operatingMode should report STANDBY
		And dish_manager capturing and spfrx capturingData attributes should report False
