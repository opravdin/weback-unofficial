from weback_unofficial.client import WebackApi, BaseDevice

# uses a weekly plan (Mon, Tues, Wed, Thur, Fri, Sat, Sun)
AUTO = 'auto'
# uses the temperature you set in the set_temp property
MANUAL = 'hand'

WORKING_MODES = {AUTO, MANUAL}
# temperature is always times two (e.g. 25 degrees = 50 degrees in shadow object)
TEMP_MULTIPLIER = 2

# temperature is given like 250, which means 25.0 degrees
TEMP_DISPLAY_DIVIDER = 10

CURRENT_TEMPERATURE = 'air_tem'
GOAL_TEMPERATURE = 'set_tem'
CONNECTED = 'connected'
WORKMODE = 'workmode'
WORKING_STATUS = 'working_status'


class Thermostat(BaseDevice):
    def __init__(self, name, client, shadow=None, description=None, nickname=None):
        super().__init__(name, client, shadow=shadow, description=description, nickname=nickname)

    def setMode(self, mode: str):
        if not mode in WORKING_MODES:
            self.raise_invalid_value(WORKING_MODES)
        self.publish_single('workmode', mode)

    def setTemp(self, temp: str):
        self.setMode(MANUAL)
        self.publish_single('set_tem', temp * TEMP_MULTIPLIER)


    @property
    def is_available(self):
        return True if self.shadow.get(CONNECTED) == 'false' else True

    @property
    def mode(self):
        return self.shadow.get(WORKMODE)

    @property
    def temperature(self):
        return self.shadow.get(CURRENT_TEMPERATURE) / TEMP_DISPLAY_DIVIDER

    @property
    def goal_temperature(self):
        return self.shadow.get(GOAL_TEMPERATURE) / TEMP_MULTIPLIER

    @property
    def is_heating(self):
        return True if self.shadow.get(WORKING_STATUS) == 'on' else False    

    @property
    def autosettings(self):
        return {
            "Mon": self.format_auto_settings('Mon'),
            "Tue": self.format_auto_settings('Tues'),
            "Wed": self.format_auto_settings('Wed'),
            "Thu": self.format_auto_settings('Thur'),
            "Fri": self.format_auto_settings('Fri'),
            "Sat": self.format_auto_settings('Sat'),
            "Sun": self.format_auto_settings('Sun')
        }

    # the shadow object includes a string for every day where the actions are concatenated
    # this function is used to split them up
    # input: "04:50_043C,08:00_030C,17:00_043C,20:00_030C,20:00_030C,20:00_030C"
    # output: [
    #     "04:50_043C",
    #     "08:00_030C",
    #     "17:00_043C",
    #     "20:00_030C",
    #     "20:00_030C",
    #     "20:00_030C"
    # ]
    def format_auto_settings(self, day):
        command_string = self.shadow.get(day)
        commands = command_string.split(',')
        return commands
