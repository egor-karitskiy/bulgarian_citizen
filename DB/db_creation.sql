
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
    language    varchar,
    email       varchar(255)
);


create table logs
(
    timestamp   timestamp,
    message_source     varchar,
    log_message  varchar
);


create table messages
(
    message_code varchar not null,
    en           varchar,
    ru           varchar
);


