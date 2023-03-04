#!/usr/bin/env python3

from datetime import datetime as dt
from jdatetime import date as jd
import cx_Oracle as ora
import sqlite3 as sl


db_queries = {
    "insert_user_data_into_local_db": "insert into {table} (email_address, message_type, message_content, sms_sended, datetime) values('{email_address}', '{message_type}', '{message_content}', {sms_sended}, '{datetime}')",
    "insert_track_id_into_local_db": "insert into {table} (email_id, track_id, status) values({email_id}, '{track_id}', '{status}')",
    "select_not_sended": "select * from {table} where sms_sended = 0",
    "select_encountered_error": "select * from {table} where sms_sended = 3",
    
    "select_all_from_table": "select * from {table}",
    "select_with_condition": "select {fields} from {table} where {condition}",
    "update_with_condition": "update {table} set {field_value} where {condition}",
    "delete_with_condition": "delete from {table} where {condition}",
    "insert_into_db": "insert into {table} ({field_name}) values({values})",

    "count_today_emails": "select count(*) from {table} where sms_sended = 1 and datetime like '%{date}%'",
    "update_after_send": "update {table} set sms_sended = 1 where id = {id}",
    "update_user_data": "update {table} set user_name = '{user_name}', mobile_phone = '{mobile_phone}' where id = {id}",
    "update_wrong_email": "update {table} set sms_sended = 2 where id = {id}",
    "error_from_smsengine": "update {table} set sms_sended = 3, mobile_phone = '{mobile_phone}' where id = {id}",
    "get_user_name_and_phone": "select user_name, mobile_phone from {schema}.{table} where user_email = '{email}'"
}


class Database:
    """Class for db connections and query"""

    def __init__(self, logging, called_from, sqlite_db_name='', db_user='', db_user_password='', db_ip='', db_port='', db_service_name=''):
        self.oracle_connection = None
        self.oracle_cursor     = None
        self.sqlite_connection = None
        self.sqlite_cursor     = None
        self.logging           = logging
        try:
            if sqlite_db_name != '':
                self.sqlite_connection = sl.connect(sqlite_db_name)
                self.sqlite_cursor = self.sqlite_connection.cursor()
                self.logging.info(f'Connected to sqlite db from {called_from} module successfully.')
            if db_user != '' and db_user_password != '' and db_ip != '' and db_port != '' and db_service_name != '':
                self.oracle_connection = ora.connect(f'{db_user}/{db_user_password}@{db_ip}:{db_port}/{db_service_name}')
                self.oracle_cursor = self.oracle_connection.cursor()
                self.logging.info(f'Connected to oracle db from {called_from} module successfully.')
        except Exception as e:
            self.logging.error(f'Connecting to db encountered error, {e}.')
            if self.oracle_connection:
                self.oracle_connection.close()
            if self.oracle_cursor:
                self.oracle_cursor.close()
            if self.sqlite_connection:
                self.sqlite_connection.close()
            if self.sqlite_cursor:
                self.sqlite_cursor.close()
    
    
    def __del__(self):
        try:
            self.disconnect_db_connections()
            self.logging.info('Database instance destroyed Successfuly.')
        except Exception as e:
            self.logging.error(e)
            self.logging.warn('Database instance destroyed with ERROR.')


    def disconnect_db_connections(self):
        if self.oracle_connection:
            self.oracle_connection.close()
        if self.oracle_cursor:
            self.oracle_cursor.close()
        if self.sqlite_connection:
            self.sqlite_connection.close()
        if self.sqlite_cursor:
            self.sqlite_cursor.close()


    def sqlite_db_query(self, query_type, query, data=None): #db_name, 
        result = None
        error = None
        # con = None
        # cur = None
        try:
            # con = sl.connect(db_name)
            # cur = con.cursor()
            if query_type == 'CREATE' or query_type == 'DROP' or query_type == 'TRUNCATE':
                self.sqlite_cursor.execute(query)
            elif query_type == 'INSERT' or query_type == 'UPDATE' or query_type == 'DELETE':
                self.sqlite_cursor.execute(query)
                self.sqlite_connection.commit()
            elif query_type == 'INSERTMANY' or query_type == 'UPDATEMANY':
                self.sqlite_cursor.executemany(query, data)
                self.sqlite_connection.commit()
            elif query_type == 'SELECT':
                result = self.sqlite_cursor.execute(query)
        except Exception as e:
            error = f'ERROR: There is a problem: {e} in execution of query {query} @ {str(dt.now())}'
        finally:
            if result is not None and error is None:
                rows = self.sqlite_cursor.fetchall()
                # if cur:
                #     cur.close()
                # if con:
                #     con.close()
                return f'INFO: Query({query}) executed successfully @ {str(dt.now())}', rows
            else:
                # if cur:
                #     cur.close()
                # if con:
                #     con.close()
                if error is not None:
                    return error, None
                else:
                    return f'INFO: Query({query}) executed successfully @ {str(dt.now())}', None
            return f'ERROR: Something went wrong @ {str(dt.now())}', None


    def oracle_db_query(self, query_type, query, data=None): #username, password, ip, port, service_name, 
        result = None
        error = None
        # con = None
        # cur = None
        try:
            # con = ora.connect(f'{username}/{password}@{db_ip}:{db_port}/{service_name}')
            # cur = con.cursor()
            if query_type == 'CREATE' or query_type == 'DROP' or query_type == 'TRUNCATE':
                self.oracle_cursor.execute(query)
            elif query_type == 'INSERT' or query_type == 'UPDATE':
                self.oracle_cursor.execute(query)
                self.oracle_connection.commit()
            elif query_type == 'INSERTMANY' or query_type == 'UPDATEMANY':
                self.oracle_cursor.executemany(query, data)
                self.oracle_connection.commit()
            elif query_type == 'SELECT':
                result = self.oracle_cursor.execute(query)
        except ora.DatabaseError as e:
            error = f'ERROR: There is a problem with Oracle {e}\n{query} @ {str(dt.now())}'
        except Exception as e:
            error = f'ERROR: There is a problem: {e} in execution of query {query} @ {str(dt.now())}'

        finally:
            if result is not None and error is None:
                rows = self.oracle_cursor.fetchall()
                # if cur:
                #     cur.close()
                # if con:
                #     con.close()
                return f'INFO: Query({query}) executed successfully @ {str(dt.now())}', rows
            else:
                # if cur:
                #     cur.close()
                # if con:
                #     con.close()
                if error is not None:
                    return f'{error}\n {str(dt.now())}', None
                else:
                    return f'INFO: Query({query}) executed successfully @ {str(dt.now())}', None
            return f'ERROR: Something went wrong @ {str(dt.now())}', None

