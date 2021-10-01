# Unofficial WeBack API Client  
This client was developed using reverse engineering of the Android application and traffic analysis. There is no guarantee that this API will continue to work. However, it will be quite easy to fix in case of any errors/issues/changes as the WeBack servers are only responsible for gaining access to the API (Amazon Cognito, to be precise).  

## Usage
```
pip3 install weback-unofficial
```
### Authentication
First of all, you need to choose whether you want to manage your session manually or with this package.
```python
from weback_unofficial.client import WebackApi
import boto3

# Method 1: make this package keep session itself
# If you are authenticating via e-mail, you may need to provide login as '+{country_code}-{email}' format, e.g. '+7-youmail@address.tld'
client = WebackApi('+7-1234567890', '<your_password>')
session = client.get_session() # Returns Amazon Session from boto3 package 


# Method 2: manage by yourself
client = WebackApi()
weback_data = client.auth('+7-1234567890', '<your_password>') # Returns creds for auth in AWS

region = weback_data['Region_Info']
client = boto3.client('cognito-identity', region)

# Here you will receive session data & expiration time (usually 1 day)
# Don't forget to keep it alive!
aws_creds =  client.get_credentials_for_identity(
    IdentityId=weback_data['Identity_Id'], 
    Logins={
        "cognito-identity.amazonaws.com": weback_data['Token']
    }
)
session = boto3.Session(
    aws_access_key_id=aws_creds['Credentials']['AccessKeyId'],
    aws_secret_access_key=aws_creds['Credentials']['SecretKey'],
    aws_session_token=aws_creds['Credentials']['SessionToken'],
    region_name=region
)

```

### Manipulating with vacuum robot (example)
```python
devices = client.device_list()
device_name = devices[0]['Thing_Name']
# Method 1: via helper functions
# Get device shadow status
client.get_device_shadow(device_name)
# Get device description: https://docs.aws.amazon.com/iot/latest/apireference/API_DescribeThing.html
client.get_device_description(device_name)
# Publish message for device
client.publish_device_msg(device_name, {"working_status": "AutoClean"})

# Method 2: via Vacuum class
vacuum = CleanRobot(device_name, self.client)
vacuum.update()
print(vacuum.state)
print(vacuum.current_mode)

vacuum.turn_on()
vacuum.stop()
vacuum.return_home()

# Method 3: by yourself
# Get device shadow status
client = session.client('iot-data')
resp = client.get_thing_shadow(thingName=device_name)
shadow = json.loads(resp['payload'].read())
print("Attributes:")
pp = pprint.PrettyPrinter(indent=1)
pp.pprint(shadow['state']['reported'])

# Start up vacuum cleaner
client = session.client('iot-data')
topic = f"$aws/things/{device_name}/shadow/update"
# See more MQTT commands below
payload = {
    'state': {
        'desired': {
            "working_status": "AutoClean"
        }
    }
}
resp = client.publish(topic=topic, qos = 0, payload = json.dumps(payload))
print(resp)
```

## API usage cycle description
I implemented a minimum number of entry points to activate the vacuum cleaner robot. There are definitely other entry points, but they're either not necessary or I don't have devices to check them. 
* Authorization by username and password. If you use the phone number as a login, provide it in the format {country code}-{number} (e.g. +7-1234567890 if you are from Russia). The server will return the data for access via Amazon Cognito.
* Authorization in Amazon API ([boto3 method](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cognito-identity.html#CognitoIdentity.Client.get_credentials_for_identity))
    * Logins format is {"cognito-identity.amazonaws.com": weback_data['Token']}
* Device list receiving (via WeBack's Amazon Lambda)
* Fetching device status via [Shadow](https://docs.aws.amazon.com/iot/latest/developerguide/API_GetThingShadow.html) ([boto3 method](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iot-data.html#IoTDataPlane.Client.get_thing_shadow))
* OR
* Controlling device via [MQTT publish](https://docs.aws.amazon.com/iot/latest/apireference/API_iotdata_Publish.html) on f"$aws/things/{device_name}/shadow/update" ([boto3 method](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/iot-data.html#IoTDataPlane.Client.publish))

## API description
For each WeBack-related request the method of its call with or without this client is described.
This package also contains several helper methods to simplify the work with the API.

### Authorization
```
POST https://www.weback-login.com/WeBack/WeBack_Login_Ats_V3
Payload: {
    "App_Version":"android_3.9.3", # App version
    "Password":"a57da57da57da57da57da57da57da57d", # Password MD5 hash
    "User_Account":"+7-1234567890"
}

Response example: {
  "Request_Result": "success",
  "Identity_Pool_Id": "POOL_ID",
  "Developer_Provider_Name": "Login_WeBack_AP_SOUTHEAST_1",
  "End_Point": "ENDPOINT",
  "Identity_Id": "ID",
  "Token": "TOKEN",
  "Token_Duration": 86400,
  "Region_Info": "ap-southeast-1",
  "Configuration_Page_URL": "URL",
  "Discovery_Page_URL": "URL",
  "Customer_Service_Card_URL": "URL",
  "Thing_Register_URL": "URL",
  "Thing_Register_URL_Signature": "URL"
}
```

### Fetching device list
```
AWS Lambda name: Device_Manager_V2
Payload: {
    "Device_Manager_Request":"query",
    "Identity_Id":"<Identity_Id>",
    "Region_Info":"<Region_Info>"
}

Response example: {
    "Device_Manager_Request": "query",
    "Request_Result": "success",
    "Request_Cotent": [{
        "Thing_Name": "device-name-plus-mac-address",
        "Thing_Nick_Name": "your-device-nick-name",
        "Image_Url": "image-url"
    }]
}
```

## MQTT Payload
You should provide payload like this

```
    payload = {
        'state': {
            'desired': {
                "<Attribute>": "<Status>"
            }
        }
    }
```

Here "Attribute" and "Status" is one of the payload values from the next sections. I'm not sure if this is suitable for all devices, but my robot vacuum cleaner reacts perfectly to them.

## List of MQTT attributes
You can get Shadow status of your device and try to manipulate the parameters included in it (the keys are usually the same).  
Currently I have found just some of them: (related to my robot vacuum)
* fan_status
    * ROBOT_CTRL_SPEED_NORMAL("Normal"),
    * ROBOT_CTRL_SPEED_STRONG("Strong"),
* working_status - Try "ROBOT_CTRL_" ENUMs. I tested *Standby, BackCharging*, *MopClean* and *SmartClean*. Last one works both with mop and vacuum modes.
* water_tank_shift and water_level - Same parameters (apparently), but the specific attribute depends on the robot. These values are suitable for "water_level" in my case:
    * ROBOT_WATER_TANK_LOW("Low"),
    * ROBOT_WATER_TANK_DEFAULT("Default"),
    * ROBOT_WATER_TANK_HIGH("High")  

## List of all MQTT messages 
Grabbed from ENUMs in code. 

```
ROBOT_CTRL_FRONT("MoveFront"),
ROBOT_CTRL_BACK("MoveBack"),
ROBOT_CTRL_LEFT("MoveLeft"),
ROBOT_CTRL_RIGHT("MoveRight"),
ROBOT_CTRL_STOP("MoveStop"),
ROBOT_NEW_CTRL_FRONT("move_front"),
ROBOT_NEW_CTRL_BACK("move_back"),
ROBOT_NEW_CTRL_LEFT("move_left"),
ROBOT_NEW_CTRL_RIGHT("move_right"),
ROBOT_NEW_CTRL_STOP("move_stop"),
ROBOT_CTRL_CLEAN_STOP("Standby"),
ROBOT_CTRL_CLEAN_CHARGE("BackCharging"),
ROBOT_CTRL_CLEAN_STOP2("Stop"),
ROBOT_CTRL_MODE_SPOT("SpotClean"),
ROBOT_CTRL_MODE_PLAN("PlanClean"),
ROBOT_CTRL_MODE_ROOM("RoomClean"),
ROBOT_CTRL_MODE_AUTO("AutoClean"),
ROBOT_CTRL_MODE_EDGE("EdgeClean"),
ROBOT_CTRL_MODE_FIXED("StrongClean"),
ROBOT_CTRL_MODE_Z("ZmodeClean"),
ROBOT_CTRL_MODE_MOPPING("MopClean"),
ROBOT_CTRL_VACUUM("VacuumClean"),
PLANNING_RECT("PlanningRect"),
ROBOT_CTRL_MODE_PLAN2("SmartClean"),
ROBOT_CTRL_SPEED_NORMAL("Normal"),
ROBOT_CTRL_SPEED_STRONG("Strong"),
ROBOT_CTRL_SPEED_STOP("Pause"),
ROBOT_CTRL_SPEED_SOUND_STOP("Quite"),
ROBOT_CTRL_SPEED_SOUND_STOP_2("Quiet"),
ROBOT_CTRL_SPEED_MAX("Max"),
ROBOT_HAS_NONE_FAN("None"),
ROBOT_WORK_STATUS_STOP("Hibernating"),
ROBOT_WORK_STATUS_STANDBY("Standby"),
ROBOT_LOCATION_ALARM("LocationAlarm"),
PLANNING_LOCATION("PlanningLocation"),
ROBOT_WORK_STATUS_CHARGING_3("Charging"),
ROBOT_WORK_STATUS_WORKING("Cleaning"),
ROBOT_WORK_STATUS_WORK_OVER("Cleandone"),
ROBOT_WORK_STATUS_GO_CHARGE("Backcharging"),
ROBOT_WORK_STATUS_CHARGING("Pilecharging"),
ROBOT_WORK_STATUS_CHARGE_OVER("Chargedone"),
ROBOT_WORK_STATUS_LOWPOWER("Lowpower"),
ROBOT_WORK_STATUS_ERROR("Malfunction"),
ROBOT_WORK_STATUS_CHARGING2("DirCharging"),
ROBOT_WORK_STATUS_CTRL("DirectionControl"),
ROBOT_WATER_TANK_OFF(BucketVersioningConfiguration.OFF),
ROBOT_WATER_TANK_LOW("Low"),
ROBOT_WATER_TANK_DEFAULT("Default"),
ROBOT_WATER_TANK_HIGH("High"),
ROBOT_WATER_TANK_LOW_TAB("Slow"),
ROBOT_WATER_TANK_DEFAULT_TAB("Normal"),
ROBOT_WATER_TANK_HIGH_TAB("Fast"),
ROBOT_HAS_NONE_TANK("None"),
ROBOT_VOICE_CTRL_ON("on"),
ROBOT_VOICE_CTRL_OFF("off"),
ROBOT_CAMERA_UP("Up"),
ROBOT_CAMERA_DOWN("Down"),
ROBOT_CAMERA_LEFT("Left"),
ROBOT_CAMERA_RIGHT("Right"),
ROBOT_POWER_AWAKE("PowerAwake"),
ROBOT_POWER_SLEEP("PowerSleep"),
ROBOT_NO_CHATTING("NoChatting"),
ROBOT_AV_CHATTING("AVChatting"),
ROBOT_VIDEO_CHATTING("VideoChatting"),
ROBOT_AUDIO_CHATTING("AudioChatting"),
ROBOT_SPEED_LOW("Low"),
ROBOT_SPEED_HIGH("High"),
ROBOT_ERROR_NO("NoError"),
ROBOT_ERROR_UNKNOWN("UnknownError"),
ROBOT_ERROR_LEFT_WHEEL("LeftWheelWinded"),
ROBOT_ERROR_RIGHT_WHEEL("RightWheelWinded"),
ROBOT_ERROR_WHEEL_WINDED("WheelWinded"),
ROBOT_ERROR_60017("LeftWheelSuspend"),
ROBOT_ERROR_60019("RightWheelSuspend"),
ROBOT_ERROR_WHEEL_SUSPEND("WheelSuspend"),
ROBOT_ERROR_LEFT_BRUSH("LeftSideBrushWinded"),
ROBOT_ERROR_RIGHT_BRUSH("RightSideBrushWinded"),
ROBOT_ERROR_SIDE_BRUSH("SideBrushWinded"),
ROBOT_ERROR_60031("RollingBrushWinded"),
ROBOT_ERROR_COLLISION("AbnormalCollisionSwitch"),
ROBOT_ERROR_GROUND("AbnormalAntiFallingFunction"),
ROBOT_ERROR_FAN("AbnormalFan"),
ROBOT_ERROR_DUSTBOX2("NoDustBox"),
ROBOT_ERROR_CHARGE_FOUND("CannotFindCharger"),
ROBOT_ERROR_CHARGE_ERROR("BatteryMalfunction"),
ROBOT_ERROR_LOWPOWER("LowPower"),
ROBOT_ERROR_CHARGE("BottomNotOpenedWhenCharging"),
ROBOT_ERROR_CAMERA_CONTACT_FAIL("CameraContactFailure"),
ROBOT_ERROR_LIDAR_CONNECT_FAIL("LidarConnectFailure"),
ROBOT_ERROR_TANK("AbnormalTank"),
ROBOT_ERROR_SPEAKER("AbnormalSpeaker"),
ROBOT_ERROR_NO_WATER_BOX("NoWaterBox"),
ROBOT_ERROR_NO_WATER_MOP("NoWaterMop"),
ROBOT_ERROR_WATER_BOX_EMPTY("WaterBoxEmpty"),
ROBOT_ERROR_FLOATING("WheelSuspendInMidair"),
ROBOT_ERROR_DUSTBOX("DustBoxFull"),
ROBOT_ERROR_GUN_SHUA("BrushTangled"),
ROBOT_ERROR_TRAPPED("RobotTrapped"),
ROBOT_CHARGING_ERROR("ChargingError"),
ROBOT_BOTTOM_NOT_OPENED_WHEN_CHARGING("BottomNotOpenedWhenCharging"),
ROBOT_ERROR_60024("CodeDropped"),
ROBOT_ERROR_60026("NoDustBox"),
ROBOT_ERROR_60028("OperatingCurrentOverrun"),
ROBOT_ERROR_60029("VacuumMotorTangled"),
ROBOT_ERROR_60032("StuckWheels"),
ROBOT_ERROR_STUCK("RobotStuck"),
ROBOT_ERROR_BE_TRAPPED("RobotBeTrapped"),
ROBOT_ERROR_COVER_STUCK("LaserHeadCoverStuck"),
ROBOT_ERROR_LASER_HEAD("AbnormalLaserHead"),
ROBOT_ERROR_WALL_BLOCKED("WallSensorBlocked"),
ROBOT_ERROR_VIR_WALL_FORB("VirtualWallForbiddenZoneSettingError"),
ROBOT_IS_OFF("off"),
ROBOT_IS_ON("on"),
ROBOT_MODE_COLOR("color"),
ROBOT_MODE_WHITE("white"),
UPGRADING_DOWNLOAD_WIFI("upgrading_download_wifi"),
UPGRADING_INSTALL_WIFI("upgrading_install_wifi"),
UPGRADING_DOWNLOAD_VENDOR("upgrading_download_vendor"),
UPGRADING_INSTALL_VENDOR("upgrading_install_vendor"),
UPGRADING_DOWNLOAD_CHASSIS("upgrading_download_chassis"),
UPGRADING_INSTALL_CHASSIS("upgrading_install_chassis"),
UPGRADING_REBOOTING("upgrading_rebooting"),
UNREACHABLE("UnReachable"),
REACHABLE("Reached"),
ROBOT_CTRL_START_UP("StartUp"),
ROBOT_EDGE_DETECT("EdgeDetect"),
UNDISTURB_MODE("undisturb_mode"),
ROBOT_CLEAR_MAP("ClearMap"),
ROBOT_RELOCATION("Relocation");
```
