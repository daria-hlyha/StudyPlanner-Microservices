import hashlib
from pathlib import Path

from database import get_connection


# Директорія із SQL-міграціями
BASE_DIR = Path(__file__).resolve().parent
MIGRATIONS_DIR = BASE_DIR / "migrations"

# Ідентифікатор блокування міграцій Study Plan Service
MIGRATION_LOCK_ID = 31001


def calculate_checksum(sql):
    """Обчислення контрольної суми SQL-міграції."""

    return hashlib.sha256(
        sql.encode("utf-8")
    ).hexdigest()


def create_migrations_table(cursor):
    """Створення службової таблиці обліку міграцій."""

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS study_plan.schema_migrations (
            version VARCHAR(100) PRIMARY KEY,
            checksum VARCHAR(64) NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def get_applied_migrations(cursor):
    """Отримання вже застосованих міграцій."""

    cursor.execute(
        """
        SELECT version, checksum
        FROM study_plan.schema_migrations
        ORDER BY version
        """
    )

    return dict(cursor.fetchall())


def apply_migrations():
    """Перевірка та застосування SQL-міграцій."""

    migration_files = sorted(
        MIGRATIONS_DIR.glob("*.sql")
    )

    if not migration_files:
        raise RuntimeError("No SQL migration files found")

    # Підготовка SQL-файлів та контрольних сум
    migrations = []

    for migration_file in migration_files:
        version = migration_file.stem

        sql = migration_file.read_text(
            encoding="utf-8-sig"
        )

        if not sql.strip():
            raise RuntimeError(
                f"Empty migration: {version}"
            )

        checksum = calculate_checksum(sql)

        migrations.append(
            (version, sql, checksum)
        )

    applied_count = 0
    skipped_count = 0

    print("Connecting to PostgreSQL...")

    # Усі операції виконуються в одній транзакції
    with get_connection() as connection:
        with connection.cursor() as cursor:

            # Перевірка цільової бази даних та користувача
            cursor.execute(
                """
                SELECT
                    current_database(),
                    current_user,
                    current_schema()
                """
            )

            database, user, schema = cursor.fetchone()

            if (
                database != "studyplanner"
                or user != "study_plan_user"
                or schema != "study_plan"
            ):
                raise RuntimeError(
                    "Unexpected database connection settings"
                )

            print(f"Database: {database}")
            print(f"User: {user}")
            print(f"Schema: {schema}")

            # Захист від одночасного запуску міграцій
            cursor.execute(
                "SELECT pg_advisory_xact_lock(%s)",
                (MIGRATION_LOCK_ID,)
            )

            # Створення таблиці обліку міграцій
            create_migrations_table(cursor)

            # Отримання застосованих міграцій
            applied_migrations = get_applied_migrations(
                cursor
            )

            available_versions = {
                version
                for version, sql, checksum in migrations
            }

            # Перевірка відсутніх файлів застосованих міграцій
            missing_versions = (
                set(applied_migrations) - available_versions
            )

            if missing_versions:
                raise RuntimeError(
                    "Applied migration files are missing: "
                    + ", ".join(sorted(missing_versions))
                )

            # Застосування міграцій
            for version, sql, checksum in migrations:

                if version in applied_migrations:

                    if (
                        applied_migrations[version]
                        != checksum
                    ):
                        raise RuntimeError(
                            f"Migration has been modified: {version}"
                        )

                    print(f"Skipped: {version}")
                    skipped_count += 1

                    continue

                # Заборона додавання старішої міграції
                # після вже застосованої новішої версії
                if (
                    applied_migrations
                    and version < max(applied_migrations)
                ):
                    raise RuntimeError(
                        f"Migration is out of order: {version}"
                    )

                print(f"Applying: {version}")

                # Виконання SQL-міграції
                cursor.execute(sql)

                # Збереження інформації про міграцію
                cursor.execute(
                    """
                    INSERT INTO study_plan.schema_migrations (
                        version,
                        checksum
                    )
                    VALUES (%s, %s)
                    """,
                    (version, checksum)
                )

                applied_count += 1

    # Ці повідомлення виводяться після успішного commit
    print()
    print("Database migrations completed successfully")
    print(f"Applied migrations: {applied_count}")
    print(f"Skipped migrations: {skipped_count}")


if __name__ == "__main__":
    try:
        apply_migrations()

    except Exception as error:
        print("Database migration failed")
        print(f"Error: {error}")

        raise SystemExit(1)