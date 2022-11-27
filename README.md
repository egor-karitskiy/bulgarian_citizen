# "Bulgarian Citizenship Bot" telegram bot

This simple bot is created for quite rare need -- monitoring and alerting of changing statuses during official process of granting Bulgarian citizenship. 
The process takes around two-three years and statuses of petition are being changed very seldom. That's why it's convenient to have a background routine which regulary queries web-site of Bulgarian Ministry of Justice, retrieves petition status and alerts user when petition status is changed.

Most probably you could adapt this bot main feature to any task of this kind - users notification if some statuses are being changed.

Bot is available in Telegram as @bulcit_bot. You can use that one or you may fork it and create your own if you like. 

The routine worker of @bulcit_bot app is deployed on Heroku.

