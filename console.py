#!/usr/bin/env python3

from database import *
from datetime import datetime as dt
from jdatetime import date as jd
from logging import handlers
from os import system
from os import stat
from time import sleep
from prettytable import PrettyTable as ptable
import sys
import json
import logging
import re


with open('/opt/Email2SMS/config.json', 'r') as config_file:
    configs = json.load(config_file)

logging_path                    = configs["CONSOLE_LOGGING_PATH"]
local_db_address                = configs["LOCAL_DB_ADDRESS"]
db_user                         = configs["DB_USER"]
db_user_password                = configs["DB_PASSWORD"]
db_ip                           = configs["DB_IP"]
db_port                         = configs["DB_PORT"]
db_service_name                 = configs["DB_SERVICE_NAME"]

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


def print_header():
    system('clear')
    print('*' * 40)
    print('*' * 40)
    print(f'**  Informatics Services Corporation  **')
    print(f'**      Operation3 - ISSO group       **')
    print(f'**    Email to SMS Program Console    **')
    print('*' * 40)


def complete_user_data(db, fields, table_name, condition):
    select_user_query = db_queries["select_with_condition"].format(
        fields=fields,
        table=f'gadata.{table_name}',
        condition=condition
    )
    result, user_data = db.oracle_db_query(query_type='SELECT', query=select_user_query)
    if result.startswith('ERROR'):
        logging.error(result)
        return 'ERROR'
    elif user_data:
        return user_data[0]
    else:
        logging.warn(f'User with {condition} does not exists.')
        return 'ERROR'


def get_content_and_insert_record(db, email_address, user_name, mobile_phone, message_type='', is_new=False):
    msg = 'Enter message contents: ' if is_new else 'Enter new contents: '
    content = input(msg)
    proceed = input(f'Message contents is "{content}", would you proceed? (Yes or No) ')
    if proceed == 'Y' or proceed == 'y' or proceed == 'Yes' or proceed == 'yes' or proceed == 'YES':
        datetime_ = dt.now().strftime('%Y-%m-%d %H:%M:%S')
        insert_query = db_queries["insert_into_db"].format(
            table='received_emails',
            field_name='email_address, message_type, message_content, sms_sended, user_name, mobile_phone, datetime',
            values=f"'{email_address}', '{message_type}', '{content}', 0, '{user_name}', '98{mobile_phone}', '{datetime_}'"
        )
        result, _ = db.sqlite_db_query(query_type='INSERT', query=insert_query)
        if result.startswith('ERROR'):
            logging.error(result)
            raise Exception(result)
        else:
            logging.info('A message inserted into sms queue table and is ready to send.')
            raise Exception('A message inserted into sms queue table and is ready to send.')
    elif proceed == 'N' or proceed == 'n' or proceed == 'No' or proceed == 'no' or proceed == 'NO':
        pass
    else:
        raise Exception(f'Wrong input <<{proceed}>>.')


def send_content_after_confirm(db, sms):
    print(f'Content of sended message to {sms[5]} is:')
    print(sms[3])
    send_again = input(f'Do you want to send this content again (Yes or No)? ')
    if send_again == 'Y' or send_again == 'y' or send_again == 'Yes' or send_again == 'yes' or send_again == 'YES':
        update_query = db_queries["update_with_condition"].format(
            table='received_emails',
            field_value='sms_sended = 0',
            condition=f'id = {sms[0]}'
        )
        result, _ = db.sqlite_db_query(query_type='UPDATE', query=update_query)
        if result.startswith('ERROR'):
            logging.error(result)
            raise Exception(result)
        else:
            logging.info(f'Record with id {sms[0]} will send again soon.')
            raise Exception(f'Record with id {sms[0]} will send again soon.')
    elif send_again == 'N' or send_again == 'n' or send_again == 'No' or send_again == 'no' or send_again == 'NO':
        get_content_and_insert_record(
            db=db,
            email_address=sms[1],
            user_name=sms[4],
            mobile_phone=sms[5],
            message_type='console_message',
            is_new=True
        )
    else:
        raise Exception(f'Wrong input <<{send_again}>>.')


