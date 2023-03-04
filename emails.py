#!/usr/bin/env python3

from datetime import datetime as dt
from jdatetime import date as jd
from enum import Enum
from database import Database, db_queries
from time import sleep
import os
import json
import re


message_contents       = {
    'admin_notification' : '''اطلاع رسانی به مدیر سیستم:
موضوع: {subject}
زمان: {date_time}''',
    'password_expiration_notice' : '''کاربر محترم #username#
کلمه عبور شما در تاریخ {exp_date} منقضی خواهد شد،
لطفاً در اسرع وقت قبل از تاریخ فوق از طریق لینک زیر اقدام به تغییر کلمه عبور خود نمائید:
{link}
تیم پشتیبانی سامانه سیتا، شرکت خدمات انفورماتیک
تلفن پشتیبانی: 29985700''',
    'reset_password_request' : '''کاربر محترم #username#
یک درخواست مبنی بر بازنشانی کلمه عبور حساب شما دریافت شد،
لطفاً از طریق لینک یکتای زیر اقدام به بازنشانی کلمه عبور خود نمائید:
{link}
تیم پشتیبانی سامانه سیتا، شرکت خدمات انفورماتیک
تلفن پشتیبانی: 29985700''',
    'password_has_been_changed' : '''کاربر محترم #username#
کلمه عبور حساب کاربری شما بازنشانی شده است،
لطفاً از این پس از عبارت  {new_password}  به عنوان کلمه عبور جدید استفاده نمائید
تیم پشتیبانی سامانه سیتا، شرکت خدمات انفورماتیک
تلفن پشتیبانی: 29985700''',
}


class State(Enum):
    WAIT_FOR_NEW_EMAIL         = 1
    READ_EMAIL_ADDRESS         = 2
    READ_EMAIL_SUBJECT         = 3
    SEND_SMS_TO_USER           = 4
    SAVE_EMAIL_TO_FILE         = 5


class Subject(Enum):
    PASSWORD_EXPIRATION_NOTICE = 1
    PASSWORD_RESET_REQUEST     = 2
    PASSWORD_HAS_BEEN_CHANGED  = 3
    ADMIN_NOTIFICATION_EMAIL   = 7


def tail(file):
    file.seek(0, 0)
    while True:
        line = file.readline()
        if not line:
            # sleep(0.1)
            continue
        yield line


def save_email_to_file(emails_directory, file_name, file_content):
    with open(f'{emails_directory}/{file_name}.html', mode='w', encoding='utf-8') as eml:
        eml.writelines(file_content)


