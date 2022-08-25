"""General utils for testing"""
from tango import CmdArgType


def retrieve_attr_value(dev_proxy, attr_name):
    """Get the attribute reading from device"""
    current_val = dev_proxy.read_attribute(attr_name)
    if current_val.type == CmdArgType.DevEnum:
        current_val = getattr(dev_proxy, attr_name).name
    elif current_val.type == CmdArgType.DevState:
        current_val = str(current_val.value)
    else:
        current_val = current_val.value
    return current_val
