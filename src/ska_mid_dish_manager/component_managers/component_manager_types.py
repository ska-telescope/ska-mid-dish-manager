from ska_mid_dish_manager.component_managers.b5dc_cm import B5DCComponentManager
from ska_mid_dish_manager.component_managers.ds_cm import DSComponentManager
from ska_mid_dish_manager.component_managers.spf_cm import SPFComponentManager
from ska_mid_dish_manager.component_managers.spfrx_cm import SPFRxComponentManager
from ska_mid_dish_manager.component_managers.wms_cm import WMSComponentManager

type SubComponentManagers = (
    B5DCComponentManager
    | DSComponentManager
    | SPFComponentManager
    | SPFRxComponentManager
    | WMSComponentManager
)
