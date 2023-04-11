import asyncio
import os
import time

from dotenv import load_dotenv
import telegram
from telegram import Bot
from telegram.ext import Application

from db_operations import (
    log,
    append_new_status,
    last_status,
    user_petition_number_from_db,
    user_pin_from_db,
    get_translated_message,
    get_users_ids_from_db,
    user_language_from_db,
    user_email_from_db,
    delete_user_creds_record
)

from email_operations import send_email
from site_operations import retrieve_status_from_web_site

load_dotenv()

loop = asyncio.get_event_loop()
asyncio.set_event_loop(loop)


TELEGRAM_TOKEN = os.getenv('REAL_TELEGRAM_TOKEN')


async def send_announce_message():
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    users_list = get_users_ids_from_db()
    for user_record in users_list:
        for user_id in user_record:
            language_code = user_language_from_db(user_id)
            reply_text = (get_translated_message('announce_message', language_code))
            # await bot.send_message(chat_id=user_id, text=reply_text)
            await bot.send_message(chat_id=80810688, text=reply_text)
            log('announce', f'Announce message sent for user {user_id}. ')


try:

    asyncio.run(send_announce_message())
except KeyboardInterrupt:
    pass
