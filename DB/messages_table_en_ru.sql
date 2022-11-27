INSERT INTO public.messages (message_code, en, ru) VALUES ('done_no_pin', 'Current info provided by you is the following:
Your PIN: %s
Petition number is not provided. Please use /start menu.', 'Вот что мы имеем:
PIN: %s
Номер прошения не предоставлен. 
Используй меню /start для продолжения.');
INSERT INTO public.messages (message_code, en, ru) VALUES ('new_user_welcome_message', 'Hi! My name is Bulgarian Citizen bot — to be shorty — BulCit (nothing familiar to ''Bullshit''!). I help check and monitor statuses of your Bulgarian citizenship petition! 
Please provide credentials (petition number and PIN) given by Bulgarian Ministry of Justice. 
Push corresponding buttons below to provide info to me.', 'Привет! Меня зовут Bulgarian Citizen bot - сокращенно - BulCit (не путать с ''Bullshit''!). Я буду проверять и отслеживать статус твоего прошения о гражданстве Болгарии!
Пожалуйста, сообщи мне свои реквизиты (номер прошения и PIN), выданные Министерством юстиции Болгарии. Используй кнопки ниже.');
INSERT INTO public.messages (message_code, en, ru) VALUES ('done_no_pn', 'Current info provided by you is the following:
Your Petition number: %s
PIN is not provided. Please use /start menu.', 'Вот что мы имеем:
Номер прошения: %s
PIN не предоставлен.
Используй меню /start для продолжения.');
INSERT INTO public.messages (message_code, en, ru) VALUES ('existing_user_welcome_message', 'Hi again! Here I am! The BulCit bot! If you''d like to update your credentials (PIN or petition number) please use
buttons below.
If you''d like to see freshly updated status of your petition please push ''Done'' button.', 'Привет еще раз! BulCit-бот на связи! Если тебе понадобится обновить учетные данные (PIN или номер прошения),
пожалуйста, воспользуйся кнопками ниже.
Если ты хочешь увидеть свеженький, только что запрошенный статус прошения, пожалуйста, нажми кнопку «Done»');
INSERT INTO public.messages (message_code, en, ru) VALUES ('give_me_your_pin', 'Please send me your PIN, or type NO if you don''t like to change PIN already provided by you earlier.', 'Отправь мне PIN или напиши NO если не хочешь менять тот, который уже есть.');
INSERT INTO public.messages (message_code, en, ru) VALUES ('give_me_your_petition_number', 'Please send me your petition number, or type NO if you don''t like to change the number already provided by you earlier.', 'Отправь мне номер прошения или напиши NO если не хочешь менять тот, который уже есть.');
INSERT INTO public.messages (message_code, en, ru) VALUES ('all_set_message', 'Current info provided by you is the following:
Petition number: %s
PIN: %s
We are all set! Please push ''Done'' button.', 'Вот что я получил от тебя:
Номер прошения:  %s
PIN: %s
Все данные у меня есть! Так что, нажимай кнопку Done!');
INSERT INTO public.messages (message_code, en, ru) VALUES ('pin_provided_pn_not', 'PIN is provided. But petition number is not! Please push ''Petition number'' button!', 'PIN мне известен, а вот номер прошения пока нет! Используй кнопку ''Petition number'' ниже, чтоб сообщить мне эту информацию!');
INSERT INTO public.messages (message_code, en, ru) VALUES ('pn_provided_pin_not', 'Petition number is provided. But PIN is not! Please push ''PIN'' button!', 'Номер прошения мне известен, а вот PIN пока нет! Используй кнопку ''PIN'' ниже, чтоб сообщить мне эту информацию!');
INSERT INTO public.messages (message_code, en, ru) VALUES ('no_creds_provided', 'Credentials are not provided yet. Use buttons below to provide!', 'Данных пока нет. Используй кнопки ниже, чтоб отправить мне номер прошения и PIN!');
INSERT INTO public.messages (message_code, en, ru) VALUES ('done_full_message', 'Current info provided by you is the following:
Your petition number: %s
Your PIN: %s
Status of your petition is:
%s

%s days passed since last status change.

Monitoring is ON.
I''ll let you know when status is changed.', 'Вот что мы имеем:
Номер прошения: %s
PIN: %s
Статус обращения: 
%s

%s дней прошло с последнего изменения статуса.

Мониторинг включен. Когда статус поменяется, я сообщу!');
INSERT INTO public.messages (message_code, en, ru) VALUES ('done_no_creds', 'Currently neither PIN nor petition number are provided. Please use /start menu.', 'Вот что мы имеем:
Пока ни PIN, ни Номер прошения не предоставлены. 
Используй меню /start для продолжения.');
INSERT INTO public.messages (message_code, en, ru) VALUES ('status_changed_message', 'Hey there!!! Here is the new status of your petition:
%s', 'Наконец-то! Статус прошения изменился! Новый статус:
%s');
