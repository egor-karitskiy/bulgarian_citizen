import datetime
import re

import db_operations

users_list = db_operations.get_users_ids_from_db()


for user_record in users_list:
    for user_id in user_record:
        status_text = db_operations.last_status(user_id)
        lines_count = status_text.count('\n')
        year_date_text = re.search("(\d\d\.\d\d\.\d{4})", status_text)
        print(status_text)
        # print('\n')

        if lines_count == 1 and 'Образувана преписка' in status_text and year_date_text is not None:
            year_date_text = year_date_text.group(1)
            datetime_object = datetime.datetime.strptime(year_date_text, '%d.%m.%Y')
            timestamp = datetime_object.replace(tzinfo=datetime.timezone.utc)
            print(f'Смотрим дату в тексте {timestamp}')
        else:
            print(f'Ставим текущую дату {datetime.datetime.now(datetime.timezone.utc)}')

        print('\n')
        print('\n')