import datetime
import os

from github import Github
from dotenv import load_dotenv



load_dotenv()

GIT_TOKEN = os.getenv('GIT_TOKEN')

github = Github(GIT_TOKEN)
repository = github.get_user().get_repo('bulgarian_citizen')
f = repository.create_file('persistent.dat', "create_file via PyGithub", "egsdfgsdfg")



user_data ={}
user_data['statuses'] = {'status_no': [], 'text': [], 'date': []}

user_data['pin'] = '23423'
user_data['petition number'] = '23423/234'

for i in range(5):
    user_data['statuses']['status_no'].append(i)
    user_data['statuses']['text'].append(f'fasdf sdf {i}sdf')
    user_data['statuses']['date'].append(datetime.date.today())

user_data['statuses']['text'][3] = 'asdfasdf adfasdfasfdasdfasdfasfasdfafd'

last_status = user_data['statuses']['text'][max(user_data['statuses']['status_no'])]

for i in user_data['statuses']['status_no']:
    if user_data['statuses']['status_no'][i] == 3:
        print(user_data['statuses']['status_no'][i])
        print(user_data['statuses']['text'][i])
        print(user_data['statuses']['date'][i])

print(last_status)

