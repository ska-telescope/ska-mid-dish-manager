=======================
Tracking on DishManager
=======================

DishManager has attributes and commands that provide for tracking functionality. DishManager does not do any complex conditioning,
validation or caching of inputs related to tracking. Dish Structure Manager is a subcomponent of DishManager that is used for
translating between OPCUA and Tango interfaces for the Dish Structure Controller. The main functionality of DishManager is to
provide an interface to the Dish Structure Controller and aggregate states amongst subdevices to provide a global state of a dish. 

The attributes related to tracking are:

* `trackTableLoadMode` - allows for either loading a `NEW` track table which resets the internal buffer indexes or loading additional tables with `APPEND`
  
  When tables are loaded with APPEND one can expect the `trackTableEndIndex` to increment with the number of points provided.

* `programTrackTable` - the timestamped points of desired azimuth and elevation

  Note that the dish structure controller has spline interpolation between track table points, hence it is not necessary to provide track tables with
  very small time difference between points unless agile maneuvering is required.

* `achievedPointing` - the actual azimuth and elevation (timestamped)

* `trackTableCurrentIndex` - the current position of the internal circular buffer of the dish structure controller
* `trackTableEndIndex` - the end position of the internal circular buffer of the dish structure controller

  The dish structure controller has an internal buffer size of 10000. This maximum size is required to calculate how much space is available. The end index increments in the circular buffer
  as track table are loaded. The number of valid entries in the track table can be calculated according to table_len = (trackTableEndIndex - trackTableCurrentIndex) % 10000 + 1
  Then the space available can be concluded by subtracting table_len from 10000. As points in the table are consumed, the `trackTableCurrentIndex` moves closer towards the `trackTableEndIndex`.

* `pointingState` - the current pointing state of the dish

The commands related to tracking are:

* `Track()` - command to start tracking

  There must be valid entries loaded into the track table for a track to start successfully. Once the tables are consumed in the track table, the dish stops tracking. If once wishes to 
  maintain tracking state, the track table must be replenished with valid entries to track - "valid" in the sense that the timestamp is in the future.

* `TrackStop()` - command to stop tracking


See `abort documentation`_ for discussion and flow diagram

.. warning::
    An ongoing STOW can be interrupted if Abort is triggered. SetStowMode can
    be requested again to resume STOW movement. STOW is primarily a SAFETY request
    is the user's responsibility to avoid unintended consequences.

.. _documentation: https://developer.skao.int/projects/ska-tango-base/en/latest/concepts/long-running-commands.html
.. _abort documentation: https://confluence.skatelescope.org/x/cMiJEQ
