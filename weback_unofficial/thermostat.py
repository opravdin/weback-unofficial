from weback_unofficial.client import WebackApi, BaseDevice

# uses a weekly plan (Mon, Tues, Wed, Thur, Fri, Sat, Sun)
AUTO = 'auto'
# uses the temperature you set in the set_temp property
MANUAL = 'hand'

WORKING_MODES = {AUTO, MANUAL}
TEMP_MULTIPLIER = 2

class Thermostat(BaseDevice):
    def __init__(self, name, client, shadow=None, description=None, nickname=None):
        super().__init__(name, client, shadow=shadow, description=description, nickname=nickname)

    def setMode(self, mode: str):
        if not mode in WORKING_MODES:
            self.raise_invalid_value(WORKING_MODES)
        
        print(mode)
        self.publish_single('workmode', mode)

    def setTemp(self, temp: str):
        self.setMode(MANUAL)
        self.publish_single('set_tem', temp * TEMP_MULTIPLIER)


    @property
    def is_available(self):
        return True if self.shadow.get('connected') == 'false' else True

    @property
    def mode(self):
        return self.shadow.get('workmode')

    @property
    def temperature(self):
        return self.shadow.get('air_tem') / 10

    @property
    def goal_temperature(self):
        return self.shadow.get('set_tem') / TEMP_MULTIPLIER

    @property
    def is_heating(self):
        return True if self.shadow.get('working_status') == 'on' else False    

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

    def format_auto_settings(self, day):
        command_string = self.shadow.get(day)
        commands = command_string.split(',')
        return commands