def main():
    logging.info('Establishing DB connections.')
    print('Please wait while DB connections to be established...')
    db = Database(
        logging=logging,
        called_from='console',
        sqlite_db_name=local_db_address,
        db_user=db_user,
        db_user_password=db_user_password,
        db_ip=db_ip,
        db_port=db_port,
        db_service_name=db_service_name
    )
    while True:
        print_header()
        print(f'************** Main Menu ***************')
        print(f'** Select one option and press enter  **')
        print(f'**  1) Send custom sms                **')
        print(f'**  2) Resend sms                     **')
        print(f'**  3) Check sms status               **')
        print(f'**  0) Exit                           **')
        print('*' * 40)
        user_input = input(f'************************* Your choice: ')
        try:
            main_menu_choice = int(user_input)
            if main_menu_choice == 0:
                print('Goodbye!')
                logging.warn('Exiting from console.')
                sys.exit(0)
            elif main_menu_choice == 1:
                print_header()
                print(f'*********** Send custom sms ************')
                print(f'** Select one option and press enter  **')
                print(f'**  1) Send sms by mobile phone       **')
                print(f'**  2) Send sms by email address      **')
                print(f'**  3) Send sms by username           **')
                print(f'**  0) Back main menu                 **')
                print('*' * 40)
                menu_input = input(f'************************* Your choice: ')
                menu_choice = int(menu_input)
                mobile_phone = ''
                email_address = ''
                user_name = ''
                if menu_choice == 0:
                    continue
                is_admin_user = input(f'Is ADMIN user (Yes or No)? ')
                if is_admin_user == 'Y' or is_admin_user == 'y' or is_admin_user == 'Yes' or is_admin_user == 'yes' or is_admin_user == 'YES':
                    table_name = 'dpa_user'
                    message_type = 'admin_notification'
                elif is_admin_user == 'N' or is_admin_user == 'n' or is_admin_user == 'No' or is_admin_user == 'no' or is_admin_user == 'NO':
                    table_name = 'dpa_web_user'
                    message_type = 'console_message'
                else:
                    raise Exception(f'Wrong input <<{is_admin_user}>>.')
                if menu_choice == 1:
                    mobile_phone = input(f'Enter mobile number (digits only): ')
                    if len(mobile_phone) > 11 or len(mobile_phone) < 10:
                        logging.error('Wrong mobile number.')
                        raise Exception(f'Wrong mobile number <<{mobile_phone}>>.')
                    if re.search('[a-z].*', mobile_phone) or re.search('[A-Z].*', mobile_phone):
                        logging.error('Wrong mobile number.')
                        raise Exception(f'Wrong mobile number <<{mobile_phone}>>.')
                    if mobile_phone.startswith('0'):
                        mobile_phone = f'{mobile_phone[1:]}'
                    user_data = complete_user_data(
                        db=db,
                        fields='user_name, user_email',
                        table_name=table_name,
                        condition=f'mobile_phone = {mobile_phone}'
                    )
                    if user_data == 'ERROR':
                        raise Exception('User not found')
                    user_name = user_data[0]
                    email_address = user_data[1]
                elif menu_choice == 2:
                    email_address = input(f'Enter email address: ')
                    if not re.search('^\S+@\S+\.\S+$', email_address):
                        logging.error('Wrong email address.')
                        raise Exception(f'Wrong email address <<{email_address}>>.')
                    user_data = complete_user_data(
                        db=db,
                        fields='user_name, mobile_phone',
                        table_name=table_name,
                        condition=f"user_email = '{email_address}'"
                    )
                    if user_data == 'ERROR':
                        raise Exception('User not found')
                    user_name = user_data[0]
                    mobile_phone = user_data[1]
                elif menu_choice == 3:
                    user_name = input(f'Enter username: ')
                    user_data = complete_user_data(
                        db=db,
                        fields='user_email, mobile_phone',
                        table_name=table_name,
                        condition=f"user_name = '{user_name}'"
                    )
                    if user_data == 'ERROR':
                        raise Exception('User not found')
                    email_address = user_data[0]
                    mobile_phone = user_data[1]
                get_content_and_insert_record(
                    db=db,
                    email_address=email_address,
                    user_name=user_name,
                    mobile_phone=mobile_phone,
                    message_type=message_type
                )
            elif main_menu_choice == 2:
                print_header()
                print(f'************** Resend sms **************')
                print(f'** Select one option and press enter  **')
                print(f'**  1) Print out last sended sms      **')
                print(f'**  2) Find sended sms by reciever    **')
                print(f'**  3) Find sended sms by content     **')
                print(f'**  0) Back main menu                 **')
                print('*' * 40)
                menu_input = input(f'************************* Your choice: ')
                menu_choice = int(menu_input)
                if menu_choice == 0:
                    continue
                elif menu_choice == 1:
                    sms_count_input = input(f'How many sended sms do you want to check? ')
                    sms_count = int(sms_count_input)
                    if sms_count <= 0:
                        raise Exception(f'Wrong input, count can not be <<{sms_count}>>.')
                    select_query = db_queries["select_with_condition"].format(
                        fields='id, email_address, message_type, message_content, user_name, mobile_phone, datetime',
                        table='received_emails',
                        condition=f"sms_sended = 1 and message_type != 'admin_notification' order by id desc limit {sms_count}"
                    )
                    result, sended = db.sqlite_db_query(query_type='SELECT', query=select_query)
                    if result.startswith('ERROR'):
                        logging.error(result)
                    else:
                        tb = ptable()
                        tb.field_names = ['id', 'email_address', 'message_type', 'user_name', 'mobile_phone', 'datetime']
                        for sms in sended:
                            tb.add_row([sms[0], sms[1], sms[2], sms[4], sms[5], sms[6]])
                        print(tb)
                        sended_id = input(f'\nSelect one id and press enter (0 for back to main menu): ')
                        id_ = int(sended_id)
                        if id_ == 0:
                            continue
                        ids = [sms[0] for sms in sended]
                        if id_ in ids:
                            for sms in sended:
                                if id_ == sms[0]:
                                    send_content_after_confirm(db, sms)
                        else:
                            logging.error('Wrong id inserted.')
                            raise Exception(f'Wrong id inserted <<{id_}>>.')
                elif menu_choice == 2:
                    print_header()
                    print(f'******* Resend sms by receiver *********')
                    print(f'** Select one option and press enter  **')
                    print(f'**  1) Find receiver by mobile phone  **')
                    print(f'**  2) Find receiver by email address **')
                    print(f'**  3) Find receiver by username      **')
                    print(f'**  0) Back main menu                 **')
                    print('*' * 40)
                    rec_inp = input(f'************************* Your choice: ')
                    rec_choice = int(rec_inp)
                    if rec_choice == 0:
                        continue
                    elif rec_choice == 1:
                        mobile_phone = input(f'Enter mobile number (digits only): ')
                        if len(mobile_phone) > 11 or len(mobile_phone) < 10:
                            logging.error('Wrong mobile number.')
                            raise Exception(f'Wrong mobile number <<{mobile_phone}>>.')
                        if re.search('[a-z].*', mobile_phone) or re.search('[A-Z].*', mobile_phone):
                            logging.error('Wrong mobile number.')
                            raise Exception(f'Wrong mobile number <<{mobile_phone}>>.')
                        if mobile_phone.startswith('0'):
                            mobile_phone = f'{mobile_phone[1:]}'
                        select_query = db_queries["select_with_condition"].format(
                            fields='id, email_address, message_type, message_content, user_name, mobile_phone, datetime',
                            table='received_emails',
                            condition=f"mobile_phone = '98{mobile_phone}'"
                        )
                        result, sended = db.sqlite_db_query(query_type='SELECT', query=select_query)
                        if result.startswith('ERROR'):
                            logging.error(result)
                        else:
                            tb = ptable()
                            tb.field_names = ['id', 'email_address', 'message_type', 'user_name', 'mobile_phone', 'datetime']
                            for sms in sended:
                                tb.add_row([sms[0], sms[1], sms[2], sms[4], sms[5], sms[6]])
                            print(tb)
                            sended_id = input(f'\nSelect one id and press enter (0 for back to main menu): ')
                            id_ = int(sended_id)
                            if id_ == 0:
                                continue
                            ids = [sms[0] for sms in sended]
                            if id_ in ids:
                                for sms in sended:
                                    if id_ == sms[0]:
                                        send_content_after_confirm(db, sms)
                            else:
                                logging.error('Wrong id inserted.')
                                raise Exception(f'Wrong id inserted <<{id_}>>.')
                    elif rec_choice == 2:
                        email_address = input(f'Enter email address: ')
                        if not re.search('^\S+@\S+\.\S+$', email_address):
                            logging.error('Wrong email address.')
                            raise Exception(f'Wrong email address <<{email_address}>>.')
                        select_query = db_queries["select_with_condition"].format(
                            fields='id, email_address, message_type, message_content, user_name, mobile_phone, datetime',
                            table='received_emails',
                            condition=f"email_address = '{email_address}'"
                        )
                        result, sended = db.sqlite_db_query(query_type='SELECT', query=select_query)
                        if result.startswith('ERROR'):
                            logging.error(result)
                        else:
                            tb = ptable()
                            tb.field_names = ['id', 'email_address', 'message_type', 'user_name', 'mobile_phone', 'datetime']
                            for sms in sended:
                                tb.add_row([sms[0], sms[1], sms[2], sms[4], sms[5], sms[6]])
                            print(tb)
                            sended_id = input(f'\nSelect one id and press enter (0 for back to main menu): ')
                            id_ = int(sended_id)
                            if id_ == 0:
                                continue
                            ids = [sms[0] for sms in sended]
                            if id_ in ids:
                                for sms in sended:
                                    if id_ == sms[0]:
                                        send_content_after_confirm(db, sms)
                            else:
                                logging.error('Wrong id inserted.')
                                raise Exception(f'Wrong id inserted <<{id_}>>.')
                    elif rec_choice == 3:
                        user_name = input(f'Enter username: ')
                        select_query = db_queries["select_with_condition"].format(
                            fields='id, email_address, message_type, message_content, user_name, mobile_phone, datetime',
                            table='received_emails',
                            condition=f"user_name = '{user_name}'"
                        )
                        result, sended = db.sqlite_db_query(query_type='SELECT', query=select_query)
                        if result.startswith('ERROR'):
                            logging.error(result)
                        else:
                            tb = ptable()
                            tb.field_names = ['id', 'email_address', 'message_type', 'user_name', 'mobile_phone', 'datetime']
                            for sms in sended:
                                tb.add_row([sms[0], sms[1], sms[2], sms[4], sms[5], sms[6]])
                            print(tb)
                            sended_id = input(f'\nSelect one id and press enter (0 for back to main menu): ')
                            id_ = int(sended_id)
                            if id_ == 0:
                                continue
                            ids = [sms[0] for sms in sended]
                            if id_ in ids:
                                for sms in sended:
                                    if id_ == sms[0]:
                                        send_content_after_confirm(db, sms)
                            else:
                                logging.error('Wrong id inserted.')
                                raise Exception(f'Wrong id inserted <<{id_}>>.')
                elif menu_choice == 3:
                    content_part = input(f'\nInsert part of content to search in messages (0 for back to main menu): ')
                    select_query = db_queries["select_with_condition"].format(
                        fields='id, email_address, message_type, message_content, user_name, mobile_phone, datetime',
                        table='received_emails',
                        condition=f"message_content like '%{content_part}%'"
                    )
                    result, sended = db.sqlite_db_query(query_type='SELECT', query=select_query)
                    if result.startswith('ERROR'):
                        logging.error(result)
                    else:
                        tb = ptable()
                        tb.field_names = ['id', 'email_address', 'message_type', 'user_name', 'mobile_phone', 'datetime']
                        for sms in sended:
                            tb.add_row([sms[0], sms[1], sms[2], sms[4], sms[5], sms[6]])
                        print(tb)
                        sended_id = input(f'\nSelect one id and press enter (0 for back to main menu): ')
                        id_ = int(sended_id)
                        if id_ == 0:
                            continue
                        ids = [sms[0] for sms in sended]
                        if id_ in ids:
                            for sms in sended:
                                if id_ == sms[0]:
                                    send_content_after_confirm(db, sms)
                        else:
                            logging.error('Wrong id inserted.')
                            raise Exception(f'Wrong id inserted <<{id_}>>.')
            elif main_menu_choice == 3:
                print_header()
                print(f'********** Check sms status ************')
                print(f'** Select one option and press enter  **')
                print(f'**  1) Check sms status by Track id   **')
                print(f'**  2) Check sms status by receiver   **')
                print(f'**  3) Check sms status by content    **')
                print(f'**  0) Back main menu                 **')
                print('*' * 40)
                menu_input = input(f'************************* Your choice: ')
                menu_choice = int(menu_input)
            else:
                raise Exception('Wrong input number.')
        except Exception as e:
            print(e)
            input('Press any key to continue...')
        finally:
            sleep(1)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'help' or sys.argv[1] == '-h' or sys.argv[1] == '--help':
            print('Email to SMS Program Console')
            print('Help:')
            print('      e2sconsole')
            print('                 - Use without options to enter the console menu\n')
            print('      e2sconsole [mobile|email|username=value] [content="message content"]')
            print('                 - Use one of below options at a time')
            print('                   mobile=[0]9---------        receiver mobile number')
            print('                   email=email@domain.com      receiver email address')
            print('                   username=something          receiver mobile number')
            print('                 - Message content should be within double quotes')
            print('                   content="message content"\n')
            print('      e2sconsole [file=/path/to/the/file]')
            print('                 - A json file containing receiver(s) data and message content should be provide')
        #TODO: develop cmd switch options
    else:
        main()