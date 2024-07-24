import re

import requests
from bs4 import BeautifulSoup


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

    status_object = re.search('''<div class="validation-summary-errors text-danger"><ul><li>((.|\n)*?)</li>''',
                              request_given.text)

    if status_object:
        status = status_object.group(1)
        if 'Липсват данни' in status or 'Липсва молба' in status:
            return "Incorrect credentials"
    else:
        status = "CAPTCHA"
    return status


print(retrieve_status_from_web_site(req_num=5, pin='5'))
