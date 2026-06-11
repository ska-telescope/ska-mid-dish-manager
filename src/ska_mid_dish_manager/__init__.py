import numpy as np
from tango import log4tango

# Remove repeated "float64" from logs
np.set_printoptions(legacy="1.25")

# Longer logs, like LRC IDs get truncated by Tango, bumping MAX_ARG_LEN helps debugging
log4tango.MAX_ARG_LEN = 200  # noqa: F811
