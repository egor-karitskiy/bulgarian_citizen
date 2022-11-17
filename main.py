import re
import os
from urllib.parse import urlparse

import psycopg2
import requests
import logging
import datetime

from bs4 import BeautifulSoup
from dotenv import load_dotenv

from PGpersistence import PostgresPersistence

from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)

if __version_info__ < (20, 0, 0, "alpha", 1):
    raise RuntimeError(
        f"This bot is not compatible with your current version {TG_VER}."
    )
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters, PicklePersistence,
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

# Enable logging
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
    """Start the conversation, display any stored data and ask user for input."""
    reply_text = f"Hi! My name is Bulgarian Citizen bot — to be shorty — BulCit " \
                 f"(nothing familiar to 'Bullshit'!). \n" \
                 f"I help check and monitor statuses of your Bulgarian " \
                 f"citizenship petition! \n"

    if 'pin' not in context.user_data or 'petition number' not in context.user_data:
        reply_text += (
            "Please provide credentials (petition number and PIN) given by "
            "Bulgarian Ministry of Justice. \n"
            "Push corresponding buttons below to provide info to me."

        )
    else:
        reply_text += (
            "You have already provided your PIN and petition number to me. \n"
            "If you like to change credentials please use corresponding buttons below."
        )

    await update.message.reply_text(reply_text, reply_markup=markup)

    current_jobs = context.job_queue.jobs()
    for job in current_jobs:
        job.schedule_removal()

    return CHOOSING


async def regular_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user for info about the selected predefined choice."""
    text = update.message.text.lower()
    context.user_data["choice"] = text
    if context.user_data.get(text):
        reply_text = (
            f"Please send me your {text}. Saved {text} is: {context.user_data[text]}"
        )
    else:
        reply_text = f"Please send me your {text}."
    await update.message.reply_text(reply_text)

    return TYPING_REPLY


async def received_information(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store info provided by user and ask for the next category."""
    text = update.message.text
    category = context.user_data["choice"]
    context.user_data[category] = text.lower()
    del context.user_data["choice"]

    await update.message.reply_text(
        f"Current info provided by you is the following:\n"
        f"%s\n"
        f"%s\n"

        % (
            f"Your petition number: {context.user_data['petition number']}"
            if 'petition number' in context.user_data
            else "Petition number is not provided yet",

            f"Your PIN: {context.user_data['pin']}"
            if 'pin' in context.user_data
            else "PIN is not provided yet"),
        reply_markup=markup,
    )

    return CHOOSING


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        f"Current info provided by you is the following:\n"
        f"%s\n"
        f"%s\n"
        f"\n"
        f"%s\n"
        # f"{context.user_data['status']}"
        % (
            f"Your petition number: {context.user_data['petition number']}"
            if 'petition number' in context.user_data
            else "Petition number is not provided yet",

            f"Your PIN: {context.user_data['pin']}"
            if 'pin' in context.user_data
            else "PIN is not provided yet",

            f"Status of your petition is:\n"
            f"{request_status(context.user_data['petition number'], context.user_data['pin'])}"
            if 'petition number' and 'pin' in context.user_data
            else "No sufficient data for petition status request"
        ),

        reply_markup=ReplyKeyboardRemove(),
    )

    job_queue = context.job_queue
    if 'pin' in context.user_data and 'petition number' in context.user_data:
        job_queue.run_repeating(check_status_routine,
                                interval=10,
                                chat_id=update.effective_user.id,
                                data=context.user_data)
        await update.message.reply_text('Status monitoring is on', reply_markup=ReplyKeyboardRemove(), )
    return ConversationHandler.END


async def check_status_routine(context: ContextTypes.DEFAULT_TYPE) -> None:
    pin = context.job.data['pin']
    num = context.job.data['petition number']
    user_id = context.job.data['id']
    result = request_status(num, pin)

    if last_status(user_id) is not None:
        if last_status(user_id) != result:
            append_new_status(user_id, result)
            status_changed_message = f"Petition status has been changed!\n" \
                                     f"New status is: {result}"
            await context.bot.send_message(context.job.chat_id, text=status_changed_message)
    else:
        append_new_status(user_id, result)
        first_time_status_message = f"Petition status is the following:\n" \
                                    f"{result}"
        await context.bot.send_message(context.job.chat_id, text=first_time_status_message)


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


def main() -> None:
    """Run the bot."""
    application = Application.builder().token(TELEGRAM_TOKEN).persistence(PostgresPersistence(url=DB_URI)).build()

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
        persistent=True,
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == "__main__":
    main()
