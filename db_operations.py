import re
import os

from urllib.parse import urlparse

import psycopg2
import datetime

from dotenv import load_dotenv

load_dotenv()

DB_URI = os.getenv('DATABASE_URL')

db_url_parse = urlparse(DB_URI)
username = db_url_parse.username
password = db_url_parse.password
database = db_url_parse.path[1:]
hostname = db_url_parse.hostname
port = db_url_parse.port


def get_user_statuses_list(user_id):
    """for future usage, when list of statuses will be needed"""
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_select_query = f"SELECT status, COALESCE(to_char(status_date, 'DD.MM.YYYY'), '') " \
                           f"AS status_date_date FROM statuses " \
                           f"WHERE user_id = '{user_id}' ORDER BY id DESC"
        cursor.execute(sql_select_query)
        select_result = cursor.fetchall()
        if not select_result:
            return None
        else:
            return select_result

    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def log_record(user_id, status_text, message):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_insert_query = f""" INSERT INTO logs (user_id, status_text, timestamp, message) VALUES (%s,%s,%s,%s)"""

        record_to_insert = (user_id, status_text, datetime.datetime.now(datetime.timezone.utc), message)

        cursor.execute(sql_insert_query, record_to_insert)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def time_delta_to_str(t_delta, fmt):
    d = {"days": t_delta.days}
    d["hours"], rem = divmod(t_delta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def append_new_status(user_id, status_text):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_insert_query = f""" INSERT INTO statuses (user_id, status, status_date) VALUES (%s,%s,%s)"""

        if 'Образувана преписка' in status_text:
            year_date_text = re.search("(\d\d\.\d\d\.\d{4})", status_text)
            if year_date_text is not None:
                year_date_text = year_date_text.group(1)
                datetime_object = datetime.datetime.strptime(year_date_text, '%d.%m.%Y')
                timestamp = datetime_object.replace(tzinfo=datetime.timezone.utc)
                record_to_insert = (user_id, status_text, timestamp)
            else:
                record_to_insert = (user_id, status_text, datetime.datetime.now(datetime.timezone.utc))
        else:
            record_to_insert = (user_id, status_text, datetime.datetime.now(datetime.timezone.utc))

        cursor.execute(sql_insert_query, record_to_insert)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}.")


def last_status(user_id):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_select_query = f"SELECT * FROM statuses WHERE user_id = '{user_id}' ORDER BY id DESC LIMIT 1"
        cursor.execute(sql_select_query)
        select_result = cursor.fetchall()
        if not select_result:
            return None
        else:
            return select_result[0][1]

    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def last_status_date(user_id):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_select_query = f"SELECT * FROM statuses WHERE user_id = '{user_id}' ORDER BY id DESC LIMIT 1"
        cursor.execute(sql_select_query)
        select_result = cursor.fetchall()
        if not select_result:
            return None
        else:
            return select_result[0][2]

    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def user_petition_number_from_db(user_id):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_select_query = f"SELECT * FROM creds WHERE user_id = '{user_id}'"
        cursor.execute(sql_select_query)
        select_result = cursor.fetchall()
        if not select_result:
            return None
        else:
            return select_result[0][1]

    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def user_pin_from_db(user_id):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_select_query = f"SELECT * FROM creds WHERE user_id = '{user_id}'"
        cursor.execute(sql_select_query)
        select_result = cursor.fetchall()
        if not select_result:
            return None
        else:
            return select_result[0][2]

    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def new_user_creds_record(user_id, language):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_insert_query = \
            f""" INSERT INTO creds (user_id, petition_no, pin, language, email) VALUES (%s,%s,%s,%s,%s)"""
        record_to_insert = (user_id, '0', '0', language, '0')
        cursor.execute(sql_insert_query, record_to_insert)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def delete_user_creds_record(user_id):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_delete_query = f""" DELETE FROM creds WHERE user_id = '{user_id}'"""
        cursor.execute(sql_delete_query)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def update_user_pin(user_id, pin):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_insert_query = f"UPDATE creds SET pin='{pin}' where user_id='{user_id}'"
        cursor.execute(sql_insert_query)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def update_user_email(user_id, email):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_insert_query = f"UPDATE creds SET email='{email}' where user_id='{user_id}'"
        cursor.execute(sql_insert_query)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def get_translated_message(message_code, language):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_select_query = f"SELECT {language} FROM messages WHERE message_code = '{message_code}'"
        cursor.execute(sql_select_query)
        select_result = cursor.fetchall()
        if not select_result:
            return None
        else:
            return select_result[0][0]

    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def update_user_petition_number(user_id, petition_no):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_insert_query = f"UPDATE creds SET petition_no='{petition_no}' where user_id='{user_id}'"
        cursor.execute(sql_insert_query)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def get_users_ids_from_db():
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_select_query = f"SELECT user_id FROM creds"
        cursor.execute(sql_select_query)
        select_result = cursor.fetchall()
        if not select_result:
            return None
        else:
            return select_result

    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def user_language_from_db(user_id):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_select_query = f"SELECT * FROM creds WHERE user_id = '{user_id}'"
        cursor.execute(sql_select_query)
        select_result = cursor.fetchall()
        if not select_result:
            return None
        else:
            return select_result[0][3]

    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


def user_email_from_db(user_id):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_select_query = f"SELECT * FROM creds WHERE user_id = '{user_id}'"
        cursor.execute(sql_select_query)
        select_result = cursor.fetchall()
        if not select_result:
            return None
        else:
            return select_result[0][4]

    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )
