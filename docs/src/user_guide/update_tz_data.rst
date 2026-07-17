===========================================
Update SPFRx time zone data via DishManager
===========================================

*UpdateTZData* (a Long Running Command) refreshes the time zone (TZ) data used by
SPFRx. When invoked, DishManager downloads the latest TZ data file, base64
encodes it and forwards it to SPFRx via the SPFRx *UpdateTZData* command.

The command takes no arguments. The location of the TZ data file is read from the
``TZ_DATA_URL`` environment variable on the DishManager device server, so no URL is
passed by the caller.

Because it is a long running command, the call returns immediately with a command
ID. The final outcome is reported asynchronously on the ``lrcFinished`` attribute.

**Note**:

* SPFRx must not be ignored (``ignoreSpfrx`` must be ``False``).

How it works
^^^^^^^^^^^^

When *UpdateTZData* is invoked, DishManager:

#. Reads the download URL from the ``TZ_DATA_URL`` environment variable.

#. Downloads the TZ data file from that URL.

#. Base64 encodes the downloaded file.

#. Forwards the encoded data to SPFRx via its *UpdateTZData* command.

Command Feedback: A collection of command responses and their meanings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. list-table:: Command Feedback
   :header-rows: 1

   * - Scenario
     - Command Response
     - Status Code
   * - TZ data successfully uploaded
     - UpdateTZData completed. TZ data successfully uploaded to SPFRx.
     - ResultCode.OK
   * - SPFRx is ignored
     - UpdateTZData rejected. SPFRx is ignored, cannot upload TZ data.
     - ResultCode.FAILED
   * - ``TZ_DATA_URL`` not set or empty
     - UpdateTZData failed. Environment variable 'TZ_DATA_URL' is not set or is empty; cannot determine where to download the TZ data from.
     - ResultCode.FAILED
   * - Download failed
     - UpdateTZData failed. Could not download TZ data from <url>.
     - ResultCode.FAILED
   * - Encoding failed
     - UpdateTZData failed. Could not base64 encode the downloaded TZ data.
     - ResultCode.FAILED
   * - SPFRx rejected the upload
     - UpdateTZData failed. SPFRx rejected the TZ data upload: <reason>
     - ResultCode.FAILED
   * - Unexpected error calling SPFRx
     - UpdateTZData failed. Unexpected error while calling UpdateTZData on SPFRx.
     - ResultCode.FAILED
