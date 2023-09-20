import email.utils
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import jinja2

from dotenv import load_dotenv

load_dotenv()

EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')


def send_email(to_addr, message, title):
    msg = MIMEMultipart()
    msg['From'] = email.utils.formataddr(('Bulgarian Citizenship Bot', EMAIL_ADDRESS))
    msg['To'] = to_addr
    msg['Subject'] = title

    environment = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
    template = environment.get_template("email_template.html")

    context = {
        "message": message,
    }

    message = template.render(context)
    msg.attach(MIMEText(message, 'html'))

    try:
        mailserver = smtplib.SMTP('smtp.yandex.ru', 587)
        mailserver.set_debuglevel(False)
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.ehlo()
        mailserver.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        mailserver.sendmail(EMAIL_ADDRESS, 'egor.karitskiy@gmail.com', msg.as_string())
        mailserver.quit()
    except smtplib.SMTPException as error:
        raise RuntimeError(
            f"email error: {error}."
        )


send_email('egor.karitskiy@gmail.com', 'Я люблю тебя, Жизнь!', 'Проверка связи')
