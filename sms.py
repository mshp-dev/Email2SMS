#!/usr/bin/env python3

from datetime import datetime as dt
from jdatetime import date as jd
from smsengine import SMSEngine, SMSStatus
from database import Database, db_queries
import time
import json


def send_sms(stop_event, logging, sms_engine_ip, sms_engine_port, sms_engine_service_name, sms_engine_username, sms_engine_password, send_api, db_user, db_user_password, db_ip, db_port, db_service_name, local_db_address, send_sms_interval):
    db = Database(
        logging=logging,
        called_from='send_sms',
        sqlite_db_name=local_db_address,
        db_user=db_user,
        db_user_password=db_user_password,
        db_ip=db_ip,
        db_port=db_port,
        db_service_name=db_service_name
    )
    smsengine = SMSEngine(
        logging=logging,
        called_from='send_sms',
        sms_engine_ip=sms_engine_ip,
        sms_engine_port=sms_engine_port,
        sms_engine_service_name=sms_engine_service_name,
        sms_engine_username=sms_engine_username,
        sms_engine_password=sms_engine_password,
        api_endpoint=send_api,
        method='POST'
    )
    while True:
        time.sleep(send_sms_interval)
        if stop_event.is_set():
            break
        select_emails_query = db_queries["select_with_condition"].format(
            fields='*',
            table='received_emails',
            condition='sms_sended = 0'
        )
        result, emails = db.sqlite_db_query(query_type='SELECT', query=select_emails_query)
        if result.startswith('ERROR'):
            logging.error(result)
        # else:
        #     logging.info(result)
        if emails:
            for email in emails:
                try:
                    logging.info(f'Sending SMS: {email}')
                    email_id = email[0]
                    email_address = email[1]
                    message_type = email[2]
                    message_content = email[3]
                    username = email[5]
                    mobilephone = email[6]
                    if message_type == 'admin_notification':
                        tb = 'dpa_user'
                        ptrn = 'sita_admin_message'
                    else:
                        tb = 'dpa_web_user'
                        ptrn = 'sita_client_message'
                    if not username and not mobilephone:
                        select_user_query = db_queries["select_with_condition"].format(
                            fields='user_name, mobile_phone',
                            table=f'gadata.{tb}',
                            condition=f"user_email = '{email_address}'"
                        )
                        result, user_data = db.oracle_db_query(query_type='SELECT', query=select_user_query)
                        if result.startswith('ERROR'):
                            logging.error(result)
                            continue
                        elif user_data:
                            username = user_data[0][0]
                            mobilephone = f'98{user_data[0][1]}'
                            update_query = db_queries["update_with_condition"].format(
                                table='received_emails',
                                field_value=f"user_name = '{username}', mobile_phone = '{mobilephone}'",
                                condition=f'id = {email_id}'
                            )
                            result, _ = db.sqlite_db_query(query_type='UPDATE', query=update_query)
                            if result.startswith('ERROR'):
                                logging.error(result)
                            # else:
                            #     logging.info(result)
                        else:
                            logging.warn(f'User with email {email_address} does not exists. No message has been sent')
                            update_query = db_queries["update_with_condition"].format(
                                table='received_emails',
                                field_value='sms_sended = 2',
                                condition=f'id = {email_id}'
                            )
                            result, _ = db.sqlite_db_query(query_type='UPDATE', query=update_query)
                            if result.startswith('ERROR'):
                                logging.error(result)
                            # else:
                            #     logging.info(result)
                            continue
                    result, response = smsengine.api_call(
                        pattern=ptrn,
                        phone_number=mobilephone,
                        message_content=message_content.replace('#username#', username) if message_type != 'admin_notification' else message_content
                    )
                    if result.startswith('ERROR') or response.status_code != 200:
                        logging.error(result)
                        # logging.error(response.text)
                        time.sleep(1)
                        continue
                    else:
                        logging.info(result)
                        if response.json()["success"]:
                            track_id = response.json()['data']['trackId']
                            logging.info(f"SMS Engine api call sent successfully with track id {track_id}")
                            update_query = db_queries["update_with_condition"].format(
                                table='received_emails',
                                field_value='sms_sended = 1',
                                condition=f'id = {email_id}'
                            )
                            result, _ = db.sqlite_db_query(query_type='UPDATE', query=update_query)
                            if result.startswith('ERROR'):
                                logging.error(result)
                            # else:
                            #     logging.info(result)
                            datetime_ = dt.now().strftime('%Y-%m-%d %H:%M:%S')
                            insert_query = db_queries["insert_into_db"].format(
                                table='sended_sms',
                                field_name='email_id, track_id, status, sms_datetime',
                                values=f"{email_id}, '{track_id}', 'Created', '{datetime_}'"
                            )
                            result, _ = db.sqlite_db_query(query_type='INSERT', query=insert_query)
                            if result.startswith('ERROR'):
                                logging.error(result)
                            # else:
                            #     logging.info(result)
                        else:
                            logging.error(f'SMS Engine responded with error: {response.json()["error"]}')
                            update_query = db_queries["update_with_condition"].format(
                                table='received_emails',
                                field_value='sms_sended = 3',
                                condition=f'id = {email_id}'
                            )
                            result, _ = db.sqlite_db_query(query_type='UPDATE', query=update_query)
                            if result.startswith('ERROR'):
                                logging.error(result)
                            # else:
                            #     logging.info(result)
                except Exception as e:
                    logging.error(e)
                    continue


