#!/usr/bin/env python3

from emails import *
from sms import *
from database import Database
from datetime import datetime as dt
from jdatetime import date as jd
from threading import Thread
from threading import Event
from logging import handlers
from os import system
from os import stat
from time import sleep
import sys
import json
import logging
import atexit
import signal


with open('/path/to/Email2SMS/config.json') as config_file:
    configs = json.load(config_file)

mail_archive_path               = configs["MAIL_ARCHIVE_PATH"]
email_files_directory           = configs["EMAIL_FILES_DIRECTORY"]
logging_path                    = configs["LOGGING_PATH"]
local_db_address                = configs["LOCAL_DB_ADDRESS"]
db_user                         = configs["DB_USER"]
db_user_password                = configs["DB_PASSWORD"]
db_ip                           = configs["DB_IP"]
db_port                         = configs["DB_PORT"]
db_service_name                 = configs["DB_SERVICE_NAME"]
smsengine_ip                    = configs["SMSENGINE_IP"]
smsengine_port                  = configs["SMSENGINE_PORT"]
smsengine_service_name          = configs["SMSENGINE_SERVICE_NAME"]
smsengine_username              = configs["SMSENGINE_USERNAME"]
smsengine_password              = configs["SMSENGINE_PASSWORD"]
smsengine_api_send              = configs["SMSENGINE_API_SEND"]
smsengine_api_status            = configs["SMSENGINE_API_STATUS"]
send_sms_interval               = configs["SEND_SMS_INTERVAL"]
check_sms_status_interval       = configs["CHECK_SMS_STATUS_INTERVAL"]
read_new_emails_method          = configs["READ_NEW_EMAILS_METHOD"]
send_sms_method                 = configs["SEND_SMS_METHOD"]
check_status_method             = configs["CHECK_STATUS_METHOD"]
check_mailarchive_size_interval = configs["CHECK_MAILARCHIVE_SIZE_INTERVAL"]

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)-8s] (%(module)s.%(funcName)s) %(message)s',
    datefmt='[%Y-%m-%d %H:%M:%S]',
    handlers=[
        handlers.RotatingFileHandler(
            filename=logging_path,
            mode='a',
            maxBytes=10485760,
            backupCount=30,
            encoding='utf-8'
        )
    ]
)

# read_new_emails_and_save_to_file_thread = None
# send_sms_stop_event = None
# check_status_stop_event = None
# stop_service_signal = False


def main():
    if read_new_emails_method:
        logging.info(f'Starting read_new_emails_and_save_to_file module in seprate thread.')
        read_new_emails_stop_event = Event()
        read_new_emails_and_save_to_file_thread = Thread(
            target=read_new_emails_and_save_to_file,
            args=(
                read_new_emails_stop_event,
                logging,
                mail_archive_path,
                email_files_directory,
                local_db_address
            )
        )
        read_new_emails_and_save_to_file_thread.start()
    if send_sms_method:
        logging.info(f'Starting send_sms module in seprate thread.')
        send_sms_stop_event = Event()
        send_sms_thread = Thread(target=send_sms, args=(
            logging,
            smsengine_ip,
            smsengine_port,
            smsengine_service_name,
            smsengine_username,
            smsengine_password,
            smsengine_api_send,
            db_user,
            db_user_password,
            db_ip,
            db_port,
            db_service_name,
            local_db_address,
            send_sms_interval
        ))
        send_sms_thread.start()
    if check_status_method:
        logging.info(f'Starting check_status module in seprate thread.')
        check_status_stop_event = Event()
        check_status_thread = Thread(target=check_status, args=(
            logging,
            smsengine_ip,
            smsengine_port,
            smsengine_service_name,
            smsengine_username,
            smsengine_password,
            smsengine_api_status,
            db_user,
            db_user_password,
            db_ip,
            db_port,
            db_service_name,
            local_db_address,
            check_sms_status_interval
        ))
        check_status_thread.start()
    # check for mailarchive size and rotate it
    start_read_email_thread_again = False
    while True:
        if start_read_email_thread_again and read_new_emails_method:
            sleep(1)
            start_read_email_thread_again = False
            read_new_emails_and_save_to_file_thread = Thread(
                target=read_new_emails_and_save_to_file,
                args=(
                    read_new_emails_stop_event,
                    logging,
                    mail_archive_path,
                    email_files_directory,
                    local_db_address
                )
            )
            read_new_emails_stop_event.clear()
            logging.info(f'Starting read_new_emails_and_save_to_file module in seprate thread.')
            read_new_emails_and_save_to_file_thread.start()
        sleep(check_mailarchive_size_interval)
        mailarchive_size_in_MB = (stat(mail_archive_path).st_size / 1024) / 1024
        if mailarchive_size_in_MB >= 10:
            logging.warn(f'Stop execution of read_new_emails_and_save_to_file thread and postfix service.')
            cmd = 'systemctl stop postfix.service'
            ret_code = system(cmd)
            if ret_code != 0:
                logging.error(f'Somthing went wrong in execution of <<{cmd}>>')
                system(cmd)
            read_new_emails_stop_event.set()
            logging.warn(f'Rotate mailarchive and start postfix service.')
            cmd = f"mv {mail_archive_path} {mail_archive_path}.{dt.now().strftime('%Y-%m-%d--%H-%M-%S')}"
            ret_code = system(cmd)
            if ret_code != 0:
                logging.error(f'Somthing went wrong in execution of <<{cmd}>>')
                system(cmd)
            cmd = f'touch {mail_archive_path}'
            ret_code = system(cmd)
            if ret_code != 0:
                logging.error(f'Somthing went wrong in execution of <<{cmd}>>')
                system(cmd)
            cmd = f'chmod 600 {mail_archive_path}'
            ret_code = system(cmd)
            if ret_code != 0:
                logging.error(f'Somthing went wrong in execution of <<{cmd}>>')
                system(cmd)
            cmd = f'chown mailarchive:mail {mail_archive_path}'
            ret_code = system(cmd)
            if ret_code != 0:
                logging.error(f'Somthing went wrong in execution of <<{cmd}>>')
                system(cmd)
            cmd = 'systemctl start postfix.service'
            ret_code = system(cmd)
            if ret_code != 0:
                logging.error(f'Somthing went wrong in execution of <<{cmd}>>')
                system(cmd)
            start_read_email_thread_again = True


#TODO: not working in systemctl mode, deal with SIGTERM
# @atexit.register
# def exit():
#     logging.warn('Exiting from email_to_sms program and stop all threads.')
#     stop_service_signal = True
#     if read_new_emails_and_save_to_file_thread:
#         read_new_emails_and_save_to_file_thread.is_set()
#     if send_sms_stop_event:
#         send_sms_stop_event.is_set()
#     if check_status_stop_event:
#         check_status_stop_event.is_set()
#     sys.exit()


if __name__ == "__main__":
    # signal.signal(signal.SIGINT, exit)
    # signal.signal(signal.SIGTERM, exit)
    # signal.signal(signal.SIGKILL, exit)
    main()