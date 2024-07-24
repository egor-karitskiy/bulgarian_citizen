import os
import time

from dotenv import load_dotenv

from telegram import Bot

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
    delete_user_creds_record,
    long_wrong_creds_status,
    get_announce_status,
    update_announce_status
)

from email_operations import send_email
from site_operations import retrieve_status_from_web_site
from translation_operations import translate

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')


async def checking_statuses_routine():
    bot = Bot(TELEGRAM_TOKEN)
    users_list = get_users_ids_from_db()
    for user_record in users_list:
        for user_id in user_record:
            user_petition_number = user_petition_number_from_db(user_id)
            user_pin = user_pin_from_db(user_id)
            creds_provided = True
            if user_pin == '0':
                creds_provided = False
            if user_petition_number == '0':
                creds_provided = False

            if creds_provided:
                time.sleep(60)
                fresh_status = retrieve_status_from_web_site(user_petition_number, user_pin)
                if fresh_status == 'No status appeared':
                    log('routine check', f'CAPTCHA detected. No way to get proper status.')
                if fresh_status != 'No status appeared':
                    last_status_from_db = last_status(user_id)
                    language_code = user_language_from_db(user_id)
                    translated_status = translate(fresh_status, language_code)
                    log('routine check', f'Status for user {user_id} is {fresh_status}')
                    if fresh_status != last_status_from_db:
                        try:
                            reply_text = (get_translated_message('status_changed_message', language_code)
                                          % (fresh_status, translated_status))
                            await bot.send_message(user_id, reply_text)
                            log('routine check', f'Changed status message sent for user {user_id}. '
                                                 f'New status is {fresh_status}')
                            to_addr = user_email_from_db(user_id)
                            mail_title = get_translated_message('status_changed_email_title', language_code)
                            mail_message = (get_translated_message('status_changed_email_message', language_code)
                                            % fresh_status)
                            if to_addr != '0':
                                send_email(to_addr, mail_message, mail_title)
                                log('email', f'Email to {user_id} has been sent. During routine check')

                        except Exception as error:
                            raise RuntimeError(f'Message sent error: {error}')
                        append_new_status(user_id, fresh_status)
                        log('statuses', f'New status added to DB for user {user_id}. '
                                        f'Status is {fresh_status}')


async def database_empty_creds_cleaner():
    users_list = get_users_ids_from_db()
    bot = Bot(TELEGRAM_TOKEN)
    log('DB cleaner', 'DB cleaner routine started')

    for user_record in users_list:
        for user_id in user_record:
            user_petition_number = user_petition_number_from_db(user_id)
            language_code = user_language_from_db(user_id)
            user_pin = user_pin_from_db(user_id)
            if user_petition_number == '0' and user_pin == '0':
                delete_user_creds_record(user_id)
                log('DB cleaner', f'Creds record for user {user_id} has been deleted due to empty creds')
            if long_wrong_creds_status(user_id):
                log('DB cleaner', f'Creds record for user {user_id} has been deleted due to wrong creds')
                try:
                    reply_text = (get_translated_message('long_wrong_creds_message', language_code))
                    await bot.send_message(user_id, reply_text)
                    log('DB cleaner', f'Wrong creds message is sent for user {user_id}')
                    to_addr = user_email_from_db(user_id)
                    mail_title = 'Wrong creds!'
                    mail_message = get_translated_message('long_wrong_creds_message', language_code)
                    if to_addr != '0':
                        send_email(to_addr, mail_message, mail_title)
                        log('DB cleaner', f'Wrong creds email is sent for user {user_id}')

                except Exception as error:
                    raise RuntimeError(f'Message sent error: {error}')
                delete_user_creds_record(user_id)


async def send_announce_message():
    bot = Bot(TELEGRAM_TOKEN)
    users_list = get_users_ids_from_db()
    for user_record in users_list:
        for user_id in user_record:
            language_code = user_language_from_db(user_id)
            announce_status = get_announce_status(user_id)
            reply_text = (get_translated_message('announce_message', language_code))
            # await bot.send_message(chat_id=user_id, text=reply_text)
            if announce_status:
                await bot.send_message(chat_id=user_id, text=reply_text)
                update_announce_status(user_id, False)
            log('announce', f'Announce message sent for user {user_id}. ')
