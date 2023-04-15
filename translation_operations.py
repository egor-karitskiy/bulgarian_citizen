import os
import json
import requests

from dotenv import load_dotenv

load_dotenv()
Y_KEY = os.getenv('Y_KEY')


def translate(src_text, target_lang_code):
    folder_id = 'b1g7hdtdihutak5vbla5'
    texts = [src_text]

    body = {
        "targetLanguageCode": target_lang_code,
        "languageCodeHints": ["bg", "en"],
        "texts": texts,
        "folderId": folder_id,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {Y_KEY}"
    }

    response = requests.post('https://translate.api.cloud.yandex.net/translate/v2/translate',
                             json=body,
                             headers=headers
                             )
    jdict = json.loads(response.text)

    return jdict['translations'][0]['text']