#TODO: use general queries
def check_status(stop_event, logging, sms_engine_ip, sms_engine_port, sms_engine_service_name, sms_engine_username, sms_engine_password, status_api, db_user, db_user_password, db_ip, db_port, db_service_name, local_db_address, check_sms_status_interval):
    db = Database(
        logging=logging,
        called_from='check_status',
        sqlite_db_name=local_db_address
    )
    smsengine = SMSEngine(
        logging=logging,
        called_from='check_status',
        sms_engine_ip=sms_engine_ip,
        sms_engine_port=sms_engine_port,
        sms_engine_service_name=sms_engine_service_name,
        sms_engine_username=sms_engine_username,
        sms_engine_password=sms_engine_password,
        api_endpoint=status_api,
        method='POST'
    )
    while True:
        time.sleep(check_sms_status_interval)
        if stop_event.is_set():
            break
        all_sended_sms_query = db_queries["select_all_from_table"].format(table='sended_sms')
        result, sended_sms = db.sqlite_db_query(query_type='SELECT', query=all_sended_sms_query)
        if result.startswith('ERROR'):
            logging.error(result)
        else:
            logging.info(result)
        if sended_sms:
            for sms in sended_sms:
                mobilephone = ''
                try:
                    sended_id = sms[0]
                    email_id = sms[1]
                    track_id = sms[2]
                    status = sms[3]
                    if status in (SMSStatus.CREATED.value, SMSStatus.SUCCESSFUL_SEND_TO_PROVIDER.value):
                        logging.info(f'Checking SMS status with track id {track_id} (status: {status})')
                        result, response = smsengine.api_call(
                            pattern='sita_sms_status',
                            track_id=track_id
                        )
                        if result.startswith('ERROR') or response.status_code != 200:
                            logging.error(result)
                        else:
                            if response.text != '':
                                logging.info(result)
                                update_query = db_queries["update_with_condition"].format(
                                    table='sended_sms',
                                    field_value=f"status = '{response.text}'",
                                    condition=f"id = {sended_id}"
                                )
                                result, _ = db.sqlite_db_query(query_type='UPDATE', query=update_query)
                                if result.startswith('ERROR'):
                                    logging.error(result)
                                else:
                                    logging.info(result)
                                logging.info(f'SMS state with track id {track_id} is {response.text}')
                            else:
                                logging.warn(f'Something went side ways - <<{result}>>')
                    elif status in (SMSStatus.FAILED_SEND_TO_PROVIDER.value, SMSStatus.FAILED_DELIVERY_TO_RECEIVER.value, SMSStatus.CORRUPTED_DELIVERY_TO_RECEIVER.value):
                        logging.info(f'Putting SMS with track id {track_id} (status: {status}) in send queue')
                        # update_query = db_queries["update_with_condition"].format(
                        #     table='received_emails',
                        #     field_value=f"sms_sended = 0",
                        #     condition=f"id = {email_id}"
                        # )
                        # result, _ = db.sqlite_db_query(query_type='UPDATE', query=update_query)
                        # if result.startswith('ERROR'):
                        #     logging.error(result)
                        # else:
                        #     logging.info(result)
                    elif status == SMSStatus.UNKNOWN.value:
                        logging.info(f'Deleting record with status: {status}, email_id is {email_id}')
                        delete_query = db_queries["delete_with_condition"].format(
                            table='sended_sms',
                            condition=f"id = {sended_id}"
                        )
                        result, _ = db.sqlite_db_query(query_type='DELETE', query=delete_query)
                        if result.startswith('ERROR'):
                            logging.error(result)
                        else:
                            logging.info(result)
                except Exception as e:
                    logging.error(e)
                    continue

