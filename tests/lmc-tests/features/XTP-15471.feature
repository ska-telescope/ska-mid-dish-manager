@VTS-226
Feature: Dish LMC acceptance tests
	#The Dish lmc behaviour is tested by invoking the commands of the Dish master TANGO device and verifying that dishMode and pointing state transitions as well as dish stow movements are as per the documentation.

	
	@XTP-15471 @XTP-15470 @XTP-811 @L2-4697 @XTP-16286
	Scenario: LMC Reports DSH Capability Standby in FP mode
		Given dish_manager dishMode reports STANDBY-FP
		When I issue ConfigureBand2 on dish_manager
		Then spfrx b2CapabilityState should report OPERATE
		And spf b2CapabilityState should report OPERATE-FULL
		And dish_manager b2CapabilityState should report STANDBY
