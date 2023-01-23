import json
import os

import jinja2
import requests

environment = jinja2.Environment(loader=jinja2.FileSystemLoader("templates/"))
template = environment.get_template("email_template.html")


def send_email(to_addr, message, title):
    context = {
        "message": message,
    }

    result_message = template.render(context)

    api_url = os.environ['TRUSTIFI_URL'] + '/api/i/v1/email'

    headers = {
        'x-trustifi-key': os.environ['TRUSTIFI_KEY'],
        'x-trustifi-secret': os.environ['TRUSTIFI_SECRET'],
        'Content-Type': 'application/json'
    }

    payload_structured = json.dumps({
        "recipients": [{
            "email": to_addr
        }],
        "title": title,
        "html": result_message,
        "from": {
            "name": "Bulgarian Citizenship Bot"
        }
    })

    requests.post(api_url, headers=headers, data=payload_structured.encode('utf-8'))
