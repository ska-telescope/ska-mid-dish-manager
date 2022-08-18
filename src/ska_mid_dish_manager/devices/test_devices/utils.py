# pylint: disable=invalid-name
"""General utils for test devices"""
import random
import time
from functools import wraps

import tango

from ska_mid_dish_manager.models.dish_enums import (
    Band,
    BandInFocus,
    DishMode,
    IndexerPosition,
)


def random_delay_execution(func):
    """Delay a command a bit"""

    @wraps(func)
    def inner(*args, **kwargs):
        time.sleep(round(random.uniform(1.5, 2.5), 2))
        return func(*args, **kwargs)

    return inner


def set_dish_manager_to_standby_lp(event_store, dish_manager_proxy):
    """Ensure dishManager is in a known state"""
    if dish_manager_proxy.dishMode != DishMode.STANDBY_LP:

        dish_manager_proxy.subscribe_event(
            "dishMode",
            tango.EventType.CHANGE_EVENT,
            event_store,
        )

        # Set it to a known mode, can Stow from any state
        if dish_manager_proxy.dishMode != DishMode.STOW:
            dish_manager_proxy.SetStowMode()
            event_store.wait_for_value(DishMode.STOW, timeout=10)

        dish_manager_proxy.SetStandbyLPMode()
        event_store.wait_for_value(DishMode.STANDBY_LP, timeout=10)


def set_configuredBand_b1():
    """
    Set B1 configuredBand
    Rules:
        DS.indexerposition  == 'IndexerPosition.B1'
        SPFRX.configuredband  == 'Band.B1'
        SPF.bandinfocus == 'BandInFocus.B1'
    """
    ds_device = tango.DeviceProxy("mid_d0001/lmc/ds_simulator")
    spf_device = tango.DeviceProxy("mid_d0001/spf/simulator")
    spfrx_device = tango.DeviceProxy("mid_d0001/spfrx/simulator")

    ds_device.indexerPosition = IndexerPosition.B1
    spf_device.bandinfocus = BandInFocus.B1
    spfrx_device.configuredband = Band.B1


def set_configuredBand_b2():
    """
    Set B2 configuredBand
    Rules:
        DS.indexerposition  == 'IndexerPosition.B2'
        SPFRX.configuredband  == 'Band.B2'
        SPF.bandinfocus == 'BandInFocus.B2'
    """
    ds_device = tango.DeviceProxy("mid_d0001/lmc/ds_simulator")
    spf_device = tango.DeviceProxy("mid_d0001/spf/simulator")
    spfrx_device = tango.DeviceProxy("mid_d0001/spfrx/simulator")

    ds_device.indexerPosition = IndexerPosition.B2
    spf_device.bandinfocus = BandInFocus.B2
    spfrx_device.configuredband = Band.B2
