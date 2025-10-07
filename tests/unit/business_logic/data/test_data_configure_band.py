configure_band_all = """
{
    "dish": {
        "receiver_band": "1",
        "sub_band": 1,
        "spfrx_processing_parameters": [
        {
            "dishes" : ["all"],
            "sync_pps": true,
            "attenuation_pol_x": 10,
            "attenuation_pol_y": 10,
            "saturation_threshold": 0.6,
            "noise_diode" : {
                "psuedo_random" : {
                    "binary_polynomial" : 100,
                    "seed" : 100,
                    "dwell" : 100
                },
                "periodic" : {
                    "period" : 100,
                    "duty_cycle" : 100,
                    "phase_shift" : 100
                }
            }
        }]
    }
}
"""

configure_band_5b_no_subband = """
{
    "dish": {
        "receiver_band": "5b",
        "spfrx_processing_parameters": [
        {
            "dishes" : ["SKA001"]
        }]
    }
}
"""

configure_band_5b_with_subband = """
{
    "dish": {
        "receiver_band": "5b",
        "sub_band": 1,
        "spfrx_processing_parameters": [
        {
            "dishes" : ["SKA001"]
        }]
    }
}
"""

configure_band_invalid_receiver_band = """
{
    "dish": {
        "receiver_band": "10",
        "spfrx_processing_parameters": [
        {
            "dishes" : ["SKA001"]
        }]
    }
}
"""
