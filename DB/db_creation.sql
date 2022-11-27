
create table statuses
(
    user_id     varchar(255),
    status      varchar(255),
    status_date timestamp,
    id          serial
        primary key
);

create table creds
(
    user_id     varchar(255),
    petition_no varchar(255),
    pin         varchar(255),
    language    varchar
);


create table logs
(
    id          serial,
    user_id     varchar,
    status_text varchar,
    timestamp   timestamp,
    message     varchar
);


create table messages
(
    message_code varchar not null,
    en           varchar,
    ru           varchar
);


