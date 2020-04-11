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

    def __init__(self, login: str = None, password: str = None, aws_session: boto3.Session = None, aws_session_expiration: int = None):
        self.aws_session = aws_session
        self.aws_session_expiration = None
        self.__api_login = login
        self.__api_password = password

    def auth(self, login: str = None, password: str = None) -> dict:
        if login is None:
            if self.__api_login is None:
                raise Exception(
                    "Login is not provided via params or class constructor")
            login = self.__api_login
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
        

    def is_renewal_required(self):
        return True if (self.expiration_time < datetime.datetime.now(self.expiration_time.tzinfo)) else False

    def get_session(self) -> boto3.Session:
        if self.aws_session and not self.is_renewal_required():
            return self.aws_session
        weback_data = self.auth()
        region = weback_data['Region_Info']
        self.aws_identity_id = weback_data['Identity_Id']

        aws_creds = self.auth_cognito(
            region, weback_data['Identity_Id'], weback_data['Token'])
        self.expiration_time = aws_creds['Credentials'].get('Expiration')

        sess = self.make_session_from_cognito(aws_creds, region)
        self.aws_session = sess
        return sess
