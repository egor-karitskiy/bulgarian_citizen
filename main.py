import requests, re
from bs4 import BeautifulSoup
import json


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


print(request_status('16547/2022', '474698'))
