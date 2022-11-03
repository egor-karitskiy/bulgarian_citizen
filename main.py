import re
import os
import time

import requests
import logging
import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from typing import Dict
from telegram import __version__ as TG_VER

try:
    from telegram import __version_info__
except ImportError:
    __version_info__ = (0, 0, 0, 0, 0)  # type: ignore[assignment]

if __version_info__ < (13, 0, 0, "alpha", 1):
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
    PicklePersistence,
    filters,
)

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

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


def facts_to_str(user_data: Dict[str, str]) -> str:
    """Helper function for formatting the gathered user info."""
    facts = [f"{key} - {value}" for key, value in user_data.items()]
    return "\n".join(facts).join(["\n", "\n"])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation, display any stored data and ask user for input."""
    if 'status' not in context.user_data:
        context.user_data['status'] = {'status_no': [], 'text': [], 'date': []}
    context.user_data['id'] = update.effective_user.id
    reply_text = f"Hi! My name is Bulgarian Citizen bot — to be shorty — BulCit " \
                 f"(nothing familiar to 'Bullshit'!). \n" \
                 f"I help with checking statuses and alerting of your Bulgarian " \
                 f"citizenship petition! \n"

    if 'pin' or 'petition number' not in context.user_data:
        reply_text += (
            "Please provide credentials (petition number and PIN) given by "
            "Bulgarian Ministry of Justice. "
            "Push corresponding buttons below to provide info to me."

        )
    await update.message.reply_text(reply_text, reply_markup=markup)

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
    """Display the gathered info and end the conversation."""
    chat_id = update.effective_message.chat_id
    if "choice" in context.user_data:
        del context.user_data["choice"]

    await update.message.reply_text(
        f"Current info provided by you is the following:\n"
        f"%s\n"
        f"%s\n"
        f"\n"
        f"%s\n"
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
        job_queue.run_repeating(check_status,
                                interval=3600,
                                chat_id=update.effective_user.id,
                                data=context.user_data)
        await update.message.reply_text('Status monitoring is on', reply_markup=ReplyKeyboardRemove(), )
    return ConversationHandler.END


async def check_status(context: ContextTypes.DEFAULT_TYPE) -> None:
    pin = context.job.data['pin']
    num = context.job.data['petition number']
    result = request_status(num, pin)

    if context.job.data['status']['status_no']:
        pin = context.job.data['pin']
        num = context.job.data['petition number']
        last_status_id = max(context.job.data['status']['status_no'])
        last_status = context.job.data['status']['text'][last_status_id]
        result = request_status(num, pin)

        if result != last_status:
            status_changed_message = f"Petition status has changed!\n" \
                                     f"New status is: {result}"
            await context.bot.send_message(context.job.chat_id, text=status_changed_message)

            context.job.data['status']['status_no'].append(last_status_id + 1)
            context.job.data['status']['text'].append(result)
            context.job.data['status']['date'].append(datetime.datetime.now())

    else:
        context.job.data['status']['status_no'].append(0)
        context.job.data['status']['text'].append(result)
        context.job.data['status']['date'].append(datetime.datetime.now())


def main() -> None:
    """Run the bot."""

    persistence = PicklePersistence(filepath="persistent_data_storage.dat")
    application = Application.builder().token(TELEGRAM_TOKEN).persistence(persistence).build()

    # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                MessageHandler(
                    filters.Regex("^(Petition number|PIN)$"), regular_choice)
                # ) ,
                # MessageHandler(filters.Regex("^Something else...$"), custom_choice),
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
