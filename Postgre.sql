-- Database: bookly_data

-- DROP DATABASE IF EXISTS bookly_data;

CREATE DATABASE bookly_data
    WITH
    OWNER = bookly_user
    ENCODING = 'UTF8'
    LC_COLLATE = 'C'
    LC_CTYPE = 'C'
    LOCALE_PROVIDER = 'libc'
    TABLESPACE = pg_default
    CONNECTION LIMIT = -1
    IS_TEMPLATE = False;
