# "Bulgarian citizen" telegram bot

This simple bot is created for quite rare need -- monitoring and alerting of changing statuses during official process of granting Bulgarian citizenship. 
The process takes around two years and statuses of petition are being changed very seldom. That's why it's convenient to have a background routine which requests
web-site of Bulgarian ministry of Justice and alerts when petition status is changed.

Bot is available in Telegram as @bulcit_bot or you can fork it and create your own if you like. 

The routine worker of @bulcit_bot app is deployed on Heroku.