# deprecated
def read_new_emails(logging, mail_archive_path, email_files_directory, local_db_address):
    db = Database(
        logging=logging,
        called_from='read_new_emails',
        sqlite_db_name=local_db_address
    )
    mailarchive = open(mail_archive_path, 'r')
    mails = tail(mailarchive)
    current_state = State.WAIT_FOR_NEW_EMAIL
    email_datetime = ''
    email_address = ''
    subject = ''
    exp_date = ''
    current_state = ''
    link = ''
    new_password = ''
    email_content = ''
    message_type = ''
    message_content = ''
    for line in mails:
        sleep(0.001)
        if line.startswith('Date:'):
            email_datetime = dt.strptime(re.sub('\s\+.*', '', re.sub('^.*,\s', '', line)).replace('\n', ''), '%d %b %Y %H:%M:%S').strftime("%Y-%m-%d %H:%M:%S")
            current_state = State.READ_EMAIL_ADDRESS
        elif line.startswith('To:'):
            email_address = line.replace('To:', '').replace(' ', '').replace('<', '').replace('>', '').replace('\n', '')
            current_state = State.READ_EMAIL_SUBJECT
        elif line.startswith('Subject:'):
            subject = line.replace('Subject: ', '').replace("'", "").replace('"', '').replace('\n', '')
            if 'Password Expiration Notice' in subject:
                current_state = State.PASSWORD_EXPIRATION_NOTICE
            elif 'Reset Password Request' in subject:
                current_state = State.PASSWORD_RESET_REQUEST
            elif 'Your Account Information Has Changed' in subject:
                current_state = State.PASSWORD_HAS_BEEN_CHANGED
            else:
                current_state = State.ADMIN_NOTIFICATION_EMAIL
        else:
            if current_state == State.PASSWORD_EXPIRATION_NOTICE:
                if 'Your password is set to expire on' in line:
                    s = line.split(' ')[-1]
                    exp_date = jd.fromgregorian(day=int(s.split(' ')[-1].split('/')[1]), month=int(s.split(' ')[-1].split('/')[0]), year=int(f"20{s.split(' ')[-1].split('/')[-1]}")).strftime(f'%Y/%m/%d')
                elif '<a href' in line:
                    link = line.replace('\t', '').replace('<a href="', '').replace(' ', '').replace('\n', '').split('"')[0]
                    message_type = 'password_expiration_notice'
                    message_content = message_contents['password_expiration_notice'].format(exp_date=exp_date, link=link)
                    current_state = State.SEND_SMS_TO_USER
            elif current_state == State.PASSWORD_RESET_REQUEST:
                if '<a href' in line:
                    link = line.replace('\t', '').replace('<a href="', '').replace(' ', '').replace('\n', '').split('"')[0]
                    message_type = 'reset_password_request'
                    message_content = message_contents['reset_password_request'].format(link=link)
                    current_state = State.SEND_SMS_TO_USER
            elif current_state == State.PASSWORD_HAS_BEEN_CHANGED:
                if 'The password for your account has been reset to' in line:
                    new_password = line.replace('<b>', '').replace('</b>', '').replace('\n', '').split(' ')[-1]
                    message_type = 'password_has_been_changed'
                    message_content = message_contents['password_has_been_changed'].format(new_password=new_password)
                    current_state = State.SEND_SMS_TO_USER
            elif current_state == State.ADMIN_NOTIFICATION_EMAIL:
                if '[GoAnywhere Alert]' in subject:
                    subject = subject.replace('[GoAnywhere Alert] ', '').replace('\n', '')
                message_type = 'admin_notification'
                message_content = message_contents['admin_notification'].format(
                    subject=subject,
                    date_time=email_datetime
                )
                if line.startswith('<html>'):
                    email_content = f'{line}\n'
                    current_state = State.SAVE_EMAIL_TO_FILE
            elif current_state == State.SAVE_EMAIL_TO_FILE:
                email_content += f'{line}\n'
                if line.startswith('</html>'):
                    save_email_to_file(
                        emails_directory=email_files_directory,
                        file_name=f"{email_address.split('@')[0]}@{dt.now().strftime('%Y-%m-%d--%H-%M-%S-%f')}",
                        file_content=email_content
                    )
                    current_state = State.SEND_SMS_TO_USER
            elif current_state == State.SEND_SMS_TO_USER:
                for em_ad in email_address.split(','):
                    logging.info(f'An email recieved for {em_ad} with subject of {subject}')
                    insert_query = db_queries["insert_user_data_into_local_db"].format(
                        table='received_emails',
                        email_address=em_ad,
                        message_type=message_type,
                        message_content=message_content,
                        sms_sended=0,
                        datetime=email_datetime
                    )
                    result, user_info = db.sqlite_db_query(query_type='INSERT', query=insert_query)
                    if result.startswith('ERROR'):
                        logging.error(result)
                    else:
                        logging.info(result)
                email_datetime = ''
                email_address = ''
                subject = ''
                exp_date = ''
                current_state = ''
                link = ''
                new_password = ''
                email_content = ''
                message_type = ''
                message_content = ''
                current_state = State.WAIT_FOR_NEW_EMAIL


