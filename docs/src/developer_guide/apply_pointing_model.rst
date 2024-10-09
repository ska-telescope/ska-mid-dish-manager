==================================
ApplyPointingModel on DishManager
==================================

*ApplyPointingModel* (a Fast Command) is a command that accepts a JSON input to update PointingModelParams (band 1 - band 5b). It
does this by updating the 18 coefficients for the band in question found in the JSON input.
Note:

* All 18 coefficients need to be present in the JSON object.

* Units need to be correct and present for each coefficients (deg or arcsec).

* The values of the coefficients need to adhere to this range [-2000, 2000].

* The Dish ID should be correct. (Necessary so that the write dish is written too).

* Each time the command is called all parameters will get updated not just the ones that have been modified.

**Command Parameters: Structure of JSON Object**

It is important to note that the only properties assessed by the command
are:

* antenna 
* band
* coefficients

  * value
  * unit


In essence if the other properties listed in the JSON object are not present then it will not affect the execution 
of the command. An example of the JSON command is shown below:

.. code-block:: json

  {
  "interface": "https://schema.skao.int/ska-mid-dish-gpm/1.2",
  "antenna": "SKA063",
  "band": "Band_2",
  "attrs": {
    "obs_date_times": [
      "2021-03-11T12:34:56Z"
    ],
    "eb_ids": [
      "eb-t0001-20231018-00004",
      "eb-t0001-20231018-00005"
    ],
    "analysis_script": "SKAO SysSci pointing fitting script v0.5",
    "analysis_date_time": "2024-09-06T13:30:18Z",
    "comment": "perhaps a comment from the operator?"
  },
  "coefficients": {
    "IA": {
      "value": -491.05237180985154,
      "units": "arcsec",
      "stderr": 29.839937537191794,
      "used": true
    },
    "CA": {
      "value": -46.49438759990891,
      "units": "arcsec",
      "stderr": 44.321354844319295,
      "used": true
    },
    "NPAE": {
      "value": -0.20043883924247693,
      "units": "arcsec",
      "stderr": 35.59750461448338,
      "used": true
    },
    "AN": {
      "value": 6.303488540553789,
      "units": "arcsec",
      "stderr": 2.312270797023683,
      "used": true
    },
    "AN0": {
      "value": 0.0,
      "units": "arcsec",
      "stderr": null,
      "used": false
    },
    "AW": {
      "value": 16.015694895168707,
      "units": "arcsec",
      "stderr": 2.3411331674188256,
      "used": true
    },
    "AW0": {
      "value": 0.0,
      "units": "arcsec",
      "stderr": null,
      "used": false
    },
    "ACEC": {
      "value": 11.97440290133107,
      "units": "arcsec",
      "stderr": 4.465286689575499,
      "used": true
    },
    "ACES": {
      "value": -3.7385420287177227,
      "units": "arcsec",
      "stderr": 4.112809842198496,
      "used": true
    },
    "ABA": {
      "value": 0.0,
      "units": "arcsec",
      "stderr": null,
      "used": false
    },
    "ABphi": {
      "value": 0.0,
      "units": "deg",
      "stderr": null,
      "used": false
    },
    "IE": {
      "value": 1655.986889730121,
      "units": "arcsec",
      "stderr": 43.79485227727362,
      "used": true
    },
    "ECEC": {
      "value": -145.2842284526637,
      "units": "arcsec",
      "stderr": 29.53868683296845,
      "used": true
    },
    "ECES": {
      "value": -26.760848137365375,
      "units": "arcsec",
      "stderr": 35.15891823374198,
      "used": true
    },
    "HECE4": {
      "value": 0.0,
      "units": "arcsec",
      "stderr": null,
      "used": false
    },
    "HESE4": {
      "value": 0.0,
      "units": "arcsec",
      "stderr": null,
      "used": false
    },
    "HECE8": {
      "value": 0.0,
      "units": "arcsec",
      "stderr": null,
      "used": false
    },
    "HESE8": {
      "value": 0.0,
      "units": "arcsec",
      "stderr": null,
      "used": false
    }
    },
    "rms_fits": {
      "xel_rms": {
        "value": 9.117857666551563,
        "units": "arcsec"
      },
      "el_rms": {
        "value": 9.354130675173373,
        "units": "arcsec"
      },
      "sky_rms": {
        "value": 13.06273666257238,
        "units": "arcsec"
      }
    }
  }

**Command Feedback: A collection to command responses and their meanings**

.. list-table:: Command Feeback
   :header-rows: 1

   * - JSON Object
     - Command Response
     - Status Code
   * - Correct Properties
     - Successfully wrote the following values <coefficients> to band <band> on DS
     - ResultCode.OK
   * - Missing Coefficients 
     - Coefficients are missing. The coefficients found in the JSON object were <coeff_keys>
     - ResultCode.REJECTED
   * - Unsupported Band 
     - Unsupported Band: <band>
     - ResultCode.REJECTED
   * - Coefficient Value Out of Range 
     - Value <value> for key '<key>' is out of range [<min_value>, <max_value>]
     - ResultCode.REJECTED
   * - Incorrect Dish Antenna/ID 
     - Command rejected. The Dish id <dish_id> and the Antenna's value <antenna_id> are not equal.
     - ResultCode.REJECTED
   * - Lostconnection, Tango: DevFailed
     - <related error message>
     - ResultCode.FAILED
   * - Lostconnection, Invalid JSON
     - <related error message>
     - ResultCode.REJECTED



