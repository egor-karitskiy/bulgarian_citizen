import re
import os
from urllib.parse import urlparse

import psycopg2
import requests
import logging
import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bs4 import BeautifulSoup
from dotenv import load_dotenv

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
DB_URI = os.getenv('DATABASE_URL')

db_url_parse = urlparse(DB_URI)
username = db_url_parse.username
password = db_url_parse.password
database = db_url_parse.path[1:]
hostname = db_url_parse.hostname
port = db_url_parse.port

CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(3)

reply_keyboard = [
    ["Petition number", "PIN"],
    ["Done"],
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def get_proper_web_token():
    r = requests.get("https://publicbg.mjs.bg/BgInfo/Home/Enroll")
    soup = BeautifulSoup(r.text, 'html.parser')
    for link in soup.find_all('form'):
        if link.get('action') == '/BgInfo/Home/Enroll':
            for field in link.find_all('input'):
                if field.get('name') == '__RequestVerificationToken':
                    return field.get('value')


def retrieve_status_from_web_site(req_num, pin):
    token = get_proper_web_token()
    data = {
        '__RequestVerificationToken': token,
        'reqNum': req_num,
        'pin': pin
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:106.0) Gecko/20100101 Firefox/106.0',
        'Referer': 'https://publicbg.mjs.bg/BgInfo/Home/Enroll',
        'Origin': 'https://publicbg.mjs.bg'
    }
    request_given = requests.post('https://publicbg.mjs.bg/BgInfo/Home/Enroll', headers=headers, data=data)

    status_object = re.search('''<div class="validation-summary-errors text-danger"><ul><li>(.+?)\n''',
                              request_given.text)

    if status_object:
        status = status_object.group(1)
        if 'Липсват данни' in status:
            return "Incorrect credentials"
    else:
        status = "No status appeared"
    return status


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id

    language_code = update.message.from_user.language_code
    if language_code != 'ru':
        language_code = 'en'

    is_new_user = True
    if user_petition_number_from_db(user_id) is not None or user_pin_from_db(user_id) is not None:
        is_new_user = False

    if is_new_user:
        reply_text = get_translated_message('new_user_welcome_message', language_code)
    else:
        reply_text = get_translated_message('existing_user_welcome_message', language_code)

    await update.message.reply_text(reply_text, reply_markup=markup)

    return CHOOSING


async def regular_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    context.user_data["button"] = text

    user_id = update.message.from_user.id

    language_code = update.message.from_user.language_code
    if language_code != 'ru':
        language_code = 'en'

    if user_pin_from_db(user_id) is None or user_petition_number_from_db(user_id) is None:
        new_user_creds_record(user_id, language_code)

    if text == 'pin':
        reply_text = get_translated_message('give_me_your_pin', language_code)
    elif text == 'petition number':
        reply_text = get_translated_message('give_me_your_petition_number', language_code)
    else:
        reply_text = ''
    await update.message.reply_text(reply_text)

    return TYPING_REPLY


