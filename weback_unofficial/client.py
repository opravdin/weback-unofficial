import requests
import datetime
import boto3 
import json
from hashlib import md5


class WebackApi(object):

    # boto3 session object
    aws_session = None
    aws_identity_id = None

    # Expiration time of session
    expiration_time = None

    # Creds for WeBack API
    __api_login = None
    __api_password = None
    __api_country_code = None

    def __init__(self, login: str = None, password: str = None, country_code: str = None, aws_session: boto3.Session = None, aws_session_expiration: int = None):
        self.aws_session = aws_session
        self.aws_session_expiration = None
        self.__api_login = login
        self.__api_password = password
        self.__api_country_code = country_code

    def auth(self, login: str = None, password: str = None) -> dict:
        if login is None:
            if self.__api_login is None:
                raise Exception(
                    "Login is not provided via params or class constructor")
            if self.__api_country_code is None:
                login = self.__api_login
            else:
                login = f"+{self.__api_country_code}-{self.__api_login}"
        if password is None:
            if self.__api_password is None:
                raise Exception(
                    "Password is not provided via params or class constructor")
            password = self.__api_password

        req = {
            "App_Version": "android_3.9.3",
            "Password": md5(password.encode('utf-8')).hexdigest(),
            "User_Account": login
        }
        r = requests.post(
            'https://www.weback-login.com/WeBack/WeBack_Login_Ats_V3', json=req)
        resp_content = r.json()
        return resp_content

    def auth_cognito(self, region: str, identity_id: str, token: str) -> dict:
        cl = boto3.client('cognito-identity', region)
        aws_creds = cl.get_credentials_for_identity(
            IdentityId=identity_id,
            Logins={
                "cognito-identity.amazonaws.com": token
            }
        )
        return aws_creds

    def make_session_from_cognito(self, aws_creds: dict, region: str) -> boto3.Session:
        session = boto3.Session(
            aws_access_key_id=aws_creds['Credentials']['AccessKeyId'],
            aws_secret_access_key=aws_creds['Credentials']['SecretKey'],
            aws_session_token=aws_creds['Credentials']['SessionToken'],
            region_name=region
        )
        return session

    def device_list(self, session: boto3.Session = None, identity_id: str = None):
        if (session == None):
            session = self.get_session()
            identity_id = self.aws_identity_id
        
        client = session.client('lambda')
        resp =  client.invoke(
            FunctionName='Device_Manager_V2',
            InvocationType="RequestResponse",
            Payload= json.dumps({
                "Device_Manager_Request":"query",
                "Identity_Id": self.aws_identity_id,
                "Region_Info": session.region_name
            })
        )
        payload = json.loads(resp['Payload'].read())
        return payload['Request_Cotent']

    def get_device_description(self, device_name, session = None):
        if (session == None):
            session = self.get_session()
        client = session.client('iot')
        resp = client.describe_thing(thingName=device_name)
        return resp

    def get_endpoint(self, session):
        iot_client = session.client('iot')
        return "https://" + iot_client.describe_endpoint(endpointType="iot:Data-ATS").get("endpointAddress")

    def get_device_shadow(self, device_name, session = None, return_full = False):
        if (session == None):
            session = self.get_session()
        client = session.client('iot-data', endpoint_url=self.get_endpoint(session))
        resp = client.get_thing_shadow(thingName=device_name)
        shadow = json.loads(resp['payload'].read())
        if return_full:
            return shadow
        return shadow['state']['reported']

    def publish_device_msg(self, device_name, desired_payload = {}, session = None):
        if (session == None):
            session = self.get_session()
        client = session.client('iot-data')
        topic = f"$aws/things/{device_name}/shadow/update"
        payload = {
            'state': {
                'desired': desired_payload
            }
        }
        resp = client.publish(topic=topic, qos = 0, payload = json.dumps(payload))
        return resp

    def is_renewal_required(self):
        return True if (self.expiration_time < datetime.datetime.now(self.expiration_time.tzinfo)) else False

    def get_session(self) -> boto3.Session:
        if self.aws_session and not self.is_renewal_required():
            return self.aws_session

        if not self.__api_login or not self.__api_password:
            raise Exception("You should provide login and password via constructor to use session management")
        
        weback_data = self.auth()
        if weback_data['Request_Result'] != 'success':
            raise Exception(f"Could not authenticate. {weback_data['Fail_Reason']}")

        region = weback_data['Region_Info']
        self.aws_identity_id = weback_data['Identity_Id']

        aws_creds = self.auth_cognito(
            region, weback_data['Identity_Id'], weback_data['Token'])
        self.expiration_time = aws_creds['Credentials'].get('Expiration')

        sess = self.make_session_from_cognito(aws_creds, region)
        self.aws_session = sess
        return sess

class BaseDevice(object):
    client: WebackApi = None
    name: str = None
    shadow: list = {}
    _description: dict = None
    nickname: str = None

    def __init__(self, name: str, client: WebackApi, shadow: list = None, description = None, nickname = None):
        super().__init__()
        self.client = client
        self.name = name
        self.description = description
        self.nickname = nickname if nickname is not None else self.name

        if (shadow):
            self.shadow = shadow

    def update(self):
        """Update device state"""
        shadow = self.client.get_device_shadow(self.name)
        self.shadow = shadow
        return self

    def description(self):
        """Get Amazon IoT device description"""
        if (self._description is not None):
            return self.description
        description = self.client.get_device_description(self.name)
        self._description = description
        return description
    
    def publish(self, desired_payload):
        """Publish 'desired' payload via MQTT"""
        resp = self.client.publish_device_msg(self.name, desired_payload)
        return resp
    
    def publish_single(self, attribute, value):
        """Publish single attribute via MQTT."""
        return self.publish({attribute: value})
    
    def raise_invalid_value(self, valid):
        """Helper: prevent publish unsupported values."""
        raise Exception("Only this set of values supported: %s" % ", ".join(valid))

