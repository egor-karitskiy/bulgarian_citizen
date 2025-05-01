import os
import logging
import datetime
import time
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update

from email_operations import send_email
from site_operations import retrieve_status_from_web_site
from translation_operations import translate

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from routine_operations import (
    checking_statuses_routine,
    database_empty_creds_cleaner,
    send_announce_message,
    test_coroutine
)

from db_operations import (
    log,
    time_delta_to_str,
    append_new_status,
    last_status,
    last_status_date,
    user_petition_number_from_db,
    user_pin_from_db,
    new_user_creds_record,
    update_user_pin,
    update_user_email,
    get_translated_message,
    update_user_petition_number,
    user_email_from_db,
)

time.sleep(3)

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(3)

reply_keyboard = [
    ["Petition number", "PIN"],
    ["Done"],
]

markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def is_new_user(user_id):
    if user_petition_number_from_db(user_id) is not None or user_pin_from_db(user_id) is not None:
        return False
    return True


async def email_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id

    language_code = update.message.from_user.language_code
    if language_code != 'ru':
        language_code = 'en'

    if is_new_user(user_id):
        reply_text = get_translated_message('email_new_user', language_code)
        await update.message.reply_text(reply_text)
        return ConversationHandler.END
    else:
        reply_text = get_translated_message('give_me_your_email', language_code)
        await update.message.reply_text(reply_text)
    return 1


async def email_address_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text

    language_code = update.message.from_user.language_code
    if language_code != 'ru':
        language_code = 'en'

    user_id = update.message.from_user.id

    is_wrong_input = False
    if text.lower() == 'no' or text.lower() == 'pin' or text.lower() == 'petition number':
        is_wrong_input = True

    if not is_wrong_input:
        update_user_email(user_id, text)
        reply_text = get_translated_message('email_provided', language_code)
        log('email', f'email address {text} added for user {user_id}')
        await update.message.reply_text(reply_text)

    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    user_name = update.message.from_user.username

    language_code = update.message.from_user.language_code
    if language_code != 'ru':
        language_code = 'en'

    if is_new_user(user_id):
        reply_text = get_translated_message('new_user_welcome_message', language_code)
        log('start message', f'New user {user_name} has received welcome message')
    else:
        reply_text = get_translated_message('existing_user_welcome_message', language_code)
        log('start message', f'Existing user {user_name} has received welcome message')

    await update.message.reply_text(reply_text, reply_markup=markup)

    return CHOOSING


async def regular_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.lower()
    context.user_data["button"] = text

    user_id = update.message.from_user.id
    user_name = update.message.from_user.username
    user_full_name = update.message.from_user.full_name

    language_code = update.message.from_user.language_code
    if language_code != 'ru':
        language_code = 'en'

    if user_pin_from_db(user_id) is None or user_petition_number_from_db(user_id) is None:
        new_user_creds_record(user_id, language_code, user_name, user_full_name)
        log('credentials', f'New credentials have been added for user {user_name}')

    if text == 'pin':
        reply_text = get_translated_message('give_me_your_pin', language_code)
    elif text == 'petition number':
        reply_text = get_translated_message('give_me_your_petition_number', language_code)
    else:
        reply_text = ''
    await update.message.reply_text(reply_text)

    return TYPING_REPLY


async def received_information(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_name = update.message.from_user.username
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
        log('credentials', f'PIN for user {user_name} has been updated. New value is {text}')

    if pressed_button == 'petition number' and not is_wrong_input:
        update_user_petition_number(user_id, text)
        is_petition_number_provided = True
        log('credentials', f'Petition number for user {user_name} has been updated. New value is {text}')

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
    user_name = update.message.from_user.username

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
    translated_status = translate(fresh_status, language_code)
    last_status_from_db = last_status(user_id)
    if fresh_status == 'No status appeared':
        log('manual check', f'CAPTCHA detected. No way to get proper status.')
        reply_text = 'CAPTCHA detected. No way to get proper status.'
    else:
        if last_status_from_db is None:
            append_new_status(user_id, fresh_status)
            log('statuses', f'Status added for user {user_name} for the first time. New status is {fresh_status}')
            last_status_from_db = last_status(user_id)

        if fresh_status != last_status_from_db:
            append_new_status(user_id, fresh_status)
            log('statuses', f'Status added for user {user_name}. New status is {fresh_status}')

        if is_pin_provided and is_petition_number_provided:
            days = datetime.datetime.now() - last_status_date(user_id)
            days_str = time_delta_to_str(days, "{days}")

            log('statuses', f'User {user_name} has checked the actual status manually. Status is {fresh_status}')
        else:
            days_str = '0'

        if is_petition_number_provided and is_pin_provided:
            reply_text = (get_translated_message('done_full_message', language_code)
                          % (user_petition_number_from_db(user_id),
                             user_pin_from_db(user_id),
                             fresh_status,
                             translated_status,
                             days_str))
            to_addr = user_email_from_db(user_id)
            mail_title = get_translated_message('done_email_title', language_code)
            mail_message = (get_translated_message('done_email_message', language_code)
                            % (user_petition_number_from_db(user_id),
                               user_pin_from_db(user_id),
                               fresh_status,
                               translated_status,
                               days_str))
            if to_addr != '0':
                send_email(to_addr, mail_message, mail_title)
                log('email', f'Email to {user_name} has been sent during manual user check')

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


async def scheduled_tasks():
    scheduler = AsyncIOScheduler()
    scheduler.configure(timezone="Europe/Moscow")
    scheduler.start()
    scheduler.add_job(checking_statuses_routine, 'interval', hours=23)
    scheduler.add_job(database_empty_creds_cleaner, 'interval', days=5)
    scheduler.add_job(send_announce_message, 'interval', hours=11)
    log('main', 'Checking routines have been started')
    while True:
        await asyncio.sleep(1000)

def main() -> None:
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    log('main', 'Application started')

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

    email_handler = ConversationHandler(
        entry_points=[CommandHandler("email", email_request)],
        states={
            1: [
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND | filters.Regex("^@$")), email_address_receiver
                )
            ]
        },
        fallbacks=[MessageHandler(filters.Regex("^$"), start)],
        name="my_conversation_email",
        persistent=False,

    )

    application.add_handler(conv_handler)
    application.add_handler(email_handler)
    application.add_handler(CommandHandler("start", start))
    asyncio.run(scheduled_tasks())
    application.run_polling(close_loop=False)

    log('main', 'Application has been stopped')


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        pass
