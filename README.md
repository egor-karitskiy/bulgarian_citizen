# "Bulgarian Citizenship Bot" telegram bot

см. описание по-русски ниже. 

This simple bot is created for quite rare need -- monitoring and alerting of changing statuses during official process of granting Bulgarian citizenship. 
The process takes around two-three years and statuses of petition are being changed very seldom. That's why it's convenient to have a background routine which regulary queries web-site of Bulgarian Ministry of Justice, retrieves petition status and alerts user when petition status is changed.

Most probably you could adapt this bot main feature to any task of this kind - users notification if some statuses are being changed.

Bot is available in Telegram as @bulcit_bot. You can use that one or you may fork it and create your own if you like. 

The routine worker of @bulcit_bot app is deployed on Heroku.
Based on python-telegram-bot wrapper.


____________

Этот простенький Телеграм-бот был создан для удовлетворения довольно редкой потребности - мониторинга изменения статусов прошения о выдаче гражданства Болгарии. Так как бюрократический процесс с гражданством длится два-три года, то и статусы прошения меняются крайне редко. Поэтому было бы удобно иметь инструмент, который постоянно запрашивает статус на сайте Министерства Юстиции Болгарии и информирует, когда статус прошения меняется. 

Наверняка этого бота можно переделать для любой подобной задачи - нотификации пользователей, когда меняются какие-то статусы. 

Бот работает в Телеграме - @bulcit_bot. Можно пользоваться этим (если вдруг вам это вообще нужно) или форкнуть и доработать под свои нужды. 

Инфраструктура бота развернута в Heroku. 
Использован модуль python-telegram-bot