def read_new_emails_and_save_to_file(stop_event, logging, mail_archive_path, email_files_directory, local_db_address):
    db = Database(
        logging=logging,
        called_from='read_new_emails_and_save_to_file',
        sqlite_db_name=local_db_address
    )
    mailarchive = open(mail_archive_path, 'r')
    mails = tail(mailarchive)
    current_state = State.WAIT_FOR_NEW_EMAIL
    current_subject = ''
    email_datetime = ''
    email_address = ''
    subject = ''
    exp_date = ''
    link = ''
    new_password = ''
    email_content = ''
    message_type = ''
    message_content = ''
    part_number = ''
    for line in mails:
        sleep(0.001)
        if stop_event.is_set():
            break
        if current_state == State.WAIT_FOR_NEW_EMAIL:
            if line.startswith('Date:'):
                email_datetime = dt.strptime(re.sub('\s\+.*', '', re.sub('^.*,\s', '', line)).replace('\n', ''), '%d %b %Y %H:%M:%S').strftime("%Y-%m-%d %H:%M:%S")
                current_state = State.READ_EMAIL_ADDRESS
        elif current_state == State.READ_EMAIL_ADDRESS:
            if line.startswith('To:'):
                email_address = line.replace('To:', '').replace(' ', '').replace('<', '').replace('>', '').replace('\n', '')
                current_state = State.READ_EMAIL_SUBJECT
        elif current_state == State.READ_EMAIL_SUBJECT:
            if line.startswith('Subject:'):
                subject = line.replace('Subject: ', '').replace("'", "").replace('"', '').replace('\n', '')
                if 'Password Expiration Notice' in subject:
                    current_subject = Subject.PASSWORD_EXPIRATION_NOTICE
                elif 'Reset Password Request' in subject:
                    current_subject = Subject.PASSWORD_RESET_REQUEST
                elif 'Your Account Information Has Changed' in subject:
                    current_subject = Subject.PASSWORD_HAS_BEEN_CHANGED
                else:
                    current_subject = Subject.ADMIN_NOTIFICATION_EMAIL
                current_state = State.SAVE_EMAIL_TO_FILE
        elif current_state == State.SAVE_EMAIL_TO_FILE:
            if line.startswith('<html>'):
                email_content = f'{line}\n'
            elif line.startswith('</html>'):
                email_content += f'{line}\n'
                save_email_to_file(
                    emails_directory=email_files_directory,
                    file_name=f"{email_address.split('@')[0]}@{dt.now().strftime('%Y-%m-%d--%H-%M-%S-%f')}",
                    file_content=email_content
                )
                current_state = State.SEND_SMS_TO_USER
            else:
                email_content += f'{line}\n'
                if current_subject == Subject.PASSWORD_EXPIRATION_NOTICE:
                    if 'Your password is set to expire on' in line:
                        s = line.split(' ')[-1]
                        exp_date = jd.fromgregorian(day=int(s.split(' ')[-1].split('/')[1]), month=int(s.split(' ')[-1].split('/')[0]), year=int(f"20{s.split(' ')[-1].split('/')[-1]}")).strftime(f'%Y/%m/%d')
                    elif re.search('^\s+<a href', line):
                        link = line.replace('\t', '').replace('<a href="', '').replace(' ', '').replace('\n', '').split('"')[0]
                        message_type = 'password_expiration_notice'
                        message_content = message_contents['password_expiration_notice'].format(exp_date=exp_date, link=link)
                elif current_subject == Subject.PASSWORD_RESET_REQUEST:
                    if re.search('^\s+<a href', line):
                        link = line.replace('\t', '').replace('<a href="', '').replace(' ', '').replace('\n', '').split('"')[0]
                        message_type = 'reset_password_request'
                        message_content = message_contents['reset_password_request'].format(link=link)
                elif current_subject == Subject.PASSWORD_HAS_BEEN_CHANGED:
                    if 'The password for your account has been reset to' in line:
                        new_password = line.replace('<b>', '').replace('</b>', '').replace('\n', '').split(' ')[-1]
                        message_type = 'password_has_been_changed'
                        message_content = message_contents['password_has_been_changed'].format(new_password=new_password)
                elif current_subject == Subject.ADMIN_NOTIFICATION_EMAIL:
                    if '[GoAnywhere Alert]' in subject:
                        subject = subject.replace('[GoAnywhere Alert] ', '').replace('\n', '')
                    message_type = 'admin_notification'
                    message_content = message_contents['admin_notification'].format(
                        subject=subject,
                        date_time=email_datetime
                    )
        elif current_state == State.SEND_SMS_TO_USER:
            if line.startswith('------=_Part_') and line.replace('\n', '').endswith('--'):
                part_number = line.replace('\n', '')
                select_part_number_query = db_queries["select_with_condition"].format(
                    fields='count(*)',
                    table='received_emails',
                    condition=f"part_number = '{part_number}'"
                )
                result, count = db.sqlite_db_query(query_type='SELECT', query=select_part_number_query)
                if result.startswith('ERROR'):
                    logging.error(result)
                else:
                    # logging.info(result)
                    if count[0][0] == 0:
                        for em_ad in email_address.split(','):
                            logging.info(f'An email recieved for {em_ad} with subject of {subject}')
                            datetime_ = dt.now().strftime('%Y-%m-%d %H:%M:%S')
                            insert_query = db_queries["insert_into_db"].format(
                                table='received_emails',
                                field_name='email_address, message_type, message_content, sms_sended, email_datetime, part_number, datetime',
                                values=f"'{em_ad}', '{message_type}', '{message_content}', 0, '{email_datetime}', '{part_number}', '{datetime_}'"
                            )
                            result, _ = db.sqlite_db_query(query_type='INSERT', query=insert_query)
                            if result.startswith('ERROR'):
                                logging.error(result)
                            else:
                                logging.info(result)
                email_datetime = ''
                email_address = ''
                subject = ''
                exp_date = ''
                link = ''
                new_password = ''
                email_content = ''
                message_type = ''
                message_content = ''
                part_number = ''
                current_subject = ''
                current_state = State.WAIT_FOR_NEW_EMAIL