# flake8: noqa
"""Set up tango logging."""

from tango import log4tango

# Longer logs, like LRC IDs get truncated by Tango, bumping MAX_ARG_LEN helps debugging
log4tango.MAX_ARG_LEN = 200  # noqa: F811