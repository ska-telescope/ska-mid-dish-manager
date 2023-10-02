@VTS-226
Feature: Dish LMC acceptance tests

	@XTP-15469 @XTP-15467 @XTP-811 @L2-5125 @XTP-16286
	Scenario Outline: LMC captures data in the configuredBand
		Given dish_manager reports <dish_mode>
		And dish_manager configuredBand is <band_number>
		Then spfrx operatingMode should report <expected_operating_mode>
		And dish_manager capturing and spfrx capturingData attributes should report <value>
		
		    Examples:
		        | dish_mode  | band_number | expected_operating_mode | value |
		        | OPERATE    | 2           | DATA-CAPTURE            | True  |
		        | STANDBY-FP | 2           | DATA-CAPTURE            | True  |
