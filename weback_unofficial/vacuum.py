from weback_unofficial.client import WebackApi, BaseDevice

CLEAN_MODE_AUTO = 'AutoClean'
CLEAN_MODE_EDGE = 'EdgeClean'
CLEAN_MODE_SPOT = 'SpotClean'
CLEAN_MODE_SINGLE_ROOM = 'RoomClean'
CLEAN_MODE_STOP = 'Standby'

FAN_DISABLED = 'Pause'
FAN_SPEED_NORMAL = 'Normal'
FAN_SPEED_HIGH = 'Strong'
FAN_SPEEDS = {FAN_SPEED_NORMAL, FAN_SPEED_HIGH}

CHARGE_MODE_RETURNING = 'BackCharging'
CHARGE_MODE_CHARGING = 'Charging'
CHARGE_MODE_DOCK_CHARGING = 'PileCharging'
CHARGE_MODE_DIRECT_CHARGING = 'DirCharging'
CHARGE_MODE_IDLE = 'Hibernating'

MOP_DISABLED = 'None'
MOP_SPEED_LOW = 'Low'
MOP_SPEED_NORMAL = 'Default'
MOP_SPEED_HIGH = 'High'
MOP_SPEEDS = {MOP_SPEED_LOW, MOP_SPEED_NORMAL, MOP_SPEED_HIGH}

ROBOT_ERROR = "Malfunction"

CLEANING_STATES = {CLEAN_MODE_AUTO, CLEAN_MODE_EDGE, CLEAN_MODE_SPOT, CLEAN_MODE_SINGLE_ROOM}
CHARGING_STATES = {CHARGE_MODE_CHARGING, CHARGE_MODE_DOCK_CHARGING, CHARGE_MODE_DIRECT_CHARGING}
DOCKED_STATES = {CHARGE_MODE_IDLE, CHARGE_MODE_CHARGING, CHARGE_MODE_DOCK_CHARGING, CHARGE_MODE_DIRECT_CHARGING}

class CleanRobot(BaseDevice):
    def __init__(self, name, client, shadow=None, description=None, nickname=None):
        super().__init__(name, client, shadow=shadow, description=description, nickname=nickname)

    def turn_on(self):
        return self.publish_single('working_status', CLEAN_MODE_AUTO)

    def turn_off(self):
        return self.publish_single('working_status', CHARGE_MODE_RETURNING)

    def return_home(self):
        return self.turn_off()

    def stop(self):
        return self.publish_single('working_status', CLEAN_MODE_STOP)

    def setFan(self, mode: str):
        if not mode in FAN_SPEEDS:
            self.raise_invalid_value(FAN_SPEEDS)
        
        self.publish_single('fan_status', mode)
    
    def setMop(self, mode: str):
        if not mode in MOP_SPEEDS:
            self.raise_invalid_value(MOP_SPEEDS)
        self.publish_single('water_level', mode)

    @property
    def is_available(self):
        return True if self.shadow.get('connected') == 'false' else True

    @property
    def clean_tine(self) -> int:
        return self.shadow.get('clean_time')

    @property
    def battery_level(self) -> int:
        return self.shadow.get('battery_level')

    @property
    def current_mode(self) -> str:
        return self.shadow.get('working_status')

    @property
    def error(self) -> str:
        return self.shadow.get('error_info')

    @property
    def is_cleaning(self) -> bool:
        return True if self.current_mode in CLEANING_STATES else False
    
    @property
    def is_docked(self) -> bool:
        return True if self.current_mode in DOCKED_STATES else False
    
    @property
    def is_paused(self) -> bool:
        return True if self.current_mode == CLEAN_MODE_STOP else False
    
    @property
    def is_idle(self) -> bool:
        return not (self.is_docked or self.is_cleaning or self.is_paused \
            or self.is_returning or self.is_error)
    
    @property
    def is_returning(self) -> bool:
        return True if self.current_mode == CHARGE_MODE_RETURNING else False

    @property
    def is_error(self) -> bool:
        return True if self.current_mode == ROBOT_ERROR else False

    @property
    def state(self):
        if self.current_mode == None:
            return 'unknown'
        if self.is_error:
            return 'error'
        if self.is_cleaning:
            return 'cleaning'
        if self.is_docked:
            return 'docked'
        if self.is_returning:
            return 'returning'
        if self.is_paused:
            return 'paused'
        return 'idle'
