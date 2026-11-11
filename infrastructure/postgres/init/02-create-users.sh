#!/bin/sh

# Створення користувачів PostgreSQL та налаштування прав доступу

set -eu

# Перевірка наявності паролів
: "${AUTH_DB_PASSWORD:?Missing AUTH_DB_PASSWORD}"
: "${STUDY_PLAN_DB_PASSWORD:?Missing STUDY_PLAN_DB_PASSWORD}"
: "${PROGRESS_DB_PASSWORD:?Missing PROGRESS_DB_PASSWORD}"

# Підключення до PostgreSQL
psql -v ON_ERROR_STOP=1 \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -v auth_password="$AUTH_DB_PASSWORD" \
    -v study_password="$STUDY_PLAN_DB_PASSWORD" \
    -v progress_password="$PROGRESS_DB_PASSWORD" <<'SQL'

-- Створення користувачів, якщо вони ще не існують

SELECT format('CREATE ROLE auth_user LOGIN PASSWORD %L', :'auth_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'auth_user')
\gexec

SELECT format('CREATE ROLE study_plan_user LOGIN PASSWORD %L', :'study_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'study_plan_user')
\gexec

SELECT format('CREATE ROLE progress_user LOGIN PASSWORD %L', :'progress_password')
WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'progress_user')
\gexec

-- Обмеження загального доступу до схем

REVOKE ALL ON SCHEMA auth FROM PUBLIC;
REVOKE ALL ON SCHEMA study_plan FROM PUBLIC;
REVOKE ALL ON SCHEMA progress FROM PUBLIC;

-- Надання прав відповідним користувачам

GRANT USAGE, CREATE ON SCHEMA auth TO auth_user;
GRANT USAGE, CREATE ON SCHEMA study_plan TO study_plan_user;
GRANT USAGE, CREATE ON SCHEMA progress TO progress_user;

SQL
