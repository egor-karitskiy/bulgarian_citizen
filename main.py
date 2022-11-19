import re
import os
from urllib.parse import urlparse

import psycopg2
import requests
import logging
import datetime

import telegram
from tabulate import tabulate
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
DB_URI = os.getenv('DB_URI')

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


def get_req_token():
    r = requests.get("https://publicbg.mjs.bg/BgInfo/Home/Enroll")
    soup = BeautifulSoup(r.text, 'html.parser')
    for link in soup.find_all('form'):
        if link.get('action') == '/BgInfo/Home/Enroll':
            for field in link.find_all('input'):
                if field.get('name') == '__RequestVerificationToken':
                    return field.get('value')


def request_status(req_num, pin):
    token = get_req_token()
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
    is_new_user = True
    user_id = update.message.from_user.id
    if user_petition_number_from_db(user_id) is not None or user_pin_from_db(user_id) is not None:
        is_new_user = False

    if is_new_user:
        reply_text = f"Hi! My name is Bulgarian Citizen bot — to be shorty — BulCit " \
                     f"(nothing familiar to 'Bullshit'!). \n" \
                     f"I help check and monitor statuses of your Bulgarian " \
                     f"citizenship petition! \n" \
                     f"Please provide credentials (petition number and PIN) given by " \
                     f"Bulgarian Ministry of Justice. \n" \
                     f"Push corresponding buttons below to provide info to me."

    else:
        reply_text = f"Hi again! Here I am! The BulCit bot! \n" \
                     f"If you'd like to update your credentials (PIN or petition number)" \
                     f" please use buttons below. \n" \
                     f"If you'd like to see freshly updated status of your petition " \
                     f"please push 'Done' button. \n"

    await update.message.reply_text(reply_text, reply_markup=markup)

    return CHOOSING


async def regular_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user for info about the selected predefined choice."""
    text = update.message.text.lower()
    context.user_data["button"] = text
    user_id = update.message.from_user.id
    if user_pin_from_db(user_id) is None or user_petition_number_from_db(user_id) is None:
        new_user_creds_record(user_id)
    await update.message.reply_text(f"Please send me your {text}, or type NO if you don't like to "
                                    f"change {text} already provided by you earlier.")

    return TYPING_REPLY


async def received_information(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store info provided by user and ask for the next category."""
    text = update.message.text
    pressed_button = context.user_data["button"]
    del context.user_data["button"]

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
        reply_text = f"Current info provided by you is the following:\n" \
                     f"Petition number: {user_petition_number_from_db(user_id)} \n" \
                     f"PIN: {user_pin_from_db(user_id)}\n" \
                     f"We are all set! Please push 'Done' button."
    elif is_pin_provided and not is_petition_number_provided:
        reply_text = f"PIN is provided. But petition number is not!\n" \
                     f"Please push 'Petition number' button!: {user_petition_number_from_db(user_id)}, {is_petition_number_provided}"
    elif not is_pin_provided and is_petition_number_provided:
        reply_text = f"Petition number is provided. But PIN is not!\n" \
                     f"Please push 'PIN' button!:"
    else:
        is_petition_number_provided = True
        reply_text = f"Credentials are not provided yet.\n" \
                     f"Please push 'Petition number' or 'PIN' button!: {user_petition_number_from_db(user_id)}, {is_petition_number_provided}"

    await update.message.reply_text(reply_text, reply_markup=markup)

    return CHOOSING


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id

    is_pin_provided = True
    if user_pin_from_db(user_id) is None or user_pin_from_db(user_id) == '0':
        is_pin_provided = False

    is_petition_number_provided = True
    if user_petition_number_from_db(user_id) is None or user_petition_number_from_db(user_id) == '0':
        is_petition_number_provided = False

    fresh_status = request_status(user_petition_number_from_db(user_id), user_pin_from_db(user_id))
    last_status_from_db = last_status(user_id)

    if last_status_from_db is None or fresh_status != last_status_from_db:
        append_new_status(user_id, fresh_status)

    if is_pin_provided and is_petition_number_provided:
        user_statuses = tabulate(get_user_statuses_list(user_id), headers=['Status', 'Date'])
        days = datetime.datetime.now() - last_status_date(user_id)
        days_str = time_delta_to_str(days, "{days} days")
    else:
        days_str = '0'

    await update.message.reply_text(
        f"Current info provided by you is the following:\n"
        f"%s\n"
        f"%s\n"
        f"\n"
        f"%s\n"

        % (
            f"Your petition number: {user_petition_number_from_db(user_id)}"
            if is_petition_number_provided
            else "Petition number is not provided yet. Please use /start menu.",

            f"Your PIN: {user_pin_from_db(user_id)}"
            if is_pin_provided
            else "PIN is not provided yet. Please use /start menu.",

            f"Status of your petition is:\n"
            f"{fresh_status}\n"
            f"\n"
            f"{days_str} passed since last status change.\n"
            f"\n"
            f"Monitoring is ON.\n"
            f"I'll let you know when status is changed."

            if is_pin_provided and is_petition_number_provided
            else ""
        ),

        reply_markup=ReplyKeyboardRemove(),
    )

        # await update.message.reply_text(f'Current statuses log: \n\n\n```\n{user_statuses}```', parse_mode='Markdown')
        # await update.message.reply_text(f'{days_str} passed since last status change.')
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
            f"DB error {error}."
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
        sql_insert_query = """ INSERT INTO statuses (user_id, status, status_date) VALUES (%s,%s,%s)"""

        if 'Образувана преписка' in status_text:
            year_date_text = re.search("(\d\d\.\d\d\.\d{4})", status_text).group(1)
            datetime_object = datetime.datetime.strptime(year_date_text, '%d.%m.%Y')
            timestamp = datetime_object.replace(tzinfo=datetime.timezone.utc)
            record_to_insert = (user_id, status_text, timestamp)

        else:
            record_to_insert = (user_id, status_text, datetime.datetime.now(datetime.timezone.utc))

        cursor.execute(sql_insert_query, record_to_insert)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        raise RuntimeError(
            f"DB error {error}."
        )


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


def new_user_creds_record(user_id):
    try:
        connection = psycopg2.connect(
            database=database,
            user=username,
            password=password,
            host=hostname,
            port=port
        )
        cursor = connection.cursor()
        sql_insert_query = """ INSERT INTO creds (user_id, petition_no, pin) VALUES (%s,%s,%s)"""
        record_to_insert = (user_id, '0', '0')
        cursor.execute(sql_insert_query, record_to_insert)
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


async def checking_statuses_routine():
    bot = Bot(TELEGRAM_TOKEN)
    users_list = get_users_ids_from_db()
    for user_record in users_list:
        for user_id in user_record:
            fresh_status = request_status(user_petition_number_from_db(user_id), user_pin_from_db(user_id))
            last_status_from_db = last_status(user_id)
            if fresh_status != last_status_from_db:
                try:
                    await bot.send_message(user_id, f'Hey there!!! Here is the new status of your '
                                                    f'petition: \n '
                                                    f'{fresh_status}!')
                except Exception as error:
                    raise RuntimeError(f'Message sent error: {error}')
                append_new_status(user_id, fresh_status)


def main() -> None:
    """Run the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(checking_statuses_routine, 'interval', seconds=10800)
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
    application.run_polling()


if __name__ == "__main__":
    main()
