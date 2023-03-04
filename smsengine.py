#!/usr/bin/env python3

from requests import request
from requests.auth import HTTPBasicAuth as Auth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from datetime import datetime as dt
from jdatetime import date as jd
from enum import Enum
import time
import json
import requests


smsengine_api_patterns = {
    'sita_otp'            : '<SitaOTP PhoneNo="{phone_number}" otp="{message_content}" trackId="{track_id}"/>',
    'sita_reset_password' : '<SitaResetPassword PhoneNo="{phone_number}" ResetPassword="{message_content}" trackId="{track_id}"/>',
    'sita_admin_message'  : '<SitaAdminMessage PhoneNo="{phone_number}" AdminMessage="{message_content}" trackId="{track_id}"/>',
    'sita_client_message' : '<SitaClientMessage PhoneNo="{phone_number}" ClientMessage="{message_content}" trackId="{track_id}"/>',
    'sita_sms_status'     : ''
}


class SMSStatus(Enum):
    CREATED                         = 'Created'
    SUCCESSFUL_SEND_TO_PROVIDER     = 'SuccessfulSendToProvider'
    FAILED_SEND_TO_PROVIDER         = 'FailedSendToProvider'
    SUCCESSFUL_DELIVERY_TO_RECEIVER = 'SuccessfulDeliveryToReceiver'
    FAILED_DELIVERY_TO_RECEIVER     = 'FailedDeliveryToReceiver'
    CORRUPTED_DELIVERY_TO_RECEIVER  = 'CorruptedDeliveryToReceiver'
    UNKNOWN                         = 'Unknown'


class SMSEngine:
    """Class for sending api call to sms engine"""

    def __init__(self, logging, called_from, sms_engine_ip, sms_engine_port, sms_engine_service_name, sms_engine_username, sms_engine_password, api_endpoint, method):
        self.logging = logging
        self.url = f'https://{sms_engine_ip}:{sms_engine_port}/{sms_engine_service_name}/{api_endpoint}'
        self.method = method
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
        self.headers = {
            "Content-Type": "text/plain"
        }
        self.auth = (
            sms_engine_username,
            sms_engine_password
        )
        self.logging.info(f'Created SMSEngine instance ({method} /{api_endpoint}) from {called_from} module successfully.')


    def __del__(self):
        try:
            self.logging.info('SMSEngine instance destroyed Successfuly.')
        except Exception as e:
            self.logging.error(e)
            self.logging.warn('SMSEngine instance destroyed with ERROR.')


    def api_call(self, pattern, phone_number='', message_content='', track_id=''):
        api_call_response = None
        data_ = None
        error = None
        try:
            if pattern == 'sita_admin_message' or pattern == 'sita_client_message':
                data_ = smsengine_api_patterns[pattern].format(
                    phone_number=phone_number,
                    message_content=message_content,
                    track_id=dt.now().strftime("%Y%m%d%H%M%S%f")[:-1] if track_id == '' else track_id
                ).encode('utf-8')
            elif pattern == 'sita_sms_status':
                data_ = track_id
            api_call_response = request(
                method=self.method,
                url=self.url,
                data=data_,
                headers=self.headers,
                auth=self.auth,
                verify=False,
                timeout=1
            )
            self.logging.info(f'Request with data <<{data_}>> has been sent.')
        except Exception as e:
            error = f'ERROR: <<{e}>> when calling {self.url} @ {str(dt.now())}'
        finally:
            if api_call_response is not None:
                return f'INFO: URL ({self.url}) called and response code is {api_call_response.status_code} @ {str(dt.now())}', api_call_response
            elif error is not None:
                return error, None
            return f'ERROR: Something went wrong @ {str(dt.now())}', None

