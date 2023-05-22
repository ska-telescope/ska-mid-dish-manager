@VTS-226
Feature: Dish LMC acceptance tests
	
	@XTP-15465 @XTP-811 @XTP-15464 @XTP-3310 @XTP-3392 @XTP-5773 @XTP-16286
	Scenario: Test STANDBY-LP to STANDBY-FP
		Given dish_manager dishMode reports STANDBY-LP
		When I issue SetStandbyFPMode on dish_manager
		Then dish_manager dishMode should report STANDBY-FP
		And dish_structure operatingMode and powerState should report STANDBY-FP and FULL-POWER
		And spf operatingMode and powerState should report OPERATE and FULL-POWER
		And spfrx operatingMode should report either DATA-CAPTURE or STANDBY
