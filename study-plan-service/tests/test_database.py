from psycopg import sql
from psycopg import errors
from uuid import UUID, uuid4
from contextlib import closing

from database import get_connection


def count_subjects(cursor):
    """Отримання кількості дисциплін."""

    cursor.execute("""
        SELECT COUNT(*)
        FROM study_plan.subjects
    """)

    return cursor.fetchone()[0]


def subject_exists(cursor, subject_id):
    """Перевірка наявності дисципліни."""

    cursor.execute("""
        SELECT EXISTS (
            SELECT 1
            FROM study_plan.subjects
            WHERE id = %s
        )
    """, (subject_id,))

    return cursor.fetchone()[0]

def execute_expected_error(
    cursor,
    query,
    params,
    expected_error,
    expected_constraint=None,
    expected_column=None,
    expected_table=None
):
    """Перевірка очікуваної помилки PostgreSQL."""

    cursor.execute("SAVEPOINT negative_test")

    try:
        cursor.execute(query, params)

    except expected_error as error:
        result = True

        if expected_constraint is not None:
            result = (
                result
                and error.diag.constraint_name == expected_constraint
            )

        if expected_column is not None:
            result = (
                result
                and error.diag.column_name == expected_column
            )

        if expected_table is not None:
            result = (
                result
                and error.diag.table_name == expected_table
            )

        print("SQLSTATE:", error.sqlstate)
        print("Table:", error.diag.table_name)
        print("Column:", error.diag.column_name)
        print("Constraint:", error.diag.constraint_name)

        return result

    finally:
        cursor.execute(
            "ROLLBACK TO SAVEPOINT negative_test"
        )

        cursor.execute(
            "RELEASE SAVEPOINT negative_test"
        )

    return False

