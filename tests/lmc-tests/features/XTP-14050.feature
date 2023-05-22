@VTS-226
Feature: Dish LMC acceptance tests

	@XTP-14050 @XTP-811 @XTP-15467 @L2-5125 @XTP-16286
	Scenario: LMC does not capture data in STANDBY-LP mode
		Given dish_manager reports STANDBY-LP
		Then spfrx operatingMode should report STANDBY
		And dish_manager capturing and spfrx capturingData attributes should report False
