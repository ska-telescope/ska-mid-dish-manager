=========================
Tracking with DishManager
=========================

DishManager has attributes and commands that provide functionality for tracking. DishManager does not do any complex conditioning,
validation or caching of inputs related to tracking. Dish Structure Manager is a subcomponent of DishManager that is used for
translating between OPCUA and Tango interfaces for the Dish Structure Controller. The main functionality of DishManager is to
provide an interface to the Dish Structure Controller and aggregate states amongst subdevices to provide a global state of a dish. 

The attributes related to tracking are:

* **trackTableLoadMode**

  This attribute is used in conjuntion with ``programTrackTable`` to either load a ``NEW`` track table or 
  load additional tables with ``APPEND``. When tables are loaded with ``NEW``, the ``trackTableCurrentIndex`` is reset to 0, the track table is loaded at beginning of the 
  buffer and ``trackTableEndIndex`` points to the last entry of the track table.
  When tables are loaded with ``APPEND``, one can expect the ``trackTableEndIndex`` to increment with the number of points provided.
  The dish structure controller has a circular buffer of length 10000. The current index in the table, represented by ``trackTableCurrentIndex`` *chases* the
  end index, represented by ``trackTableEndIndex`` when tracking is **active**. One must be aware of this limitation to ensure that there is enough space for
  appending additional tables.

* **programTrackTable**

  This attribute contains the timestamped points of desired azimuth and elevation that the dish structure controller will try to achieve. Note that the dish structure controller performs 
  interpolation between track table points, hence it is not necessary to provide track tables with short time intervals between points unless agile maneuvering cannot be achieved.

* **achievedPointing**

  This is the actual azimuth and elevation achieved by the dish structure controller (timestamped).

* **trackTableCurrentIndex**
  
  The current position of the internal circular buffer of the dish structure controller. This index advances with time while tracking is active.

* **trackTableEndIndex**

  The end position of the internal circular buffer of the dish structure controller. This represents the last point loaded that should be tracked. The distance
  between the ``trackTableCurrentIndex`` and ``trackTableEndIndex`` represent the valid track table entries that shall be tracked when tracking is active. If 
  the track table points are in the past when being processed (when tracking is active), then the points will be ignored and the next valid point will be used. The circular
  buffer size is defined as 10000. As the buffer type is circular, this maximum size is necessary to calculate the space available at any point in time in the buffer.
  The space available can be calculated as follows: 
  
  .. code-block:: python
    
    if trackTableEndIndex == trackTableCurrentIndex:
        used_space = 0
    else:
        used_space = (trackTableEndIndex - trackTableCurrentIndex) % 10000 + 1

    space_available = 10000 - used_space

* **pointingState** 

  This is the current pointing state:
  
  * READY: dish is not moving
  * SLEW: dish is moving to an initial target
  * TRACK: dish pointing error is within defined tracking tolerance
  * UNKNOWN: when not in above states

  For details on pointing state see `pointing state documentation`_. 

* **Track()** 

  This is the command to start tracking. There must be valid entries loaded into the track table for a track to start successfully. Once the entries are consumed in the track table, 
  the dish stops tracking. If one wishes to maintain tracking state, the track table must be replenished with valid entries to track - *valid* in the sense that the timestamp is not in the past.

* **TrackStop()** 

  This command is used to stop tracking.

.. Note::
    **KAROO simulator:**
    If one encounters an error when loading track tables, it is most likely that the track table buffer is full. 
    One can confirm this from the simulator logs. If a buffer overflow occurs while tracking, then the rate of
    track table loading is greater than the consumption. Note that due to computational jitter timing drift can 
    result in supplying tables faster than they are consumed in long tracking operations. 
    It is advised for the clients to monitor their lead time. The lead time for a track table is defined as the 
    **duration between when the track table is constructed to the start time of the track table block**.
    The lead time should remain fairly constant. If the lead time drifts, it indicates that track tables are being 
    supplied faster or slower than being consumed.
    
    In the KAROO simulator, expired track table entries are only skipped over while tracking
    is **active** i.e. one can fill the buffer with invalid/expired entries and cause a buffer overflow. It is only while
    tracking is active that the internal buffer is consumed (and discarded if expired) - there is no continuous
    supervision of the track table. 

.. _pointing state documentation: https://confluence.skatelescope.org/display/SWSI/Dish+States+and+Modes+ICD