def create_test_records(cursor):
    """Створення взаємопов'язаних тестових записів."""

    user_id = uuid4()

    records = {
        "user_id": user_id
    }

    # 1. Дисципліна

    cursor.execute("""
        INSERT INTO study_plan.subjects (
            user_id, name, short_name,
            academic_year, semester, assessment_type
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        user_id,
        "Тестова дисципліна",
        "ТД",
        "2026/2027",
        7,
        "exam"
    ))

    records["subject_id"] = cursor.fetchone()[0]

    # 2. Навчальний план

    cursor.execute("""
        INSERT INTO study_plan.study_plans (
            user_id, plan_type, title,
            start_date, end_date
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (
        user_id,
        "academic",
        "Тестовий навчальний план",
        "2026-09-01",
        "2026-12-31"
    ))

    records["plan_id"] = cursor.fetchone()[0]

    # 3. Зв'язок плану з дисципліною

    cursor.execute("""
        INSERT INTO study_plan.study_plan_subjects (
            plan_id, subject_id
        )
        VALUES (%s, %s)
    """, (
        records["plan_id"],
        records["subject_id"]
    ))

    # 4. Конфігурація типу занять

    cursor.execute("""
        INSERT INTO study_plan.subject_class_types (
            subject_id, class_type, total_classes
        )
        VALUES (%s, %s, %s)
    """, (
        records["subject_id"],
        "practical",
        10
    ))

    records["class_type"] = "practical"

    # 5. Навчальний модуль

    cursor.execute("""
        INSERT INTO study_plan.study_modules (
            plan_id, subject_id, title, position
        )
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """, (
        records["plan_id"],
        records["subject_id"],
        "Тестовий навчальний модуль",
        1
    ))

    records["module_id"] = cursor.fetchone()[0]

    # 6. Навчальне завдання

    cursor.execute("""
        INSERT INTO study_plan.study_tasks (
            user_id, module_id,
            task_type, task_number, title
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (
        user_id,
        records["module_id"],
        "practical_work",
        3,
        "Тестова практична робота"
    ))

    records["task_id"] = cursor.fetchone()[0]

    # 7. Заняття за розкладом

    cursor.execute("""
        INSERT INTO study_plan.scheduled_classes (
            subject_id, class_type, class_number,
            education_format, start_at, end_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        records["subject_id"],
        records["class_type"],
        7,
        "online",
        "2026-12-03T09:30:00+02:00",
        "2026-12-03T11:05:00+02:00"
    ))

    records["class_id"] = cursor.fetchone()[0]

    # 8. Особиста навчальна сесія

    cursor.execute("""
        INSERT INTO study_plan.study_sessions (
            user_id, task_id, session_type,
            title, start_at, end_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        user_id,
        records["task_id"],
        "defense_preparation",
        "Тестова навчальна сесія",
        "2026-12-02T16:00:00+02:00",
        "2026-12-02T17:30:00+02:00"
    ))

    records["session_id"] = cursor.fetchone()[0]

    # 9. Важлива подія — дедлайн

    cursor.execute("""
        INSERT INTO study_plan.important_events (
            user_id, task_id,
            event_type, title, event_date
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (
        user_id,
        records["task_id"],
        "deadline",
        "Тестовий дедлайн",
        "2026-12-02"
    ))

    records["deadline_id"] = cursor.fetchone()[0]

    # 10. Важлива подія — захист

    cursor.execute("""
        INSERT INTO study_plan.important_events (
            user_id, task_id, class_id,
            event_type, title
        )
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (
        user_id,
        records["task_id"],
        records["class_id"],
        "defense",
        "Тестовий захист"
    ))

    records["defense_id"] = cursor.fetchone()[0]

    return records

def test_transactions():
    """Перевірка транзакційної ізоляції та відкату."""

    with closing(get_connection()) as conn1, \
         closing(get_connection()) as conn2:

        with conn1.cursor() as cur1, \
             conn2.cursor() as cur2:

            try:
                print("=== CONNECTION VALIDATION ===")

                cur1.execute("""
                    SELECT
                        current_database(),
                        current_user,
                        current_schema()
                """)

                settings1 = cur1.fetchone()

                cur2.execute("""
                    SELECT
                        current_database(),
                        current_user,
                        current_schema()
                """)

                settings2 = cur2.fetchone()

                expected_settings = (
                    "studyplanner",
                    "study_plan_user",
                    "study_plan"
                )

                connection_match = (
                    settings1 == settings2 == expected_settings
                )

                print("Connection 1:", settings1)
                print("Connection 2:", settings2)

                if not connection_match:
                    raise RuntimeError(
                        "Unexpected connection settings"
                    )

                print("Autocommit connection 1:", conn1.autocommit)
                print("Autocommit connection 2:", conn2.autocommit)

                if conn1.autocommit or conn2.autocommit:
                    raise RuntimeError(
                        "Autocommit must be disabled"
                    )

                cur1.execute("SHOW transaction_isolation")
                isolation1 = cur1.fetchone()[0]

                cur2.execute("SHOW transaction_isolation")
                isolation2 = cur2.fetchone()[0]

                print("Isolation level connection 1:", isolation1)
                print("Isolation level connection 2:", isolation2)

                print("\n=== INITIAL DATABASE STATE ===")

                initial_count = count_subjects(cur1)
                initial_count_external = count_subjects(cur2)

                print("Initial subjects count:", initial_count)
                print("Initial external count:", initial_count_external)

                print("\n=== INSERT TEST RECORD ===")

                test_user_id = uuid4()

                cur1.execute("""
                    INSERT INTO study_plan.subjects (
                        user_id,
                        name,
                        short_name,
                        description,
                        academic_year,
                        semester,
                        assessment_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at, updated_at
                """, (
                    test_user_id,
                    "Тестова дисципліна",
                    "ТД",
                    "Перевірка транзакцій",
                    "2026/2027",
                    7,
                    "exam"
                ))

                test_id, created_at, updated_at = cur1.fetchone()

                print("Test subject ID:", test_id)
                print("Test user ID:", test_user_id)
                print("Created at:", created_at.isoformat())
                print("Updated at:", updated_at.isoformat())

                print("\n=== TRANSACTION VISIBILITY ===")

                inside_count = count_subjects(cur1)

                visible_inside = subject_exists(
                    cur1, test_id
                )

                visible_outside = subject_exists(
                    cur2, test_id
                )

                outside_count = count_subjects(cur2)

                print("Count inside transaction:", inside_count)
                print("Record visible inside transaction:", visible_inside)
                print("Count outside transaction:", outside_count)
                print("Record visible outside transaction:", visible_outside)

                print("\n=== ROLLBACK ===")

                conn1.rollback()
                conn2.rollback()

                print("Rollback completed")

                print("\n=== STATE AFTER ROLLBACK ===")

                final_count = count_subjects(cur1)

                record_exists_after = subject_exists(
                    cur1, test_id
                )

                final_count_external = count_subjects(cur2)

                print("Final subjects count:", final_count)
                print("Final external count:", final_count_external)
                print("Test record exists after rollback:", record_exists_after)

                print("\n=== FINAL TRANSACTION VALIDATION ===")

                checks = {
                    "Connection settings":
                        connection_match,

                    "Autocommit disabled":
                        not conn1.autocommit and not conn2.autocommit,

                    "Read committed isolation":
                        isolation1 == isolation2 == "read committed",

                    "Initial counts match":
                        initial_count == initial_count_external,

                    "Test record created":
                        inside_count == initial_count + 1,

                    "UUID generated":
                        isinstance(test_id, UUID),

                    "Timestamps generated":
                        created_at is not None and updated_at is not None,

                    "Initial timestamps match":
                        created_at == updated_at,

                    "Record visible inside":
                        visible_inside,

                    "Uncommitted record isolated":
                        not visible_outside,

                    "External count unchanged":
                        outside_count == initial_count_external,

                    "Original count restored":
                        final_count == initial_count,

                    "External final count restored":
                        final_count_external == initial_count_external,

                    "Test record removed":
                        not record_exists_after
                }

                for name, result in checks.items():
                    status = "PASS" if result else "FAIL"
                    print(f"{name}: {status}")

                print("\nTotal checks:", len(checks))
                print("Passed checks:", sum(checks.values()))

                print(
                    "Failed checks:",
                    sum(not result for result in checks.values())
                )

                print(
                    "Full transaction validation:",
                    all(checks.values())
                )

                if not all(checks.values()):
                    raise AssertionError(
                        "Transaction validation failed"
                    )

            finally:
                conn1.rollback()
                conn2.rollback()

    print("Connections closed")
    print("=== TRANSACTION CHECK COMPLETED ===")

def test_valid_records():
    """Перевірка створення коректних навчальних записів."""

    tables = [
        "subjects",
        "study_plans",
        "study_plan_subjects",
        "subject_class_types",
        "study_modules",
        "study_tasks",
        "scheduled_classes",
        "study_sessions",
        "important_events"
    ]

    def count_records(cursor, table_name):
        query = sql.SQL(
            "SELECT COUNT(*) FROM {}.{}"
        ).format(
            sql.Identifier("study_plan"),
            sql.Identifier(table_name)
        )

        cursor.execute(query)

        return cursor.fetchone()[0]

    with closing(get_connection()) as conn:
        with conn.cursor() as cur:

            try:
                print("\n=== VALID RECORDS TEST ===")

                cur.execute("""
                    SELECT
                        current_database(),
                        current_user,
                        current_schema()
                """)

                settings = cur.fetchone()

                if settings != (
                    "studyplanner",
                    "study_plan_user",
                    "study_plan"
                ):
                    raise RuntimeError(
                        "Unexpected connection settings"
                    )

                if conn.autocommit:
                    raise RuntimeError(
                        "Autocommit must be disabled"
                    )

                print("\n=== INITIAL RECORD COUNTS ===")

                initial_counts = {}

                for table in tables:
                    initial_counts[table] = count_records(
                        cur, table
                    )

                    print(
                        f"{table}: {initial_counts[table]}"
                    )

                user_id = uuid4()

                print("\n=== CREATE TEST RECORDS ===")

                # 1. Створення дисципліни

                cur.execute("""
                    INSERT INTO study_plan.subjects (
                        user_id,
                        name,
                        short_name,
                        description,
                        academic_year,
                        semester,
                        assessment_type
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    "Мікросервісна архітектура та розподілені системи",
                    "МАтР",
                    "Тестова навчальна дисципліна",
                    "2026/2027",
                    7,
                    "exam"
                ))

                subject_id = cur.fetchone()[0]

                print("subjects: CREATED", subject_id)

                # 2. Створення навчального плану

                cur.execute("""
                    INSERT INTO study_plan.study_plans (
                        user_id,
                        plan_type,
                        title,
                        description,
                        start_date,
                        end_date
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    "academic",
                    "Навчальний план — 7 семестр",
                    "Тестовий навчальний план",
                    "2026-09-01",
                    "2026-12-31"
                ))

                plan_id = cur.fetchone()[0]

                print("study_plans: CREATED", plan_id)

                # 3. Додавання дисципліни до плану

                cur.execute("""
                    INSERT INTO study_plan.study_plan_subjects (
                        plan_id,
                        subject_id
                    )
                    VALUES (%s, %s)
                """, (
                    plan_id,
                    subject_id
                ))

                print("study_plan_subjects: CREATED")

                # 4. Налаштування типу занять

                cur.execute("""
                    INSERT INTO study_plan.subject_class_types (
                        subject_id,
                        class_type,
                        total_classes
                    )
                    VALUES (%s, %s, %s)
                """, (
                    subject_id,
                    "practical",
                    10
                ))

                print("subject_class_types: CREATED")

                # 5. Створення навчального модуля

                cur.execute("""
                    INSERT INTO study_plan.study_modules (
                        plan_id,
                        subject_id,
                        title,
                        description,
                        position
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    plan_id,
                    subject_id,
                    "Розробка мікросервісної системи",
                    "Тестовий навчальний модуль",
                    1
                ))

                module_id = cur.fetchone()[0]

                print("study_modules: CREATED", module_id)

                # 6. Створення навчального завдання

                cur.execute("""
                    INSERT INTO study_plan.study_tasks (
                        user_id,
                        module_id,
                        task_type,
                        task_number,
                        title,
                        description
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    module_id,
                    "practical_work",
                    3,
                    "Практична робота №3",
                    "Реалізація Study Plan Service"
                ))

                task_id = cur.fetchone()[0]

                print("study_tasks: CREATED", task_id)

                # 7. Створення заняття в розкладі

                cur.execute("""
                    INSERT INTO study_plan.scheduled_classes (
                        subject_id,
                        class_type,
                        class_number,
                        education_format,
                        start_at,
                        end_at,
                        description
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    subject_id,
                    "practical",
                    7,
                    "online",
                    "2026-12-03T09:30:00+02:00",
                    "2026-12-03T11:05:00+02:00",
                    "Тестове практичне заняття"
                ))

                class_id = cur.fetchone()[0]

                print("scheduled_classes: CREATED", class_id)

                # 8. Створення особистої навчальної сесії

                cur.execute("""
                    INSERT INTO study_plan.study_sessions (
                        user_id,
                        task_id,
                        session_type,
                        title,
                        description,
                        start_at,
                        end_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    task_id,
                    "defense_preparation",
                    "Підготовка до захисту",
                    "Підготовка до практичної роботи №3",
                    "2026-12-02T16:00:00+02:00",
                    "2026-12-02T17:30:00+02:00"
                ))

                session_id = cur.fetchone()[0]

                print("study_sessions: CREATED", session_id)

                # 9. Створення дедлайну

                cur.execute("""
                    INSERT INTO study_plan.important_events (
                        user_id,
                        task_id,
                        event_type,
                        title,
                        event_date
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    task_id,
                    "deadline",
                    "Дедлайн практичної роботи №3",
                    "2026-12-02"
                ))

                deadline_id = cur.fetchone()[0]

                print(
                    "important_events deadline: CREATED",
                    deadline_id
                )

                # 10. Створення події захисту

                cur.execute("""
                    INSERT INTO study_plan.important_events (
                        user_id,
                        task_id,
                        class_id,
                        event_type,
                        title
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    task_id,
                    class_id,
                    "defense",
                    "Захист практичної роботи №3"
                ))

                defense_id = cur.fetchone()[0]

                print(
                    "important_events defense: CREATED",
                    defense_id
                )

                # Примусова перевірка відкладених обмежень

                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

                print("Deferred constraints: VALID")

                print("\n=== RECORD COUNTS AFTER INSERT ===")

                expected_increases = {
                    table: 1 for table in tables
                }

                expected_increases["important_events"] = 2

                insert_checks = {}

                for table in tables:
                    actual_count = count_records(cur, table)

                    expected_count = (
                        initial_counts[table]
                        + expected_increases[table]
                    )

                    result = actual_count == expected_count

                    insert_checks[table] = result

                    print(
                        f"{table}: "
                        f"expected={expected_count}, "
                        f"actual={actual_count}, "
                        f"{'PASS' if result else 'FAIL'}"
                    )

                print("\n=== RELATIONSHIP VALIDATION ===")

                cur.execute("""
                    SELECT
                        s.id,
                        p.id,
                        m.id,
                        t.id,
                        c.id,
                        ss.id,
                        d.id,
                        e.id
                    FROM study_plan.subjects s
                    JOIN study_plan.study_plan_subjects ps
                        ON ps.subject_id = s.id
                    JOIN study_plan.study_plans p
                        ON p.id = ps.plan_id
                    JOIN study_plan.study_modules m
                        ON m.plan_id = p.id
                        AND m.subject_id = s.id
                    JOIN study_plan.study_tasks t
                        ON t.module_id = m.id
                    JOIN study_plan.subject_class_types ct
                        ON ct.subject_id = s.id
                    JOIN study_plan.scheduled_classes c
                        ON c.subject_id = ct.subject_id
                        AND c.class_type = ct.class_type
                    JOIN study_plan.study_sessions ss
                        ON ss.task_id = t.id
                    JOIN study_plan.important_events d
                        ON d.task_id = t.id
                        AND d.event_type = 'deadline'
                    JOIN study_plan.important_events e
                        ON e.task_id = t.id
                        AND e.class_id = c.id
                        AND e.event_type = 'defense'
                    WHERE t.id = %s
                    AND s.user_id = %s
                    AND p.user_id = %s
                    AND t.user_id = %s
                    AND ss.user_id = %s
                    AND d.user_id = %s
                    AND e.user_id = %s
                """, (
                    task_id,
                    user_id,
                    user_id,
                    user_id,
                    user_id,
                    user_id,
                    user_id
                ))

                relationship_rows = cur.fetchall()

                expected_relationship = (
                    subject_id,
                    plan_id,
                    module_id,
                    task_id,
                    class_id,
                    session_id,
                    deadline_id,
                    defense_id
                )

                relationship_match = (
                    relationship_rows
                    == [expected_relationship]
                )

                print(
                    "All nine tables connected:",
                    relationship_match
                )

                print("\n=== ROLLBACK ===")

                conn.rollback()

                print("Rollback completed")

                print("\n=== RECORD COUNTS AFTER ROLLBACK ===")

                rollback_checks = {}

                for table in tables:
                    actual_count = count_records(cur, table)

                    result = (
                        actual_count == initial_counts[table]
                    )

                    rollback_checks[table] = result

                    print(
                        f"{table}: "
                        f"initial={initial_counts[table]}, "
                        f"final={actual_count}, "
                        f"{'PASS' if result else 'FAIL'}"
                    )

                print("\n=== FINAL VALID RECORDS VALIDATION ===")

                checks = {}

                for table in tables:
                    checks[f"INSERT {table}"] = insert_checks[table]

                    checks[f"ROLLBACK {table}"] = rollback_checks[table]

                checks["Relationships"] = relationship_match

                for name, result in checks.items():
                    print(
                        f"{name}: "
                        f"{'PASS' if result else 'FAIL'}"
                    )

                print("\nTotal checks:", len(checks))

                print("Passed checks:", sum(checks.values()))

                print(
                    "Failed checks:",
                    sum(not result for result in checks.values())
                )

                print(
                    "Full valid records validation:",
                    all(checks.values())
                )

                if not all(checks.values()):
                    raise AssertionError(
                        "Valid records validation failed"
                    )

            finally:
                conn.rollback()

    print("Connection closed")
    print("=== VALID RECORDS CHECK COMPLETED ===")

def test_not_null_and_primary_keys():
    """Перевірка обмежень NOT NULL та PRIMARY KEY."""

    # Очікувані обов'язкові атрибути

    required_columns = {
        "subjects": [
            "id",
            "user_id",
            "name",
            "created_at",
            "updated_at"
        ],

        "study_plans": [
            "id",
            "user_id",
            "plan_type",
            "title",
            "created_at",
            "updated_at"
        ],

        "study_plan_subjects": [
            "plan_id",
            "subject_id"
        ],

        "subject_class_types": [
            "subject_id",
            "class_type"
        ],

        "study_modules": [
            "id",
            "plan_id",
            "title",
            "position",
            "created_at",
            "updated_at"
        ],

        "study_tasks": [
            "id",
            "user_id",
            "task_type",
            "title",
            "created_at",
            "updated_at"
        ],

        "scheduled_classes": [
            "id",
            "subject_id",
            "class_type",
            "start_at",
            "end_at",
            "created_at",
            "updated_at"
        ],

        "study_sessions": [
            "id",
            "user_id",
            "session_type",
            "title",
            "start_at",
            "end_at",
            "created_at",
            "updated_at"
        ],

        "important_events": [
            "id",
            "user_id",
            "event_type",
            "title",
            "created_at",
            "updated_at"
        ]
    }

    # Очікувані первинні ключі

    primary_keys = {
        "subjects": ["id"],
        "study_plans": ["id"],
        "study_plan_subjects": ["plan_id", "subject_id"],
        "subject_class_types": ["subject_id", "class_type"],
        "study_modules": ["id"],
        "study_tasks": ["id"],
        "scheduled_classes": ["id"],
        "study_sessions": ["id"],
        "important_events": ["id"]
    }

    not_null_checks = {}
    primary_key_checks = {}

    def get_record_counts(cursor):
        """Підрахунок записів у предметних таблицях."""

        counts = {}

        for table_name in required_columns:
            query = sql.SQL(
                "SELECT COUNT(*) FROM {}.{}"
            ).format(
                sql.Identifier("study_plan"),
                sql.Identifier(table_name)
            )

            cursor.execute(query)

            counts[table_name] = cursor.fetchone()[0]

        return counts

    with closing(get_connection()) as conn:
        with conn.cursor() as cur:

            try:
                print("\n=== NOT NULL AND PRIMARY KEY TEST ===")

                # Перевірка підключення

                cur.execute("""
                    SELECT
                        current_database(),
                        current_user,
                        current_schema()
                """)

                settings = cur.fetchone()

                if settings != (
                    "studyplanner",
                    "study_plan_user",
                    "study_plan"
                ):
                    raise RuntimeError(
                        "Unexpected connection settings"
                    )

                if conn.autocommit:
                    raise RuntimeError(
                        "Autocommit must be disabled"
                    )

                print("Connection settings: VALID")

                initial_counts = get_record_counts(cur)

                # Перевірка переліку NOT NULL

                print("\n=== NOT NULL METADATA VALIDATION ===")

                cur.execute("""
                    SELECT table_name, column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'study_plan'
                        AND table_name != 'schema_migrations'
                        AND is_nullable = 'NO'
                """)

                actual_required = set(cur.fetchall())

                expected_required = {
                    (table_name, column_name)
                    for table_name, columns
                    in required_columns.items()
                    for column_name in columns
                }

                required_match = (
                    actual_required == expected_required
                )

                print(
                    "Expected NOT NULL columns:",
                    len(expected_required)
                )

                print(
                    "Actual NOT NULL columns:",
                    len(actual_required)
                )

                print(
                    "NOT NULL metadata match:",
                    required_match
                )

                if not required_match:
                    print(
                        "Missing columns:",
                        expected_required - actual_required
                    )

                    print(
                        "Unexpected columns:",
                        actual_required - expected_required
                    )

                    raise AssertionError(
                        "NOT NULL metadata mismatch"
                    )

                # Перевірка первинних ключів

                print("\n=== PRIMARY KEY METADATA VALIDATION ===")

                cur.execute("""
                    SELECT
                        t.relname,
                        c.conname,
                        array_agg(
                            a.attname::text
                            ORDER BY k.ordinality
                        )
                    FROM pg_constraint c
                    JOIN pg_class t
                        ON t.oid = c.conrelid
                    JOIN pg_namespace n
                        ON n.oid = t.relnamespace
                    CROSS JOIN LATERAL
                        unnest(c.conkey)
                        WITH ORDINALITY AS k(attnum, ordinality)
                    JOIN pg_attribute a
                        ON a.attrelid = t.oid
                        AND a.attnum = k.attnum
                    WHERE n.nspname = 'study_plan'
                        AND c.contype = 'p'
                        AND t.relname != 'schema_migrations'
                    GROUP BY t.relname, c.conname
                """)

                actual_primary_keys = {
                    table_name: (constraint_name, columns)
                    for table_name, constraint_name, columns
                    in cur.fetchall()
                }

                expected_primary_keys = {
                    table_name: (
                        f"{table_name}_pkey",
                        columns
                    )
                    for table_name, columns
                    in primary_keys.items()
                }

                primary_keys_match = (
                    actual_primary_keys
                    == expected_primary_keys
                )

                print(
                    "Expected primary keys:",
                    len(expected_primary_keys)
                )

                print(
                    "Actual primary keys:",
                    len(actual_primary_keys)
                )

                print(
                    "Primary key metadata match:",
                    primary_keys_match
                )

                if not primary_keys_match:
                    raise AssertionError(
                        "Primary key metadata mismatch"
                    )

                # Створення коректних тестових даних

                print("\n=== CREATE TEST RECORDS ===")

                records = create_test_records(cur)

                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

                print("Test records created")
                print("Initial test constraints: VALID")

                # Відновлення відкладеної перевірки UNIQUE

                cur.execute("SET CONSTRAINTS ALL DEFERRED")

                # Первинні ключі тестових записів

                record_keys = {
                    "subjects": (
                        records["subject_id"],
                    ),

                    "study_plans": (
                        records["plan_id"],
                    ),

                    "study_plan_subjects": (
                        records["plan_id"],
                        records["subject_id"]
                    ),

                    "subject_class_types": (
                        records["subject_id"],
                        records["class_type"]
                    ),

                    "study_modules": (
                        records["module_id"],
                    ),

                    "study_tasks": (
                        records["task_id"],
                    ),

                    "scheduled_classes": (
                        records["class_id"],
                    ),

                    "study_sessions": (
                        records["session_id"],
                    ),

                    "important_events": (
                        records["deadline_id"],
                    )
                }

                # Перевірка NOT NULL

                print("\n=== NOT NULL NEGATIVE TESTS ===")

                for table_name, columns in required_columns.items():

                    key_columns = primary_keys[table_name]
                    key_values = record_keys[table_name]

                    where_clause = sql.SQL(" AND ").join(
                        sql.SQL("{} = %s").format(
                            sql.Identifier(column)
                        )
                        for column in key_columns
                    )

                    for column_name in columns:

                        print(
                            f"\nTesting NOT NULL: "
                            f"{table_name}.{column_name}"
                        )

                        query = sql.SQL("""
                            UPDATE {}.{}
                            SET {} = NULL
                            WHERE {}
                        """).format(
                            sql.Identifier("study_plan"),
                            sql.Identifier(table_name),
                            sql.Identifier(column_name),
                            where_clause
                        )

                        result = execute_expected_error(
                            cursor=cur,
                            query=query,
                            params=key_values,
                            expected_error=errors.NotNullViolation,
                            expected_column=column_name,
                            expected_table=table_name
                        )

                        test_name = (
                            f"{table_name}.{column_name}"
                        )

                        not_null_checks[test_name] = result

                        print(
                            "Result:",
                            "PASS" if result else "FAIL"
                        )

                # Перевірка PRIMARY KEY

                print("\n=== PRIMARY KEY NEGATIVE TESTS ===")

                for table_name, key_columns in primary_keys.items():

                    print(
                        f"\nTesting PRIMARY KEY: {table_name}"
                    )

                    key_values = record_keys[table_name]

                    where_clause = sql.SQL(" AND ").join(
                        sql.SQL("{} = %s").format(
                            sql.Identifier(column)
                        )
                        for column in key_columns
                    )

                    query = sql.SQL("""
                        INSERT INTO {}.{}
                        SELECT *
                        FROM {}.{}
                        WHERE {}
                    """).format(
                        sql.Identifier("study_plan"),
                        sql.Identifier(table_name),
                        sql.Identifier("study_plan"),
                        sql.Identifier(table_name),
                        where_clause
                    )

                    result = execute_expected_error(
                        cursor=cur,
                        query=query,
                        params=key_values,
                        expected_error=errors.UniqueViolation,
                        expected_constraint=f"{table_name}_pkey",
                        expected_table=table_name
                    )

                    primary_key_checks[table_name] = result

                    print(
                        "Result:",
                        "PASS" if result else "FAIL"
                    )

                # Перевірка стану після негативних тестів

                print("\n=== TEST RECORD INTEGRITY ===")

                cur.execute(
                    "SET CONSTRAINTS ALL IMMEDIATE"
                )

                expected_test_counts = {
                    table_name: count + (
                        2 if table_name == "important_events"
                        else 1
                    )
                    for table_name, count
                    in initial_counts.items()
                }

                current_counts = get_record_counts(cur)

                test_records_match = (
                    current_counts == expected_test_counts
                )

                print(
                    "Test record counts unchanged:",
                    test_records_match
                )

                print("Remaining constraints: VALID")

                # Повний відкат тестових змін

                print("\n=== ROLLBACK ===")

                conn.rollback()

                final_counts = get_record_counts(cur)

                rollback_match = (
                    final_counts == initial_counts
                )

                print("Rollback completed")

                for table_name in required_columns:
                    print(
                        f"{table_name}: "
                        f"initial={initial_counts[table_name]}, "
                        f"final={final_counts[table_name]}"
                    )

                print(
                    "Initial database state restored:",
                    rollback_match
                )

                # Підсумки тестування

                print("\n=== NOT NULL SUMMARY ===")

                print(
                    "Total NOT NULL checks:",
                    len(not_null_checks)
                )

                print(
                    "Passed NOT NULL checks:",
                    sum(not_null_checks.values())
                )

                print(
                    "Failed NOT NULL checks:",
                    sum(
                        not result
                        for result in not_null_checks.values()
                    )
                )

                print("\n=== PRIMARY KEY SUMMARY ===")

                print(
                    "Total PRIMARY KEY checks:",
                    len(primary_key_checks)
                )

                print(
                    "Passed PRIMARY KEY checks:",
                    sum(primary_key_checks.values())
                )

                print(
                    "Failed PRIMARY KEY checks:",
                    sum(
                        not result
                        for result in primary_key_checks.values()
                    )
                )

                checks = {
                    **{
                        f"NOT NULL {name}": result
                        for name, result
                        in not_null_checks.items()
                    },

                    **{
                        f"PRIMARY KEY {name}": result
                        for name, result
                        in primary_key_checks.items()
                    }
                }

                full_match = (
                    required_match
                    and primary_keys_match
                    and len(not_null_checks) == 48
                    and len(primary_key_checks) == 9
                    and all(checks.values())
                    and test_records_match
                    and rollback_match
                )

                print("\n=== FINAL CONSTRAINT VALIDATION ===")

                print("Total checks:", len(checks))

                print(
                    "Passed checks:",
                    sum(checks.values())
                )

                print(
                    "Failed checks:",
                    sum(
                        not result
                        for result in checks.values()
                    )
                )

                print(
                    "Failed scenarios:",
                    [
                        name for name, result
                        in checks.items()
                        if not result
                    ]
                )

                print(
                    "Full NOT NULL and PRIMARY KEY validation:",
                    full_match
                )

                if not full_match:
                    raise AssertionError(
                        "Constraint validation failed"
                    )

            finally:
                conn.rollback()

    print("Connection closed")
    print("=== CONSTRAINT CHECK COMPLETED ===")

def test_check_constraints():
    """Практична перевірка CHECK-обмежень."""

    tables = [
        "subjects",
        "study_plans",
        "study_plan_subjects",
        "subject_class_types",
        "study_modules",
        "study_tasks",
        "scheduled_classes",
        "study_sessions",
        "important_events"
    ]

    def get_record_counts(cursor):
        counts = {}

        for table_name in tables:
            query = sql.SQL(
                "SELECT COUNT(*) FROM {}.{}"
            ).format(
                sql.Identifier("study_plan"),
                sql.Identifier(table_name)
            )

            cursor.execute(query)

            counts[table_name] = cursor.fetchone()[0]

        return counts

    with closing(get_connection()) as conn:
        with conn.cursor() as cur:

            try:
                print("\n=== CHECK CONSTRAINTS TEST ===")

                # Перевірка підключення

                cur.execute("""
                    SELECT
                        current_database(),
                        current_user,
                        current_schema()
                """)

                settings = cur.fetchone()

                if settings != (
                    "studyplanner",
                    "study_plan_user",
                    "study_plan"
                ):
                    raise RuntimeError(
                        "Unexpected connection settings"
                    )

                if conn.autocommit:
                    raise RuntimeError(
                        "Autocommit must be disabled"
                    )

                print("Connection settings: VALID")

                initial_counts = get_record_counts(cur)

                # Створення коректних тестових даних

                print("\n=== CREATE TEST RECORDS ===")

                records = create_test_records(cur)

                cur.execute(
                    "SET CONSTRAINTS ALL IMMEDIATE"
                )

                print("Test records created")
                print("Initial test constraints: VALID")

                # Отримання ідентифікаторів

                subject_id = records["subject_id"]
                plan_id = records["plan_id"]
                module_id = records["module_id"]
                task_id = records["task_id"]
                class_id = records["class_id"]
                session_id = records["session_id"]
                deadline_id = records["deadline_id"]
                defense_id = records["defense_id"]

                # Негативні тестові сценарії:
                # таблиця, обмеження, SQL-запит, параметри

                test_cases = [

                    # 1. SUBJECTS — 5 обмежень

                    (
                        "subjects",
                        "chk_subjects_name",
                        """
                        UPDATE study_plan.subjects
                        SET name = %s
                        WHERE id = %s
                        """,
                        ("   ", subject_id)
                    ),

                    (
                        "subjects",
                        "chk_subjects_short_name",
                        """
                        UPDATE study_plan.subjects
                        SET short_name = %s
                        WHERE id = %s
                        """,
                        ("   ", subject_id)
                    ),

                    (
                        "subjects",
                        "chk_subjects_academic_year",
                        """
                        UPDATE study_plan.subjects
                        SET academic_year = %s
                        WHERE id = %s
                        """,
                        ("2026/2028", subject_id)
                    ),

                    (
                        "subjects",
                        "chk_subjects_semester",
                        """
                        UPDATE study_plan.subjects
                        SET semester = %s
                        WHERE id = %s
                        """,
                        (0, subject_id)
                    ),

                    (
                        "subjects",
                        "chk_subjects_assessment_type",
                        """
                        UPDATE study_plan.subjects
                        SET assessment_type = %s
                        WHERE id = %s
                        """,
                        ("invalid_type", subject_id)
                    ),

                    # 2. STUDY_PLANS — 3 обмеження

                    (
                        "study_plans",
                        "chk_plans_title",
                        """
                        UPDATE study_plan.study_plans
                        SET title = %s
                        WHERE id = %s
                        """,
                        ("", plan_id)
                    ),

                    (
                        "study_plans",
                        "chk_plans_type",
                        """
                        UPDATE study_plan.study_plans
                        SET plan_type = %s
                        WHERE id = %s
                        """,
                        ("invalid_type", plan_id)
                    ),

                    (
                        "study_plans",
                        "chk_plans_dates",
                        """
                        UPDATE study_plan.study_plans
                        SET end_date = start_date - 1
                        WHERE id = %s
                        """,
                        (plan_id,)
                    ),

                    # 3. SUBJECT_CLASS_TYPES — 2 обмеження

                    (
                        "subject_class_types",
                        "chk_subject_class_types_type",
                        """
                        UPDATE study_plan.subject_class_types
                        SET class_type = %s
                        WHERE subject_id = %s
                            AND class_type = %s
                        """,
                        (
                            "invalid_type",
                            subject_id,
                            records["class_type"]
                        )
                    ),

                    (
                        "subject_class_types",
                        "chk_subject_class_types_total",
                        """
                        UPDATE study_plan.subject_class_types
                        SET total_classes = %s
                        WHERE subject_id = %s
                            AND class_type = %s
                        """,
                        (
                            0,
                            subject_id,
                            records["class_type"]
                        )
                    ),

                    # 4. STUDY_MODULES — 2 обмеження

                    (
                        "study_modules",
                        "chk_modules_title",
                        """
                        UPDATE study_plan.study_modules
                        SET title = %s
                        WHERE id = %s
                        """,
                        ("", module_id)
                    ),

                    (
                        "study_modules",
                        "chk_modules_position",
                        """
                        UPDATE study_plan.study_modules
                        SET position = %s
                        WHERE id = %s
                        """,
                        (0, module_id)
                    ),

                    # 5. STUDY_TASKS — 4 обмеження

                    (
                        "study_tasks",
                        "chk_tasks_title",
                        """
                        UPDATE study_plan.study_tasks
                        SET title = %s
                        WHERE id = %s
                        """,
                        ("", task_id)
                    ),

                    (
                        "study_tasks",
                        "chk_tasks_type",
                        """
                        UPDATE study_plan.study_tasks
                        SET task_type = %s
                        WHERE id = %s
                        """,
                        ("invalid_type", task_id)
                    ),

                    (
                        "study_tasks",
                        "chk_tasks_number",
                        """
                        UPDATE study_plan.study_tasks
                        SET task_number = %s
                        WHERE id = %s
                        """,
                        (0, task_id)
                    ),

                    (
                        "study_tasks",
                        "chk_tasks_module_plan",
                        """
                        UPDATE study_plan.study_tasks
                        SET plan_id = %s
                        WHERE id = %s
                        """,
                        (plan_id, task_id)
                    ),

                    # 6. SCHEDULED_CLASSES — 4 обмеження

                    (
                        "scheduled_classes",
                        "chk_classes_type",
                        """
                        UPDATE study_plan.scheduled_classes
                        SET class_type = %s
                        WHERE id = %s
                        """,
                        ("invalid_type", class_id)
                    ),

                    (
                        "scheduled_classes",
                        "chk_classes_education_format",
                        """
                        UPDATE study_plan.scheduled_classes
                        SET education_format = %s
                        WHERE id = %s
                        """,
                        ("invalid_format", class_id)
                    ),

                    (
                        "scheduled_classes",
                        "chk_classes_number",
                        """
                        UPDATE study_plan.scheduled_classes
                        SET class_number = %s
                        WHERE id = %s
                        """,
                        (0, class_id)
                    ),

                    (
                        "scheduled_classes",
                        "chk_classes_time",
                        """
                        UPDATE study_plan.scheduled_classes
                        SET end_at = start_at - INTERVAL '1 minute'
                        WHERE id = %s
                        """,
                        (class_id,)
                    ),

                    # 7. STUDY_SESSIONS — 4 обмеження

                    (
                        "study_sessions",
                        "chk_sessions_title",
                        """
                        UPDATE study_plan.study_sessions
                        SET title = %s
                        WHERE id = %s
                        """,
                        ("", session_id)
                    ),

                    (
                        "study_sessions",
                        "chk_sessions_type",
                        """
                        UPDATE study_plan.study_sessions
                        SET session_type = %s
                        WHERE id = %s
                        """,
                        ("invalid_type", session_id)
                    ),

                    (
                        "study_sessions",
                        "chk_sessions_time",
                        """
                        UPDATE study_plan.study_sessions
                        SET end_at = start_at - INTERVAL '1 minute'
                        WHERE id = %s
                        """,
                        (session_id,)
                    ),

                    (
                        "study_sessions",
                        "chk_sessions_task_context",
                        """
                        UPDATE study_plan.study_sessions
                        SET plan_id = %s
                        WHERE id = %s
                        """,
                        (plan_id, session_id)
                    ),

                    # 8. IMPORTANT_EVENTS — 6 обмежень

                    (
                        "important_events",
                        "chk_events_title",
                        """
                        UPDATE study_plan.important_events
                        SET title = %s
                        WHERE id = %s
                        """,
                        ("", deadline_id)
                    ),

                    (
                        "important_events",
                        "chk_events_type",
                        """
                        UPDATE study_plan.important_events
                        SET event_type = %s
                        WHERE id = %s
                        """,
                        ("invalid_type", deadline_id)
                    ),

                    (
                        "important_events",
                        "chk_events_time_source",
                        """
                        UPDATE study_plan.important_events
                        SET event_date = NULL
                        WHERE id = %s
                        """,
                        (deadline_id,)
                    ),

                    (
                        "important_events",
                        "chk_events_deadline",
                        """
                        UPDATE study_plan.important_events
                        SET
                            event_date = NULL,
                            start_at = %s,
                            end_at = %s
                        WHERE id = %s
                        """,
                        (
                            "2026-12-02T16:00:00+02:00",
                            "2026-12-02T17:00:00+02:00",
                            deadline_id
                        )
                    ),

                    (
                        "important_events",
                        "chk_events_class_subject",
                        """
                        UPDATE study_plan.important_events
                        SET subject_id = %s
                        WHERE id = %s
                        """,
                        (subject_id, defense_id)
                    ),

                    (
                        "important_events",
                        "chk_events_task_plan",
                        """
                        UPDATE study_plan.important_events
                        SET plan_id = %s
                        WHERE id = %s
                        """,
                        (plan_id, deadline_id)
                    )
                ]

                # Перевірка метаданих CHECK-обмежень

                print("\n=== CHECK METADATA VALIDATION ===")

                cur.execute("""
                    SELECT
                        t.relname,
                        c.conname,
                        c.convalidated
                    FROM pg_constraint c
                    JOIN pg_class t
                        ON t.oid = c.conrelid
                    JOIN pg_namespace n
                        ON n.oid = t.relnamespace
                    WHERE n.nspname = 'study_plan'
                        AND c.contype = 'c'
                """)

                actual_constraints = {
                    (table_name, constraint_name, validated)
                    for table_name, constraint_name, validated
                    in cur.fetchall()
                }

                expected_constraints = {
                    (table_name, constraint_name, True)
                    for table_name, constraint_name, query, params
                    in test_cases
                }

                metadata_match = (
                    actual_constraints == expected_constraints
                    and len(test_cases) == 30
                    and len(expected_constraints) == 30
                )

                print(
                    "Expected CHECK constraints:",
                    len(expected_constraints)
                )

                print(
                    "Actual CHECK constraints:",
                    len(actual_constraints)
                )

                print(
                    "CHECK metadata match:",
                    metadata_match
                )

                if not metadata_match:
                    print(
                        "Missing constraints:",
                        expected_constraints - actual_constraints
                    )

                    print(
                        "Unexpected constraints:",
                        actual_constraints - expected_constraints
                    )

                    raise AssertionError(
                        "CHECK metadata mismatch"
                    )

                # Виконання негативних тестів

                print("\n=== CHECK NEGATIVE TESTS ===")

                checks = {}

                for table_name, constraint_name, query, params in test_cases:

                    print(
                        f"\nTesting CHECK: {constraint_name}"
                    )

                    result = execute_expected_error(
                        cursor=cur,
                        query=query,
                        params=params,
                        expected_error=errors.CheckViolation,
                        expected_constraint=constraint_name,
                        expected_table=table_name
                    )

                    checks[constraint_name] = result

                    print(
                        "Result:",
                        "PASS" if result else "FAIL"
                    )

                # Перевірка збереження тестових записів

                print("\n=== TEST RECORD INTEGRITY ===")

                cur.execute(
                    "SET CONSTRAINTS ALL IMMEDIATE"
                )

                expected_test_counts = {
                    table_name: count + (
                        2 if table_name == "important_events"
                        else 1
                    )
                    for table_name, count
                    in initial_counts.items()
                }

                current_counts = get_record_counts(cur)

                test_records_match = (
                    current_counts == expected_test_counts
                )

                print(
                    "Test record counts unchanged:",
                    test_records_match
                )

                print("Remaining constraints: VALID")

                # Повний відкат тестових змін

                print("\n=== ROLLBACK ===")

                conn.rollback()

                final_counts = get_record_counts(cur)

                rollback_match = (
                    final_counts == initial_counts
                )

                print("Rollback completed")

                for table_name in tables:

                    print(
                        f"{table_name}: "
                        f"initial={initial_counts[table_name]}, "
                        f"final={final_counts[table_name]}"
                    )

                print(
                    "Initial database state restored:",
                    rollback_match
                )

                # Підсумки тестування

                print("\n=== FINAL CHECK VALIDATION ===")

                full_match = (
                    metadata_match
                    and len(checks) == 30
                    and all(checks.values())
                    and test_records_match
                    and rollback_match
                )

                print("Total checks:", len(checks))

                print(
                    "Passed checks:",
                    sum(checks.values())
                )

                print(
                    "Failed checks:",
                    sum(
                        not result
                        for result in checks.values()
                    )
                )

                print(
                    "Failed constraints:",
                    [
                        name for name, result
                        in checks.items()
                        if not result
                    ]
                )

                print(
                    "Full CHECK constraints validation:",
                    full_match
                )

                if not full_match:
                    raise AssertionError(
                        "CHECK constraints validation failed"
                    )

            finally:
                conn.rollback()

    print("Connection closed")
    print("=== CHECK CONSTRAINTS TEST COMPLETED ===")

def test_foreign_keys():
    """Практична перевірка зовнішніх ключів."""

    tables = [
        "subjects",
        "study_plans",
        "study_plan_subjects",
        "subject_class_types",
        "study_modules",
        "study_tasks",
        "scheduled_classes",
        "study_sessions",
        "important_events"
    ]

    def get_record_counts(cursor):
        counts = {}

        for table_name in tables:
            query = sql.SQL(
                "SELECT COUNT(*) FROM {}.{}"
            ).format(
                sql.Identifier("study_plan"),
                sql.Identifier(table_name)
            )

            cursor.execute(query)
            counts[table_name] = cursor.fetchone()[0]

        return counts

    with closing(get_connection()) as conn:
        with conn.cursor() as cur:

            try:
                print("\n=== FOREIGN KEY TEST ===")

                # Перевірка підключення

                cur.execute("""
                    SELECT
                        current_database(),
                        current_user,
                        current_schema()
                """)

                settings = cur.fetchone()

                if settings != (
                    "studyplanner",
                    "study_plan_user",
                    "study_plan"
                ):
                    raise RuntimeError(
                        "Unexpected connection settings"
                    )

                if conn.autocommit:
                    raise RuntimeError(
                        "Autocommit must be disabled"
                    )

                print("Connection settings: VALID")

                initial_counts = get_record_counts(cur)

                # Створення основних тестових записів

                print("\n=== CREATE TEST RECORDS ===")

                records = create_test_records(cur)

                user_id = records["user_id"]
                subject_id = records["subject_id"]
                plan_id = records["plan_id"]
                module_id = records["module_id"]
                task_id = records["task_id"]
                class_id = records["class_id"]
                session_id = records["session_id"]
                deadline_id = records["deadline_id"]
                defense_id = records["defense_id"]

                # UUID неіснуючого запису

                missing_id = uuid4()

                # Додаткова дисципліна, яка не входить до плану

                cur.execute("""
                    INSERT INTO study_plan.subjects (
                        user_id,
                        name
                    )
                    VALUES (%s, %s)
                    RETURNING id
                """, (
                    user_id,
                    "Додаткова тестова дисципліна"
                ))

                extra_subject_id = cur.fetchone()[0]

                cur.execute(
                    "SET CONSTRAINTS ALL IMMEDIATE"
                )

                print("Main test records created")
                print("Extra subject created:", extra_subject_id)
                print("Missing record ID:", missing_id)
                print("Initial test constraints: VALID")

                test_counts = get_record_counts(cur)

                # Негативні тестові сценарії:
                # таблиця, обмеження, запит, параметри

                test_cases = [

                    # 1. STUDY_PLAN_SUBJECTS

                    (
                        "study_plan_subjects",
                        "fk_plan_subjects_plan",
                        """
                        INSERT INTO study_plan.study_plan_subjects (
                            plan_id, subject_id
                        )
                        VALUES (%s, %s)
                        """,
                        (missing_id, subject_id)
                    ),

                    (
                        "study_plan_subjects",
                        "fk_plan_subjects_subject",
                        """
                        INSERT INTO study_plan.study_plan_subjects (
                            plan_id, subject_id
                        )
                        VALUES (%s, %s)
                        """,
                        (plan_id, missing_id)
                    ),

                    # 2. SUBJECT_CLASS_TYPES

                    (
                        "subject_class_types",
                        "fk_subject_class_types_subject",
                        """
                        INSERT INTO study_plan.subject_class_types (
                            subject_id, class_type
                        )
                        VALUES (%s, %s)
                        """,
                        (missing_id, "practical")
                    ),

                    # 3. STUDY_MODULES

                    (
                        "study_modules",
                        "fk_modules_plan",
                        """
                        UPDATE study_plan.study_modules
                        SET
                            plan_id = %s,
                            subject_id = NULL
                        WHERE id = %s
                        """,
                        (missing_id, module_id)
                    ),

                    (
                        "study_modules",
                        "fk_modules_plan_subject",
                        """
                        UPDATE study_plan.study_modules
                        SET subject_id = %s
                        WHERE id = %s
                        """,
                        (extra_subject_id, module_id)
                    ),

                    # 4. STUDY_TASKS

                    (
                        "study_tasks",
                        "fk_tasks_subject",
                        """
                        UPDATE study_plan.study_tasks
                        SET
                            module_id = NULL,
                            plan_id = NULL,
                            subject_id = %s
                        WHERE id = %s
                        """,
                        (missing_id, task_id)
                    ),

                    (
                        "study_tasks",
                        "fk_tasks_plan",
                        """
                        UPDATE study_plan.study_tasks
                        SET
                            module_id = NULL,
                            subject_id = NULL,
                            plan_id = %s
                        WHERE id = %s
                        """,
                        (missing_id, task_id)
                    ),

                    (
                        "study_tasks",
                        "fk_tasks_module",
                        """
                        UPDATE study_plan.study_tasks
                        SET module_id = %s
                        WHERE id = %s
                        """,
                        (missing_id, task_id)
                    ),

                    (
                        "study_tasks",
                        "fk_tasks_plan_subject",
                        """
                        UPDATE study_plan.study_tasks
                        SET
                            module_id = NULL,
                            plan_id = %s,
                            subject_id = %s
                        WHERE id = %s
                        """,
                        (
                            plan_id,
                            extra_subject_id,
                            task_id
                        )
                    ),

                    # 5. SCHEDULED_CLASSES

                    (
                        "scheduled_classes",
                        "fk_classes_subject_type",
                        """
                        UPDATE study_plan.scheduled_classes
                        SET class_type = %s
                        WHERE id = %s
                        """,
                        ("lecture", class_id)
                    ),

                    # 6. STUDY_SESSIONS

                    (
                        "study_sessions",
                        "fk_sessions_subject",
                        """
                        UPDATE study_plan.study_sessions
                        SET
                            task_id = NULL,
                            plan_id = NULL,
                            subject_id = %s
                        WHERE id = %s
                        """,
                        (missing_id, session_id)
                    ),

                    (
                        "study_sessions",
                        "fk_sessions_plan",
                        """
                        UPDATE study_plan.study_sessions
                        SET
                            task_id = NULL,
                            subject_id = NULL,
                            plan_id = %s
                        WHERE id = %s
                        """,
                        (missing_id, session_id)
                    ),

                    (
                        "study_sessions",
                        "fk_sessions_task",
                        """
                        UPDATE study_plan.study_sessions
                        SET task_id = %s
                        WHERE id = %s
                        """,
                        (missing_id, session_id)
                    ),

                    (
                        "study_sessions",
                        "fk_sessions_plan_subject",
                        """
                        UPDATE study_plan.study_sessions
                        SET
                            task_id = NULL,
                            plan_id = %s,
                            subject_id = %s
                        WHERE id = %s
                        """,
                        (
                            plan_id,
                            extra_subject_id,
                            session_id
                        )
                    ),

                    # 7. IMPORTANT_EVENTS

                    (
                        "important_events",
                        "fk_events_subject",
                        """
                        UPDATE study_plan.important_events
                        SET
                            task_id = NULL,
                            plan_id = NULL,
                            subject_id = %s
                        WHERE id = %s
                        """,
                        (missing_id, deadline_id)
                    ),

                    (
                        "important_events",
                        "fk_events_plan",
                        """
                        UPDATE study_plan.important_events
                        SET
                            task_id = NULL,
                            subject_id = NULL,
                            plan_id = %s
                        WHERE id = %s
                        """,
                        (missing_id, deadline_id)
                    ),

                    (
                        "important_events",
                        "fk_events_task",
                        """
                        UPDATE study_plan.important_events
                        SET task_id = %s
                        WHERE id = %s
                        """,
                        (missing_id, deadline_id)
                    ),

                    (
                        "important_events",
                        "fk_events_class",
                        """
                        UPDATE study_plan.important_events
                        SET class_id = %s
                        WHERE id = %s
                        """,
                        (missing_id, defense_id)
                    ),

                    (
                        "important_events",
                        "fk_events_plan_subject",
                        """
                        UPDATE study_plan.important_events
                        SET
                            task_id = NULL,
                            plan_id = %s,
                            subject_id = %s
                        WHERE id = %s
                        """,
                        (
                            plan_id,
                            extra_subject_id,
                            deadline_id
                        )
                    )
                ]

                # Перевірка метаданих зовнішніх ключів

                print("\n=== FOREIGN KEY METADATA VALIDATION ===")

                cur.execute("""
                    SELECT
                        t.relname,
                        c.conname,
                        c.convalidated,
                        cardinality(c.conkey)
                    FROM pg_constraint c
                    JOIN pg_class t
                        ON t.oid = c.conrelid
                    JOIN pg_namespace n
                        ON n.oid = t.relnamespace
                    WHERE n.nspname = 'study_plan'
                        AND c.contype = 'f'
                """)

                actual_constraints = {}

                for table_name, name, validated, column_count in cur.fetchall():

                    actual_constraints[
                        (table_name, name)
                    ] = (
                        validated,
                        column_count
                    )

                composite_constraints = {
                    "fk_modules_plan_subject",
                    "fk_tasks_plan_subject",
                    "fk_classes_subject_type",
                    "fk_sessions_plan_subject",
                    "fk_events_plan_subject"
                }

                expected_constraints = {
                    (table_name, name): (
                        True,
                        2 if name in composite_constraints else 1
                    )
                    for table_name, name, query, params
                    in test_cases
                }

                metadata_match = (
                    actual_constraints == expected_constraints
                    and len(test_cases) == 19
                    and len(expected_constraints) == 19
                )

                simple_count = sum(
                    column_count == 1
                    for validated, column_count
                    in actual_constraints.values()
                )

                composite_count = sum(
                    column_count == 2
                    for validated, column_count
                    in actual_constraints.values()
                )

                print(
                    "Expected foreign keys:",
                    len(expected_constraints)
                )

                print(
                    "Actual foreign keys:",
                    len(actual_constraints)
                )

                print("Simple foreign keys:", simple_count)
                print("Composite foreign keys:", composite_count)
                print("Foreign key metadata match:", metadata_match)

                if not metadata_match:

                    print("Expected:", expected_constraints)
                    print("Actual:", actual_constraints)

                    raise AssertionError(
                        "Foreign key metadata mismatch"
                    )

                # Виконання негативних тестів

                print("\n=== FOREIGN KEY NEGATIVE TESTS ===")

                checks = {}

                for table_name, name, query, params in test_cases:

                    print(f"\nTesting FOREIGN KEY: {name}")

                    result = execute_expected_error(
                        cursor=cur,
                        query=query,
                        params=params,
                        expected_error=errors.ForeignKeyViolation,
                        expected_constraint=name,
                        expected_table=table_name
                    )

                    checks[name] = result

                    print(
                        "Result:",
                        "PASS" if result else "FAIL"
                    )

                # Перевірка стану тестових записів

                print("\n=== TEST RECORD INTEGRITY ===")

                cur.execute(
                    "SET CONSTRAINTS ALL IMMEDIATE"
                )

                expected_test_counts = {
                    table_name: count + (
                        2 if table_name in (
                            "subjects",
                            "important_events"
                        )
                        else 1
                    )
                    for table_name, count
                    in initial_counts.items()
                }

                current_counts = get_record_counts(cur)

                test_records_match = (
                    current_counts
                    == test_counts
                    == expected_test_counts
                )

                print(
                    "Test record counts unchanged:",
                    test_records_match
                )

                print("Remaining constraints: VALID")

                # Повний відкат

                print("\n=== ROLLBACK ===")

                conn.rollback()

                final_counts = get_record_counts(cur)

                rollback_match = (
                    final_counts == initial_counts
                )

                print("Rollback completed")

                for table_name in tables:

                    print(
                        f"{table_name}: "
                        f"initial={initial_counts[table_name]}, "
                        f"final={final_counts[table_name]}"
                    )

                print(
                    "Initial database state restored:",
                    rollback_match
                )

                # Окремі підсумки простих і складених ключів

                simple_checks = {
                    name: result
                    for name, result in checks.items()
                    if name not in composite_constraints
                }

                composite_checks = {
                    name: result
                    for name, result in checks.items()
                    if name in composite_constraints
                }

                print("\n=== SIMPLE FOREIGN KEY SUMMARY ===")

                print(
                    "Total simple checks:",
                    len(simple_checks)
                )

                print(
                    "Passed simple checks:",
                    sum(simple_checks.values())
                )

                print("\n=== COMPOSITE FOREIGN KEY SUMMARY ===")

                print(
                    "Total composite checks:",
                    len(composite_checks)
                )

                print(
                    "Passed composite checks:",
                    sum(composite_checks.values())
                )

                # Загальний підсумок

                full_match = (
                    metadata_match
                    and simple_count == 14
                    and composite_count == 5
                    and len(simple_checks) == 14
                    and len(composite_checks) == 5
                    and len(checks) == 19
                    and all(checks.values())
                    and test_records_match
                    and rollback_match
                )

                print("\n=== FINAL FOREIGN KEY VALIDATION ===")

                print("Total checks:", len(checks))

                print(
                    "Passed checks:",
                    sum(checks.values())
                )

                print(
                    "Failed checks:",
                    sum(
                        not result
                        for result in checks.values()
                    )
                )

                print(
                    "Failed constraints:",
                    [
                        name for name, result
                        in checks.items()
                        if not result
                    ]
                )

                print(
                    "Full foreign key validation:",
                    full_match
                )

                if not full_match:
                    raise AssertionError(
                        "Foreign key validation failed"
                    )

            finally:
                conn.rollback()

    print("Connection closed")
    print("=== FOREIGN KEY TEST COMPLETED ===")

def test_unique_constraints():
    """Перевірка UNIQUE та зміни порядку навчальних модулів."""

    tables = [
        "subjects",
        "study_plans",
        "study_plan_subjects",
        "subject_class_types",
        "study_modules",
        "study_tasks",
        "scheduled_classes",
        "study_sessions",
        "important_events"
    ]

    def get_record_counts(cursor):
        counts = {}

        for table_name in tables:
            query = sql.SQL(
                "SELECT COUNT(*) FROM {}.{}"
            ).format(
                sql.Identifier("study_plan"),
                sql.Identifier(table_name)
            )

            cursor.execute(query)

            counts[table_name] = cursor.fetchone()[0]

        return counts

    def create_module(
        cursor,
        plan_id,
        subject_id,
        title,
        position
    ):
        """Створення тестового навчального модуля."""

        cursor.execute("""
            INSERT INTO study_plan.study_modules (
                plan_id,
                subject_id,
                title,
                position
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (
            plan_id,
            subject_id,
            title,
            position
        ))

        return cursor.fetchone()[0]

    def get_position(cursor, module_id):
        """Отримання поточної позиції модуля."""

        cursor.execute("""
            SELECT position
            FROM study_plan.study_modules
            WHERE id = %s
        """, (module_id,))

        return cursor.fetchone()[0]

    checks = {}

    with closing(get_connection()) as conn:
        with conn.cursor() as cur:

            try:
                print("\n=== UNIQUE CONSTRAINT TEST ===")

                # Перевірка підключення

                cur.execute("""
                    SELECT
                        current_database(),
                        current_user,
                        current_schema()
                """)

                if cur.fetchone() != (
                    "studyplanner",
                    "study_plan_user",
                    "study_plan"
                ):
                    raise RuntimeError(
                        "Unexpected connection settings"
                    )

                if conn.autocommit:
                    raise RuntimeError(
                        "Autocommit must be disabled"
                    )

                print("Connection settings: VALID")

                initial_counts = get_record_counts(cur)

                # 1. Перевірка метаданих UNIQUE

                print("\n=== UNIQUE METADATA VALIDATION ===")

                cur.execute("""
                    SELECT
                        c.conname,
                        c.convalidated,
                        c.condeferrable,
                        c.condeferred,
                        i.indisunique,
                        i.indnullsnotdistinct,
                        i.indisvalid,
                        i.indisready,
                        ARRAY(
                            SELECT a.attname::text
                            FROM unnest(c.conkey)
                            WITH ORDINALITY
                                AS k(attnum, ordinality)
                            JOIN pg_attribute a
                                ON a.attrelid = c.conrelid
                                AND a.attnum = k.attnum
                            ORDER BY k.ordinality
                        )
                    FROM pg_constraint c
                    JOIN pg_class t
                        ON t.oid = c.conrelid
                    JOIN pg_namespace n
                        ON n.oid = t.relnamespace
                    JOIN pg_index i
                        ON i.indexrelid = c.conindid
                    WHERE n.nspname = 'study_plan'
                        AND t.relname = 'study_modules'
                        AND c.contype = 'u'
                """)

                actual_metadata = cur.fetchall()

                expected_metadata = [
                    (
                        "uq_modules_position",
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        True,
                        [
                            "plan_id",
                            "subject_id",
                            "position"
                        ]
                    )
                ]

                checks["UNIQUE metadata"] = (
                    actual_metadata == expected_metadata
                )

                print("Actual metadata:", actual_metadata)

                print(
                    "UNIQUE metadata match:",
                    checks["UNIQUE metadata"]
                )

                if not checks["UNIQUE metadata"]:
                    raise AssertionError(
                        "UNIQUE metadata mismatch"
                    )

                # Підготовка тестових записів

                print("\n=== CREATE TEST RECORDS ===")

                records = create_test_records(cur)

                user_id = records["user_id"]
                plan_id = records["plan_id"]
                subject_id = records["subject_id"]
                module_id = records["module_id"]

                # Другий модуль тієї самої дисципліни

                second_module_id = create_module(
                    cur,
                    plan_id,
                    subject_id,
                    "Другий тестовий модуль",
                    2
                )

                # Загальний модуль без дисципліни

                general_module_id = create_module(
                    cur,
                    plan_id,
                    None,
                    "Загальний тестовий модуль",
                    1
                )

                # Додаткова дисципліна

                cur.execute("""
                    INSERT INTO study_plan.subjects (
                        user_id,
                        name
                    )
                    VALUES (%s, %s)
                    RETURNING id
                """, (
                    user_id,
                    "Додаткова тестова дисципліна"
                ))

                second_subject_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO study_plan.study_plan_subjects (
                        plan_id,
                        subject_id
                    )
                    VALUES (%s, %s)
                """, (
                    plan_id,
                    second_subject_id
                ))

                # Додатковий навчальний план

                cur.execute("""
                    INSERT INTO study_plan.study_plans (
                        user_id,
                        plan_type,
                        title
                    )
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    "academic",
                    "Другий тестовий план"
                ))

                second_plan_id = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO study_plan.study_plan_subjects (
                        plan_id,
                        subject_id
                    )
                    VALUES (%s, %s)
                """, (
                    second_plan_id,
                    subject_id
                ))

                # Перевірка початкових обмежень

                cur.execute(
                    "SET CONSTRAINTS ALL IMMEDIATE"
                )

                print("Test records created")
                print("Initial constraints: VALID")

                # 2. Різні позиції в одній групі

                print("\n=== VALID MODULE POSITIONS ===")

                first_position = get_position(
                    cur, module_id
                )

                second_position = get_position(
                    cur, second_module_id
                )

                checks["Different positions"] = (
                    first_position == 1
                    and second_position == 2
                )

                print("First module:", first_position)
                print("Second module:", second_position)

                # 3. Дублікат позиції в одній дисципліні

                print("\n=== DUPLICATE SUBJECT POSITION ===")

                checks["Duplicate subject position rejected"] = (
                    execute_expected_error(
                        cursor=cur,
                        query="""
                            INSERT INTO study_plan.study_modules (
                                plan_id,
                                subject_id,
                                title,
                                position
                            )
                            VALUES (%s, %s, %s, %s)
                        """,
                        params=(
                            plan_id,
                            subject_id,
                            "Некоректний дублікат",
                            1
                        ),
                        expected_error=errors.UniqueViolation,
                        expected_constraint="uq_modules_position",
                        expected_table="study_modules"
                    )
                )

                # 4. Дублікат позиції при subject_id = NULL

                print("\n=== DUPLICATE NULL SUBJECT POSITION ===")

                checks["Duplicate NULL position rejected"] = (
                    execute_expected_error(
                        cursor=cur,
                        query="""
                            INSERT INTO study_plan.study_modules (
                                plan_id,
                                subject_id,
                                title,
                                position
                            )
                            VALUES (%s, NULL, %s, %s)
                        """,
                        params=(
                            plan_id,
                            "Дублікат загального модуля",
                            1
                        ),
                        expected_error=errors.UniqueViolation,
                        expected_constraint="uq_modules_position",
                        expected_table="study_modules"
                    )
                )

                # 5. Однакова позиція в різних дисциплінах

                print("\n=== POSITION IN DIFFERENT SUBJECTS ===")

                extra_module_id = create_module(
                    cur,
                    plan_id,
                    second_subject_id,
                    "Модуль іншої дисципліни",
                    1
                )

                checks["Same position in different subjects"] = (
                    get_position(cur, module_id) == 1
                    and get_position(cur, extra_module_id) == 1
                )

                # 6. Однакова позиція в різних планах

                print("\n=== POSITION IN DIFFERENT PLANS ===")

                another_plan_module_id = create_module(
                    cur,
                    second_plan_id,
                    subject_id,
                    "Модуль іншого плану",
                    1
                )

                another_general_id = create_module(
                    cur,
                    second_plan_id,
                    None,
                    "Загальний модуль іншого плану",
                    1
                )

                checks["Same position in different plans"] = (
                    get_position(cur, module_id) == 1
                    and get_position(
                        cur, another_plan_module_id
                    ) == 1
                    and get_position(
                        cur, general_module_id
                    ) == 1
                    and get_position(
                        cur, another_general_id
                    ) == 1
                )

                # 7. Тимчасовий конфлікт позицій

                print("\n=== DEFERRED POSITION CONFLICT ===")

                cur.execute(
                    "SET CONSTRAINTS "
                    "study_plan.uq_modules_position DEFERRED"
                )

                cur.execute("""
                    UPDATE study_plan.study_modules
                    SET position = 2
                    WHERE id = %s
                """, (module_id,))

                first_position = get_position(
                    cur, module_id
                )

                second_position = get_position(
                    cur, second_module_id
                )

                checks["Temporary conflict allowed"] = (
                    first_position == 2
                    and second_position == 2
                )

                print(
                    "Temporary positions:",
                    first_position,
                    second_position
                )

                # 8. Завершення перестановки модулів

                print("\n=== MODULE POSITION SWAP ===")

                cur.execute("""
                    UPDATE study_plan.study_modules
                    SET position = 1
                    WHERE id = %s
                """, (second_module_id,))

                cur.execute(
                    "SET CONSTRAINTS "
                    "study_plan.uq_modules_position IMMEDIATE"
                )

                first_position = get_position(
                    cur, module_id
                )

                second_position = get_position(
                    cur, second_module_id
                )

                checks["Module position swap"] = (
                    first_position == 2
                    and second_position == 1
                )

                print(
                    "Final positions:",
                    first_position,
                    second_position
                )

                print("Deferred constraint: VALID")

                # 9. Невиправлений конфлікт позицій

                print("\n=== UNRESOLVED DEFERRED CONFLICT ===")

                cur.execute(
                    "SET CONSTRAINTS "
                    "study_plan.uq_modules_position DEFERRED"
                )

                cur.execute("SAVEPOINT deferred_test")

                conflict_rejected = False

                try:
                    cur.execute("""
                        UPDATE study_plan.study_modules
                        SET position = 1
                        WHERE id = %s
                    """, (module_id,))

                    cur.execute(
                        "SET CONSTRAINTS "
                        "study_plan.uq_modules_position IMMEDIATE"
                    )

                except errors.UniqueViolation as error:

                    conflict_rejected = (
                        error.sqlstate == "23505"
                        and error.diag.constraint_name
                            == "uq_modules_position"
                        and error.diag.table_name
                            == "study_modules"
                    )

                    print("SQLSTATE:", error.sqlstate)

                    print(
                        "Constraint:",
                        error.diag.constraint_name
                    )

                finally:
                    cur.execute(
                        "ROLLBACK TO SAVEPOINT deferred_test"
                    )

                    cur.execute(
                        "RELEASE SAVEPOINT deferred_test"
                    )

                checks["Unresolved conflict rejected"] = (
                    conflict_rejected
                )

                # Перевірка стану після SAVEPOINT

                cur.execute(
                    "SET CONSTRAINTS ALL IMMEDIATE"
                )

                if (
                    get_position(cur, module_id) != 2
                    or get_position(cur, second_module_id) != 1
                ):
                    raise AssertionError(
                        "Module positions were not restored"
                    )

                print("Module positions restored")

                # 10. Повний відкат тестових змін

                print("\n=== ROLLBACK ===")

                conn.rollback()

                final_counts = get_record_counts(cur)

                checks["Initial database state restored"] = (
                    final_counts == initial_counts
                )

                for table_name in tables:
                    print(
                        f"{table_name}: "
                        f"initial={initial_counts[table_name]}, "
                        f"final={final_counts[table_name]}"
                    )

                # Підсумки тестування

                print("\n=== FINAL UNIQUE VALIDATION ===")

                for name, result in checks.items():

                    print(
                        f"{name}: "
                        f"{'PASS' if result else 'FAIL'}"
                    )

                full_match = (
                    len(checks) == 10
                    and all(checks.values())
                )

                print("\nTotal checks:", len(checks))

                print(
                    "Passed checks:",
                    sum(checks.values())
                )

                print(
                    "Failed checks:",
                    sum(
                        not result
                        for result in checks.values()
                    )
                )

                print(
                    "Failed scenarios:",
                    [
                        name for name, result
                        in checks.items()
                        if not result
                    ]
                )

                print(
                    "Full UNIQUE validation:",
                    full_match
                )

                if not full_match:
                    raise AssertionError(
                        "UNIQUE validation failed"
                    )

            finally:
                conn.rollback()

    print("Connection closed")
    print("=== UNIQUE CONSTRAINT TEST COMPLETED ===")

def test_delete_rules():
    """Практична перевірка правил ON DELETE."""

    tables = [
        "subjects",
        "study_plans",
        "study_plan_subjects",
        "subject_class_types",
        "study_modules",
        "study_tasks",
        "scheduled_classes",
        "study_sessions",
        "important_events"
    ]

    expected_rules = {
        "fk_plan_subjects_plan": "CASCADE",
        "fk_plan_subjects_subject": "CASCADE",
        "fk_subject_class_types_subject": "CASCADE",
        "fk_modules_plan": "RESTRICT",
        "fk_modules_plan_subject": "RESTRICT",
        "fk_tasks_subject": "RESTRICT",
        "fk_tasks_plan": "SET NULL",
        "fk_tasks_module": "RESTRICT",
        "fk_tasks_plan_subject": "NO ACTION",
        "fk_classes_subject_type": "RESTRICT",
        "fk_sessions_subject": "RESTRICT",
        "fk_sessions_plan": "SET NULL",
        "fk_sessions_task": "RESTRICT",
        "fk_sessions_plan_subject": "NO ACTION",
        "fk_events_subject": "RESTRICT",
        "fk_events_plan": "SET NULL",
        "fk_events_task": "RESTRICT",
        "fk_events_class": "RESTRICT",
        "fk_events_plan_subject": "NO ACTION"
    }

    def get_record_counts(cursor):
        counts = {}

        for table_name in tables:
            query = sql.SQL(
                "SELECT COUNT(*) FROM {}.{}"
            ).format(
                sql.Identifier("study_plan"),
                sql.Identifier(table_name)
            )

            cursor.execute(query)
            counts[table_name] = cursor.fetchone()[0]

        return counts

    def execute_scalar(cursor, query, params):
        """Отримання одного значення із SQL-запиту."""

        cursor.execute(query, params)
        return cursor.fetchone()[0]

    checks = {}

    with closing(get_connection()) as conn:
        with conn.cursor() as cur:

            try:
                print("\n=== ON DELETE RULES TEST ===")

                # Перевірка підключення

                cur.execute("""
                    SELECT
                        current_database(),
                        current_user,
                        current_schema()
                """)

                if cur.fetchone() != (
                    "studyplanner",
                    "study_plan_user",
                    "study_plan"
                ):
                    raise RuntimeError(
                        "Unexpected connection settings"
                    )

                if conn.autocommit:
                    raise RuntimeError(
                        "Autocommit must be disabled"
                    )

                print("Connection settings: VALID")

                initial_counts = get_record_counts(cur)

                # Перевірка метаданих ON DELETE

                print("\n=== DELETE RULES METADATA ===")

                cur.execute("""
                    SELECT
                        constraint_name,
                        delete_rule
                    FROM information_schema.referential_constraints
                    WHERE constraint_schema = 'study_plan'
                """)

                actual_rules = dict(cur.fetchall())

                metadata_match = (
                    actual_rules == expected_rules
                )

                print("Expected rules:", len(expected_rules))
                print("Actual rules:", len(actual_rules))

                for rule in [
                    "CASCADE",
                    "RESTRICT",
                    "SET NULL",
                    "NO ACTION"
                ]:
                    print(
                        rule + ":",
                        list(actual_rules.values()).count(rule)
                    )

                print("Delete rules metadata match:", metadata_match)

                if not metadata_match:
                    raise AssertionError(
                        "Delete rules metadata mismatch"
                    )

                # Створення основних тестових записів

                print("\n=== CREATE TEST RECORDS ===")

                records = create_test_records(cur)

                user_id = records["user_id"]
                subject_id = records["subject_id"]
                plan_id = records["plan_id"]
                module_id = records["module_id"]
                task_id = records["task_id"]
                class_id = records["class_id"]
                session_id = records["session_id"]
                deadline_id = records["deadline_id"]
                defense_id = records["defense_id"]

                # Додаткова незалежна дисципліна

                cur.execute("""
                    INSERT INTO study_plan.subjects (
                        user_id, name
                    )
                    VALUES (%s, %s)
                    RETURNING id
                """, (
                    user_id,
                    "Додаткова тестова дисципліна"
                ))

                extra_subject_id = cur.fetchone()[0]

                # Додатковий незалежний план

                cur.execute("""
                    INSERT INTO study_plan.study_plans (
                        user_id, plan_type, title
                    )
                    VALUES (%s, %s, %s)
                    RETURNING id
                """, (
                    user_id,
                    "academic",
                    "Додатковий тестовий план"
                ))

                extra_plan_id = cur.fetchone()[0]

                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

                baseline_counts = get_record_counts(cur)

                expected_baseline = {
                    table: count + (
                        2 if table in (
                            "subjects",
                            "study_plans",
                            "important_events"
                        )
                        else 1
                    )
                    for table, count in initial_counts.items()
                }

                if baseline_counts != expected_baseline:
                    raise AssertionError(
                        "Unexpected test record counts"
                    )

                print("Test records created")
                print("Initial constraints: VALID")

                # Допоміжні SQL-запити видалення

                delete_extra_plan = """
                    DELETE FROM study_plan.study_plans
                    WHERE id = %s
                """

                delete_extra_subject = """
                    DELETE FROM study_plan.subjects
                    WHERE id = %s
                """

                delete_plan_subject = """
                    DELETE FROM study_plan.study_plan_subjects
                    WHERE plan_id = %s
                        AND subject_id = %s
                """

                # Запуск одного сценарію CASCADE або SET NULL

                def test_successful_delete(
                    name,
                    setup,
                    delete_query,
                    delete_params,
                    verification_query,
                    verification_params,
                    expected_value
                ):
                    print(f"\nTesting {expected_rules[name]}: {name}")

                    cur.execute("SAVEPOINT delete_scenario")

                    try:
                        for query, params in setup:
                            cur.execute(query, params)

                        cur.execute(delete_query, delete_params)

                        parent_deleted = cur.rowcount == 1

                        cur.execute(
                            "SET CONSTRAINTS ALL IMMEDIATE"
                        )

                        actual_value = execute_scalar(
                            cur,
                            verification_query,
                            verification_params
                        )

                        result = (
                            parent_deleted
                            and actual_value == expected_value
                        )

                        print("Parent deleted:", parent_deleted)
                        print("Expected value:", expected_value)
                        print("Actual value:", actual_value)

                        checks[name] = result

                    finally:
                        cur.execute(
                            "ROLLBACK TO SAVEPOINT delete_scenario"
                        )

                        cur.execute(
                            "RELEASE SAVEPOINT delete_scenario"
                        )

                    print(
                        "Result:",
                        "PASS" if checks[name] else "FAIL"
                    )

                # Запуск одного сценарію RESTRICT або NO ACTION

                def test_blocked_delete(
                    name,
                    table_name,
                    setup,
                    delete_query,
                    delete_params
                ):
                    print(f"\nTesting {expected_rules[name]}: {name}")

                    cur.execute("SAVEPOINT delete_scenario")

                    try:
                        for query, params in setup:
                            cur.execute(query, params)

                        result = execute_expected_error(
                            cursor=cur,
                            query=delete_query,
                            params=delete_params,
                            expected_error=errors.ForeignKeyViolation,
                            expected_constraint=name,
                            expected_table=table_name
                        )

                        checks[name] = result

                    finally:
                        cur.execute(
                            "ROLLBACK TO SAVEPOINT delete_scenario"
                        )

                        cur.execute(
                            "RELEASE SAVEPOINT delete_scenario"
                        )

                    print(
                        "Result:",
                        "PASS" if checks[name] else "FAIL"
                    )

                # ========================================
                # 1. CASCADE — 3 перевірки
                # ========================================

                print("\n=== CASCADE TESTS ===")

                # Видалення плану видаляє зв'язок із дисципліною

                test_successful_delete(
                    "fk_plan_subjects_plan",
                    [
                        (
                            """
                            INSERT INTO study_plan.study_plan_subjects (
                                plan_id, subject_id
                            )
                            VALUES (%s, %s)
                            """,
                            (extra_plan_id, subject_id)
                        )
                    ],
                    delete_extra_plan,
                    (extra_plan_id,),
                    """
                    SELECT COUNT(*)
                    FROM study_plan.study_plan_subjects
                    WHERE plan_id = %s
                        AND subject_id = %s
                    """,
                    (extra_plan_id, subject_id),
                    0
                )

                # Видалення дисципліни видаляє зв'язок із планом

                test_successful_delete(
                    "fk_plan_subjects_subject",
                    [
                        (
                            """
                            INSERT INTO study_plan.study_plan_subjects (
                                plan_id, subject_id
                            )
                            VALUES (%s, %s)
                            """,
                            (plan_id, extra_subject_id)
                        )
                    ],
                    delete_extra_subject,
                    (extra_subject_id,),
                    """
                    SELECT COUNT(*)
                    FROM study_plan.study_plan_subjects
                    WHERE plan_id = %s
                        AND subject_id = %s
                    """,
                    (plan_id, extra_subject_id),
                    0
                )

                # Видалення дисципліни видаляє типи її занять

                test_successful_delete(
                    "fk_subject_class_types_subject",
                    [
                        (
                            """
                            INSERT INTO study_plan.subject_class_types (
                                subject_id, class_type, total_classes
                            )
                            VALUES (%s, %s, %s)
                            """,
                            (extra_subject_id, "lecture", 10)
                        )
                    ],
                    delete_extra_subject,
                    (extra_subject_id,),
                    """
                    SELECT COUNT(*)
                    FROM study_plan.subject_class_types
                    WHERE subject_id = %s
                    """,
                    (extra_subject_id,),
                    0
                )

                # ========================================
                # 2. RESTRICT — 10 перевірок
                # ========================================

                print("\n=== RESTRICT TESTS ===")

                # Заборона видалення плану з модулем

                test_blocked_delete(
                    "fk_modules_plan",
                    "study_modules",
                    [
                        (
                            """
                            UPDATE study_plan.study_modules
                            SET plan_id = %s,
                                subject_id = NULL
                            WHERE id = %s
                            """,
                            (extra_plan_id, module_id)
                        )
                    ],
                    delete_extra_plan,
                    (extra_plan_id,)
                )

                # Заборона видалення зв'язку плану
                # з дисципліною, якщо існує модуль

                test_blocked_delete(
                    "fk_modules_plan_subject",
                    "study_modules",
                    [],
                    delete_plan_subject,
                    (plan_id, subject_id)
                )

                # Заборона видалення дисципліни із завданням

                test_blocked_delete(
                    "fk_tasks_subject",
                    "study_tasks",
                    [
                        (
                            """
                            UPDATE study_plan.study_tasks
                            SET module_id = NULL,
                                subject_id = %s
                            WHERE id = %s
                            """,
                            (extra_subject_id, task_id)
                        )
                    ],
                    delete_extra_subject,
                    (extra_subject_id,)
                )

                # Заборона видалення модуля із завданням

                test_blocked_delete(
                    "fk_tasks_module",
                    "study_tasks",
                    [],
                    """
                    DELETE FROM study_plan.study_modules
                    WHERE id = %s
                    """,
                    (module_id,)
                )

                # Заборона видалення типу заняття,
                # який використовується в розкладі

                test_blocked_delete(
                    "fk_classes_subject_type",
                    "scheduled_classes",
                    [],
                    """
                    DELETE FROM study_plan.subject_class_types
                    WHERE subject_id = %s
                        AND class_type = %s
                    """,
                    (subject_id, records["class_type"])
                )

                # Заборона видалення дисципліни із сесією

                test_blocked_delete(
                    "fk_sessions_subject",
                    "study_sessions",
                    [
                        (
                            """
                            UPDATE study_plan.study_sessions
                            SET task_id = NULL,
                                subject_id = %s
                            WHERE id = %s
                            """,
                            (extra_subject_id, session_id)
                        )
                    ],
                    delete_extra_subject,
                    (extra_subject_id,)
                )

                # Заборона видалення завдання із сесією

                test_blocked_delete(
                    "fk_sessions_task",
                    "study_sessions",
                    [
                        (
                            """
                            DELETE FROM study_plan.important_events
                            WHERE id IN (%s, %s)
                            """,
                            (deadline_id, defense_id)
                        )
                    ],
                    """
                    DELETE FROM study_plan.study_tasks
                    WHERE id = %s
                    """,
                    (task_id,)
                )

                # Заборона видалення дисципліни з подією

                test_blocked_delete(
                    "fk_events_subject",
                    "important_events",
                    [
                        (
                            """
                            UPDATE study_plan.important_events
                            SET task_id = NULL,
                                subject_id = %s
                            WHERE id = %s
                            """,
                            (extra_subject_id, deadline_id)
                        )
                    ],
                    delete_extra_subject,
                    (extra_subject_id,)
                )

                # Заборона видалення завдання з подіями

                test_blocked_delete(
                    "fk_events_task",
                    "important_events",
                    [
                        (
                            """
                            DELETE FROM study_plan.study_sessions
                            WHERE id = %s
                            """,
                            (session_id,)
                        )
                    ],
                    """
                    DELETE FROM study_plan.study_tasks
                    WHERE id = %s
                    """,
                    (task_id,)
                )

                # Заборона видалення заняття з подією

                test_blocked_delete(
                    "fk_events_class",
                    "important_events",
                    [],
                    """
                    DELETE FROM study_plan.scheduled_classes
                    WHERE id = %s
                    """,
                    (class_id,)
                )

                # ========================================
                # 3. SET NULL — 3 перевірки
                # ========================================

                print("\n=== SET NULL TESTS ===")

                # Завдання залишається після видалення плану

                test_successful_delete(
                    "fk_tasks_plan",
                    [
                        (
                            """
                            UPDATE study_plan.study_tasks
                            SET module_id = NULL,
                                plan_id = %s
                            WHERE id = %s
                            """,
                            (extra_plan_id, task_id)
                        )
                    ],
                    delete_extra_plan,
                    (extra_plan_id,),
                    """
                    SELECT COUNT(*)
                    FROM study_plan.study_tasks
                    WHERE id = %s
                        AND plan_id IS NULL
                    """,
                    (task_id,),
                    1
                )

                # Сесія залишається після видалення плану

                test_successful_delete(
                    "fk_sessions_plan",
                    [
                        (
                            """
                            UPDATE study_plan.study_sessions
                            SET task_id = NULL,
                                plan_id = %s
                            WHERE id = %s
                            """,
                            (extra_plan_id, session_id)
                        )
                    ],
                    delete_extra_plan,
                    (extra_plan_id,),
                    """
                    SELECT COUNT(*)
                    FROM study_plan.study_sessions
                    WHERE id = %s
                        AND plan_id IS NULL
                    """,
                    (session_id,),
                    1
                )

                # Подія залишається після видалення плану

                test_successful_delete(
                    "fk_events_plan",
                    [
                        (
                            """
                            UPDATE study_plan.important_events
                            SET task_id = NULL,
                                plan_id = %s
                            WHERE id = %s
                            """,
                            (extra_plan_id, deadline_id)
                        )
                    ],
                    delete_extra_plan,
                    (extra_plan_id,),
                    """
                    SELECT COUNT(*)
                    FROM study_plan.important_events
                    WHERE id = %s
                        AND plan_id IS NULL
                    """,
                    (deadline_id,),
                    1
                )

                # ========================================
                # 4. NO ACTION — 3 перевірки
                # ========================================

                print("\n=== NO ACTION TESTS ===")

                # Допоміжний зв'язок без навчального модуля

                add_extra_link = (
                    """
                    INSERT INTO study_plan.study_plan_subjects (
                        plan_id, subject_id
                    )
                    VALUES (%s, %s)
                    """,
                    (extra_plan_id, extra_subject_id)
                )

                # Заборона видалення зв'язку,
                # який використовується завданням

                test_blocked_delete(
                    "fk_tasks_plan_subject",
                    "study_tasks",
                    [
                        add_extra_link,
                        (
                            """
                            UPDATE study_plan.study_tasks
                            SET module_id = NULL,
                                plan_id = %s,
                                subject_id = %s
                            WHERE id = %s
                            """,
                            (
                                extra_plan_id,
                                extra_subject_id,
                                task_id
                            )
                        )
                    ],
                    delete_plan_subject,
                    (extra_plan_id, extra_subject_id)
                )

                # Заборона видалення зв'язку,
                # який використовується сесією

                test_blocked_delete(
                    "fk_sessions_plan_subject",
                    "study_sessions",
                    [
                        add_extra_link,
                        (
                            """
                            UPDATE study_plan.study_sessions
                            SET task_id = NULL,
                                plan_id = %s,
                                subject_id = %s
                            WHERE id = %s
                            """,
                            (
                                extra_plan_id,
                                extra_subject_id,
                                session_id
                            )
                        )
                    ],
                    delete_plan_subject,
                    (extra_plan_id, extra_subject_id)
                )

                # Заборона видалення зв'язку,
                # який використовується подією

                test_blocked_delete(
                    "fk_events_plan_subject",
                    "important_events",
                    [
                        add_extra_link,
                        (
                            """
                            UPDATE study_plan.important_events
                            SET task_id = NULL,
                                plan_id = %s,
                                subject_id = %s
                            WHERE id = %s
                            """,
                            (
                                extra_plan_id,
                                extra_subject_id,
                                deadline_id
                            )
                        )
                    ],
                    delete_plan_subject,
                    (extra_plan_id, extra_subject_id)
                )

                # Перевірка стану після всіх сценаріїв

                print("\n=== TEST RECORD INTEGRITY ===")

                cur.execute("SET CONSTRAINTS ALL IMMEDIATE")

                records_restored = (
                    get_record_counts(cur) == baseline_counts
                )

                print(
                    "Test record counts restored:",
                    records_restored
                )

                print("Remaining constraints: VALID")

                # Повний відкат тестових змін

                print("\n=== ROLLBACK ===")

                conn.rollback()

                final_counts = get_record_counts(cur)

                rollback_match = (
                    final_counts == initial_counts
                )

                for table_name in tables:
                    print(
                        f"{table_name}: "
                        f"initial={initial_counts[table_name]}, "
                        f"final={final_counts[table_name]}"
                    )

                print(
                    "Initial database state restored:",
                    rollback_match
                )

                # Підсумки за кожним правилом

                print("\n=== DELETE RULES SUMMARY ===")

                for rule in [
                    "CASCADE",
                    "RESTRICT",
                    "SET NULL",
                    "NO ACTION"
                ]:

                    rule_checks = [
                        result
                        for name, result in checks.items()
                        if expected_rules[name] == rule
                    ]

                    print(
                        f"{rule}: "
                        f"{sum(rule_checks)}/{len(rule_checks)} PASS"
                    )

                full_match = (
                    metadata_match
                    and set(checks) == set(expected_rules)
                    and len(checks) == 19
                    and all(checks.values())
                    and records_restored
                    and rollback_match
                )

                print("\n=== FINAL DELETE RULES VALIDATION ===")

                print("Total checks:", len(checks))
                print("Passed checks:", sum(checks.values()))

                print(
                    "Failed checks:",
                    sum(
                        not result
                        for result in checks.values()
                    )
                )

                print(
                    "Failed constraints:",
                    [
                        name for name, result in checks.items()
                        if not result
                    ]
                )

                print(
                    "Full ON DELETE validation:",
                    full_match
                )

                if not full_match:
                    raise AssertionError(
                        "ON DELETE validation failed"
                    )

            finally:
                conn.rollback()

    print("Connection closed")
    print("=== ON DELETE RULES TEST COMPLETED ===")

def test_schema_isolation():
    """Перевірка прав доступу та ізоляції схем."""

    tables = [
        "subjects",
        "study_plans",
        "study_plan_subjects",
        "subject_class_types",
        "study_modules",
        "study_tasks",
        "scheduled_classes",
        "study_sessions",
        "important_events",
        "schema_migrations"
    ]

    def get_record_counts(cursor):
        counts = {}

        for table_name in tables:
            query = sql.SQL(
                "SELECT COUNT(*) FROM {}.{}"
            ).format(
                sql.Identifier("study_plan"),
                sql.Identifier(table_name)
            )

            cursor.execute(query)
            counts[table_name] = cursor.fetchone()[0]

        return counts

    def get_table_names(cursor):
        cursor.execute("""
            SELECT
                n.nspname,
                t.relname
            FROM pg_class t
            JOIN pg_namespace n
                ON n.oid = t.relnamespace
            WHERE n.nspname IN (
                'auth',
                'study_plan',
                'progress',
                'public'
            )
            AND t.relkind IN ('r', 'p')
            ORDER BY n.nspname, t.relname
        """)

        return cursor.fetchall()

    checks = {}

    with closing(get_connection()) as conn:
        with conn.cursor() as cur:

            try:
                print("\n=== SCHEMA ISOLATION TEST ===")

                # 1. Перевірка підключення

                print("\n=== CONNECTION VALIDATION ===")

                cur.execute("""
                    SELECT
                        current_database(),
                        current_user,
                        session_user,
                        current_schema()
                """)

                connection_settings = cur.fetchone()

                checks["Connection settings"] = (
                    connection_settings == (
                        "studyplanner",
                        "study_plan_user",
                        "study_plan_user",
                        "study_plan"
                    )
                    and not conn.autocommit
                )

                print(
                    "Connection settings:",
                    connection_settings
                )

                print("Autocommit:", conn.autocommit)

                if not checks["Connection settings"]:
                    raise RuntimeError(
                        "Unexpected connection settings"
                    )

                initial_counts = get_record_counts(cur)
                initial_tables = get_table_names(cur)

                # 2. Перевірка атрибутів ролі

                print("\n=== ROLE ATTRIBUTES ===")

                cur.execute("""
                    SELECT
                        rolname,
                        rolsuper,
                        rolcreatedb,
                        rolcreaterole,
                        rolreplication,
                        rolbypassrls,
                        rolcanlogin
                    FROM pg_roles
                    WHERE rolname = current_user
                """)

                actual_role = cur.fetchone()

                expected_role = (
                    "study_plan_user",
                    False,
                    False,
                    False,
                    False,
                    False,
                    True
                )

                checks["Role attributes"] = (
                    actual_role == expected_role
                )

                print("Actual role:", actual_role)

                # 3. Перевірка власників схем

                print("\n=== SCHEMA OWNERS ===")

                cur.execute("""
                    SELECT
                        nspname,
                        pg_get_userbyid(nspowner)
                    FROM pg_namespace
                    WHERE nspname IN (
                        'auth',
                        'study_plan',
                        'progress',
                        'public'
                    )
                """)

                actual_owners = dict(cur.fetchall())

                expected_owners = {
                    "auth": "studyplanner_user",
                    "progress": "studyplanner_user",
                    "study_plan": "studyplanner_user",
                    "public": "pg_database_owner"
                }

                checks["Schema owners"] = (
                    actual_owners == expected_owners
                )

                for schema_name, owner in sorted(
                    actual_owners.items()
                ):
                    print(f"{schema_name}: {owner}")

                # 4. Перевірка search_path

                print("\n=== SEARCH PATH ===")

                cur.execute("SHOW search_path")

                search_path = cur.fetchone()[0]

                checks["Search path"] = (
                    search_path == "study_plan"
                )

                print("Search path:", search_path)

                # 5. Перевірка прав на схеми

                print("\n=== SCHEMA PRIVILEGES ===")

                cur.execute("""
                    SELECT
                        nspname,
                        has_schema_privilege(
                            current_user, oid, 'USAGE'
                        ),
                        has_schema_privilege(
                            current_user, oid, 'CREATE'
                        )
                    FROM pg_namespace
                    WHERE nspname IN (
                        'auth',
                        'study_plan',
                        'progress',
                        'public'
                    )
                """)

                actual_privileges = {
                    name: (usage, create)
                    for name, usage, create
                    in cur.fetchall()
                }

                expected_privileges = {
                    "auth": (False, False),
                    "progress": (False, False),
                    "public": (True, False),
                    "study_plan": (True, True)
                }

                checks["Schema privileges"] = (
                    actual_privileges == expected_privileges
                )

                for name, privileges in sorted(
                    actual_privileges.items()
                ):
                    print(
                        f"{name}: "
                        f"USAGE={privileges[0]}, "
                        f"CREATE={privileges[1]}"
                    )

                # 6. Перевірка членства в ролях

                print("\n=== ROLE MEMBERSHIP ===")

                cur.execute("""
                    SELECT
                        rolname,
                        pg_has_role(
                            current_user, oid, 'MEMBER'
                        )
                    FROM pg_roles
                    WHERE rolname IN (
                        'auth_user',
                        'study_plan_user',
                        'progress_user'
                    )
                """)

                actual_membership = dict(cur.fetchall())

                expected_membership = {
                    "auth_user": False,
                    "progress_user": False,
                    "study_plan_user": True
                }

                checks["Role membership"] = (
                    actual_membership == expected_membership
                )

                print("Role membership:", actual_membership)

                # 7. Перевірка прав на таблиці

                print("\n=== TABLE PRIVILEGES ===")

                cur.execute("""
                    SELECT
                        n.nspname,
                        t.relname,
                        has_table_privilege(
                            current_user, t.oid, 'SELECT'
                        ),
                        has_table_privilege(
                            current_user, t.oid, 'INSERT'
                        ),
                        has_table_privilege(
                            current_user, t.oid, 'UPDATE'
                        ),
                        has_table_privilege(
                            current_user, t.oid, 'DELETE'
                        )
                    FROM pg_class t
                    JOIN pg_namespace n
                        ON n.oid = t.relnamespace
                    WHERE n.nspname IN (
                        'auth',
                        'study_plan',
                        'progress'
                    )
                    AND t.relkind IN ('r', 'p')
                    ORDER BY n.nspname, t.relname
                """)

                own_privileges = {}
                foreign_privileges = {}

                for row in cur.fetchall():

                    schema_name = row[0]
                    table_name = row[1]
                    privileges = tuple(row[2:])

                    print(
                        f"{schema_name}.{table_name}:",
                        privileges
                    )

                    if schema_name == "study_plan":

                        own_privileges[table_name] = (
                            privileges
                        )

                    else:

                        foreign_privileges[
                            (schema_name, table_name)
                        ] = privileges

                expected_own_privileges = {
                    table_name: (
                        True, True, True, True
                    )
                    for table_name in tables
                }

                own_privileges_match = (
                    own_privileges
                    == expected_own_privileges
                )

                foreign_privileges_match = all(
                    privileges == (
                        False, False, False, False
                    )
                    for privileges
                    in foreign_privileges.values()
                )

                checks["Table privileges"] = (
                    own_privileges_match
                    and foreign_privileges_match
                )

                print(
                    "Own tables:",
                    len(own_privileges)
                )

                print(
                    "Foreign tables:",
                    len(foreign_privileges)
                )

                if not foreign_privileges:
                    print(
                        "Foreign table privilege checks: "
                        "NOT APPLICABLE - no foreign tables"
                    )

                # Не продовжуємо практичні операції,
                # якщо базові налаштування некоректні.

                if not all(checks.values()):
                    raise AssertionError(
                        "Security metadata validation failed"
                    )

                # 8. Дозволений INSERT

                print("\n=== ALLOWED INSERT ===")

                user_id = uuid4()

                cur.execute("""
                    INSERT INTO study_plan.subjects (
                        user_id,
                        name
                    )
                    VALUES (%s, %s)
                    RETURNING id
                """, (
                    user_id,
                    "Тест прав доступу"
                ))

                subject_id = cur.fetchone()[0]

                checks["Allowed INSERT"] = (
                    isinstance(subject_id, UUID)
                )

                print("Created subject:", subject_id)

                # 9. Дозволений SELECT

                print("\n=== ALLOWED SELECT ===")

                cur.execute("""
                    SELECT name
                    FROM study_plan.subjects
                    WHERE id = %s
                """, (subject_id,))

                selected_record = cur.fetchone()

                checks["Allowed SELECT"] = (
                    selected_record == (
                        "Тест прав доступу",
                    )
                )

                print("Selected:", selected_record)

                # 10. Дозволений UPDATE

                print("\n=== ALLOWED UPDATE ===")

                cur.execute("""
                    UPDATE study_plan.subjects
                    SET name = %s
                    WHERE id = %s
                    RETURNING name
                """, (
                    "Оновлений тест прав доступу",
                    subject_id
                ))

                updated_record = cur.fetchone()

                checks["Allowed UPDATE"] = (
                    updated_record == (
                        "Оновлений тест прав доступу",
                    )
                )

                print("Updated:", updated_record)

                # 11. Дозволений DELETE

                print("\n=== ALLOWED DELETE ===")

                cur.execute("""
                    DELETE FROM study_plan.subjects
                    WHERE id = %s
                """, (subject_id,))

                deleted = cur.rowcount == 1

                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM study_plan.subjects
                        WHERE id = %s
                    )
                """, (subject_id,))

                exists_after_delete = cur.fetchone()[0]

                checks["Allowed DELETE"] = (
                    deleted
                    and not exists_after_delete
                )

                print("Record deleted:", deleted)

                print(
                    "Record exists after DELETE:",
                    exists_after_delete
                )

                # Унікальна назва тестової таблиці

                test_table_name = (
                    "test_isolation_" + uuid4().hex
                )

                # 12. Дозволене створення власної таблиці

                print("\n=== ALLOWED CREATE TABLE ===")

                create_query = sql.SQL("""
                    CREATE TABLE {}.{} (
                        id INTEGER PRIMARY KEY
                    )
                """).format(
                    sql.Identifier("study_plan"),
                    sql.Identifier(test_table_name)
                )

                cur.execute(create_query)

                cur.execute("""
                    SELECT EXISTS (
                        SELECT 1
                        FROM pg_class t
                        JOIN pg_namespace n
                            ON n.oid = t.relnamespace
                        WHERE n.nspname = %s
                            AND t.relname = %s
                            AND t.relkind = 'r'
                    )
                """, (
                    "study_plan",
                    test_table_name
                ))

                checks["Allowed CREATE TABLE"] = (
                    cur.fetchone()[0]
                )

                print(
                    "Test table created:",
                    checks["Allowed CREATE TABLE"]
                )

                # 13–15. Заборонене створення таблиць

                print("\n=== FORBIDDEN CREATE TABLE ===")

                for schema_name in [
                    "auth",
                    "progress",
                    "public"
                ]:

                    print(
                        f"\nTesting CREATE TABLE "
                        f"in {schema_name}"
                    )

                    forbidden_query = sql.SQL("""
                        CREATE TABLE {}.{} (
                            id INTEGER PRIMARY KEY
                        )
                    """).format(
                        sql.Identifier(schema_name),
                        sql.Identifier(test_table_name)
                    )

                    result = execute_expected_error(
                        cursor=cur,
                        query=forbidden_query,
                        params=(),
                        expected_error=(
                            errors.InsufficientPrivilege
                        )
                    )

                    checks[
                        f"Forbidden CREATE in {schema_name}"
                    ] = result

                    print(
                        "Result:",
                        "PASS" if result else "FAIL"
                    )

                # 16. Повний відкат усіх змін

                print("\n=== ROLLBACK ===")

                conn.rollback()

                final_counts = get_record_counts(cur)
                final_tables = get_table_names(cur)

                counts_restored = (
                    final_counts == initial_counts
                )

                tables_restored = (
                    final_tables == initial_tables
                )

                checks["Initial database state restored"] = (
                    counts_restored
                    and tables_restored
                )

                print(
                    "Record counts restored:",
                    counts_restored
                )

                print(
                    "Table list restored:",
                    tables_restored
                )

                for table_name in tables:

                    print(
                        f"{table_name}: "
                        f"initial={initial_counts[table_name]}, "
                        f"final={final_counts[table_name]}"
                    )

                # Підсумки тестування

                print("\n=== FINAL SCHEMA ISOLATION VALIDATION ===")

                for name, result in checks.items():

                    print(
                        f"{name}: "
                        f"{'PASS' if result else 'FAIL'}"
                    )

                full_match = (
                    len(checks) == 16
                    and all(checks.values())
                )

                print("\nTotal checks:", len(checks))

                print(
                    "Passed checks:",
                    sum(checks.values())
                )

                print(
                    "Failed checks:",
                    sum(
                        not result
                        for result in checks.values()
                    )
                )

                print(
                    "Failed scenarios:",
                    [
                        name for name, result
                        in checks.items()
                        if not result
                    ]
                )

                print(
                    "Full schema isolation validation:",
                    full_match
                )

                if not full_match:
                    raise AssertionError(
                        "Schema isolation validation failed"
                    )

            finally:
                conn.rollback()

    print("Connection closed")
    print("=== SCHEMA ISOLATION TEST COMPLETED ===")

if __name__ == "__main__":
    test_transactions()
    test_valid_records()
    test_not_null_and_primary_keys()
    test_check_constraints()
    test_foreign_keys()
    test_unique_constraints()
    test_delete_rules()
    test_schema_isolation()