async def received_information(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store info provided by user and ask for the next category."""
    text = update.message.text
    pressed_button = context.user_data["button"]
    del context.user_data["button"]

    language_code = update.message.from_user.language_code
    if language_code != 'ru':
        language_code = 'en'

    user_id = update.message.from_user.id

    is_wrong_input = False
    if text.lower() == 'no' or text.lower() == 'pin' or text.lower() == 'petition number':
        is_wrong_input = True

    is_pin_provided = True
    if user_pin_from_db(user_id) is None or user_pin_from_db(user_id) == '0':
        is_pin_provided = False

    is_petition_number_provided = True
    if user_petition_number_from_db(user_id) is None or user_petition_number_from_db(user_id) == '0':
        is_petition_number_provided = False

    if pressed_button == 'pin' and not is_wrong_input:
        update_user_pin(user_id, text)
        is_pin_provided = True

    if pressed_button == 'petition number' and not is_wrong_input:
        update_user_petition_number(user_id, text)
        is_petition_number_provided = True

    if is_pin_provided and is_petition_number_provided:
        reply_text = (get_translated_message('all_set_message', language_code)
                      % (user_petition_number_from_db(user_id), user_pin_from_db(user_id)))
    elif is_pin_provided and not is_petition_number_provided:
        reply_text = get_translated_message('pin_provided_pn_not', language_code)
    elif not is_pin_provided and is_petition_number_provided:
        reply_text = get_translated_message('pn_provided_pin_not', language_code)
    else:
        reply_text = get_translated_message('no_creds_provided', language_code)

    await update.message.reply_text(reply_text, reply_markup=markup)

    return CHOOSING


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id

    language_code = update.message.from_user.language_code
    if language_code != 'ru':
        language_code = 'en'

    is_pin_provided = True
    if user_pin_from_db(user_id) is None or user_pin_from_db(user_id) == '0':
        is_pin_provided = False

    is_petition_number_provided = True
    if user_petition_number_from_db(user_id) is None or user_petition_number_from_db(user_id) == '0':
        is_petition_number_provided = False

    fresh_status = retrieve_status_from_web_site(user_petition_number_from_db(user_id),
                                                 user_pin_from_db(user_id))
    last_status_from_db = last_status(user_id)

    if last_status_from_db is None or fresh_status != last_status_from_db:
        append_new_status(user_id, fresh_status)

    if is_pin_provided and is_petition_number_provided:
        days = datetime.datetime.now() - last_status_date(user_id)
        days_str = time_delta_to_str(days, "{days}")
        log_record(user_id, fresh_status, 'user check')
    else:
        days_str = '0'

    if is_petition_number_provided and is_pin_provided:
        reply_text = (get_translated_message('done_full_message', language_code)
                      % (user_petition_number_from_db(user_id),
                         user_pin_from_db(user_id),
                         fresh_status,
                         days_str))

    elif is_pin_provided and not is_petition_number_provided:
        reply_text = (get_translated_message('pin_provided_pn_not', language_code)
                      % (user_pin_from_db(user_id)))

    elif is_petition_number_provided and not is_pin_provided:
        reply_text = (get_translated_message('pn_provided_pin_not', language_code)
                      % (user_petition_number_from_db(user_id)))
    else:
        reply_text = get_translated_message('done_no_creds', language_code)

    await update.message.reply_text(reply_text, reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def time_delta_to_str(t_delta, fmt):
    d = {"days": t_delta.days}
    d["hours"], rem = divmod(t_delta.seconds, 3600)
    d["minutes"], d["seconds"] = divmod(rem, 60)
    return fmt.format(**d)


def get_user_statuses_list(user_id):
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
            "DB error {error}."
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
            "DB error {error}."
        )


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
            "DB error {error}.")


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
            "DB error {error}."
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
            "DB error {error}."
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
            "DB error {error}."
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
            "DB error {error}."
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
        sql_insert_query = f""" INSERT INTO creds (user_id, petition_no, pin, language) VALUES (%s,%s,%s,%s)"""
        record_to_insert = (user_id, '0', '0', language)
        cursor.execute(sql_insert_query, record_to_insert)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            "DB error {error}."
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
            "DB error {error}."
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
            "DB error {error}."
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
            "DB error {error}."
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
            "DB error {error}."
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
            "DB error {error}."
        )


async def checking_statuses_routine():
    bot = Bot(TELEGRAM_TOKEN)
    users_list = get_users_ids_from_db()
    for user_record in users_list:
        for user_id in user_record:
            fresh_status = retrieve_status_from_web_site(user_petition_number_from_db(user_id),
                                                         user_pin_from_db(user_id))
            last_status_from_db = last_status(user_id)
            language_code = user_language_from_db(user_id)
            log_record(user_id, fresh_status, 'routine check')
            if fresh_status != last_status_from_db:
                try:
                    reply_text = (get_translated_message('status_changed_message', language_code)
                                  % fresh_status)
                    await bot.send_message(user_id, reply_text)
                except Exception as error:
                    raise RuntimeError('Message sent error: {error}')
                append_new_status(user_id, fresh_status)


def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(checking_statuses_routine, 'interval', hours=3)
    scheduler.start()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                MessageHandler(
                    filters.Regex("^(Petition number|PIN)$"), regular_choice)
            ],
            TYPING_CHOICE: [
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND | filters.Regex("^Done$")), regular_choice
                )
            ],
            TYPING_REPLY: [
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND | filters.Regex("^Done$")),
                    received_information,
                )
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
        name="my_conversation",
        persistent=False,
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.run_polling()


if __name__ == "__main__":
    main()
