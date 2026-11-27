-- StudyPlanner
-- Study Plan Service
-- Практична робота № 3
-- Початкова структура бази даних


-- 1. Навчальні дисципліни

CREATE TABLE study_plan.subjects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    short_name VARCHAR(50),
    description TEXT,
    academic_year VARCHAR(9),
    semester SMALLINT,
    assessment_type VARCHAR(30),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 2. Навчальні плани

CREATE TABLE study_plan.study_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    plan_type VARCHAR(30) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 3. Зв'язки навчальних планів із дисциплінами

CREATE TABLE study_plan.study_plan_subjects (
    plan_id UUID NOT NULL,
    subject_id UUID NOT NULL,

    PRIMARY KEY (plan_id, subject_id)
);


-- 4. Конфігурація типів навчальних занять

CREATE TABLE study_plan.subject_class_types (
    subject_id UUID NOT NULL,
    class_type VARCHAR(50) NOT NULL,
    total_classes SMALLINT,

    PRIMARY KEY (subject_id, class_type)
);


-- 5. Навчальні модулі

CREATE TABLE study_plan.study_modules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL,
    subject_id UUID,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    position SMALLINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 6. Навчальні завдання

CREATE TABLE study_plan.study_tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    subject_id UUID,
    plan_id UUID,
    module_id UUID,
    task_type VARCHAR(50) NOT NULL,
    task_number SMALLINT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 7. Навчальний розклад

CREATE TABLE study_plan.scheduled_classes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subject_id UUID NOT NULL,
    class_type VARCHAR(50) NOT NULL,
    class_number SMALLINT,
    education_format VARCHAR(20),
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    teacher VARCHAR(255),
    classroom VARCHAR(100),
    meeting_url TEXT,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 8. Особисті навчальні сесії

CREATE TABLE study_plan.study_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    subject_id UUID,
    plan_id UUID,
    task_id UUID,
    session_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- 9. Важливі навчальні події

CREATE TABLE study_plan.important_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    subject_id UUID,
    plan_id UUID,
    task_id UUID,
    class_id UUID,
    event_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    event_date DATE,
    start_at TIMESTAMPTZ,
    end_at TIMESTAMPTZ,
    event_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- =========================================================
-- ЗОВНІШНІ КЛЮЧІ
-- =========================================================


-- 10. Зв'язки навчальних планів із дисциплінами

ALTER TABLE study_plan.study_plan_subjects
    ADD CONSTRAINT fk_plan_subjects_plan
        FOREIGN KEY (plan_id)
        REFERENCES study_plan.study_plans (id)
        ON DELETE CASCADE,

    ADD CONSTRAINT fk_plan_subjects_subject
        FOREIGN KEY (subject_id)
        REFERENCES study_plan.subjects (id)
        ON DELETE CASCADE;


-- 11. Конфігурація типів навчальних занять

ALTER TABLE study_plan.subject_class_types
    ADD CONSTRAINT fk_subject_class_types_subject
        FOREIGN KEY (subject_id)
        REFERENCES study_plan.subjects (id)
        ON DELETE CASCADE;


-- 12. Навчальні модулі

ALTER TABLE study_plan.study_modules
    ADD CONSTRAINT fk_modules_plan
        FOREIGN KEY (plan_id)
        REFERENCES study_plan.study_plans (id)
        ON DELETE RESTRICT,

    ADD CONSTRAINT fk_modules_plan_subject
        FOREIGN KEY (plan_id, subject_id)
        REFERENCES study_plan.study_plan_subjects (plan_id, subject_id)
        MATCH SIMPLE
        ON DELETE RESTRICT;


-- 13. Навчальні завдання

ALTER TABLE study_plan.study_tasks
    ADD CONSTRAINT fk_tasks_subject
        FOREIGN KEY (subject_id)
        REFERENCES study_plan.subjects (id)
        ON DELETE RESTRICT,

    ADD CONSTRAINT fk_tasks_plan
        FOREIGN KEY (plan_id)
        REFERENCES study_plan.study_plans (id)
        ON DELETE SET NULL,

    ADD CONSTRAINT fk_tasks_module
        FOREIGN KEY (module_id)
        REFERENCES study_plan.study_modules (id)
        ON DELETE RESTRICT,

    ADD CONSTRAINT fk_tasks_plan_subject
        FOREIGN KEY (plan_id, subject_id)
        REFERENCES study_plan.study_plan_subjects (plan_id, subject_id)
        MATCH SIMPLE
        ON DELETE NO ACTION;


-- 14. Навчальний розклад

ALTER TABLE study_plan.scheduled_classes
    ADD CONSTRAINT fk_classes_subject_type
        FOREIGN KEY (subject_id, class_type)
        REFERENCES study_plan.subject_class_types (subject_id, class_type)
        ON DELETE RESTRICT;


-- 15. Особисті навчальні сесії

ALTER TABLE study_plan.study_sessions
    ADD CONSTRAINT fk_sessions_subject
        FOREIGN KEY (subject_id)
        REFERENCES study_plan.subjects (id)
        ON DELETE RESTRICT,

    ADD CONSTRAINT fk_sessions_plan
        FOREIGN KEY (plan_id)
        REFERENCES study_plan.study_plans (id)
        ON DELETE SET NULL,

    ADD CONSTRAINT fk_sessions_task
        FOREIGN KEY (task_id)
        REFERENCES study_plan.study_tasks (id)
        ON DELETE RESTRICT,

    ADD CONSTRAINT fk_sessions_plan_subject
        FOREIGN KEY (plan_id, subject_id)
        REFERENCES study_plan.study_plan_subjects (plan_id, subject_id)
        MATCH SIMPLE
        ON DELETE NO ACTION;


-- 16. Важливі навчальні події

ALTER TABLE study_plan.important_events
    ADD CONSTRAINT fk_events_subject
        FOREIGN KEY (subject_id)
        REFERENCES study_plan.subjects (id)
        ON DELETE RESTRICT,

    ADD CONSTRAINT fk_events_plan
        FOREIGN KEY (plan_id)
        REFERENCES study_plan.study_plans (id)
        ON DELETE SET NULL,

    ADD CONSTRAINT fk_events_task
        FOREIGN KEY (task_id)
        REFERENCES study_plan.study_tasks (id)
        ON DELETE RESTRICT,

    ADD CONSTRAINT fk_events_class
        FOREIGN KEY (class_id)
        REFERENCES study_plan.scheduled_classes (id)
        ON DELETE RESTRICT,

    ADD CONSTRAINT fk_events_plan_subject
        FOREIGN KEY (plan_id, subject_id)
        REFERENCES study_plan.study_plan_subjects (plan_id, subject_id)
        MATCH SIMPLE
        ON DELETE NO ACTION;
-- =========================================================
-- CHECK-ОБМЕЖЕННЯ
-- =========================================================


-- 17. Навчальні дисципліни

ALTER TABLE study_plan.subjects
    ADD CONSTRAINT chk_subjects_name
        CHECK (name ~ '[^[:space:]]'),

    ADD CONSTRAINT chk_subjects_short_name
        CHECK (
            short_name IS NULL
            OR short_name ~ '[^[:space:]]'
        ),

    ADD CONSTRAINT chk_subjects_academic_year
        CHECK (
            CASE
                WHEN academic_year IS NULL THEN TRUE
                WHEN academic_year ~ '^[0-9]{4}/[0-9]{4}$'
                THEN
                    CAST(LEFT(academic_year, 4) AS INTEGER) >= 1
                    AND CAST(RIGHT(academic_year, 4) AS INTEGER)
                        = CAST(LEFT(academic_year, 4) AS INTEGER) + 1
                ELSE FALSE
            END
        ),

    ADD CONSTRAINT chk_subjects_semester
        CHECK (semester IS NULL OR semester > 0),

    ADD CONSTRAINT chk_subjects_assessment_type
        CHECK (
            assessment_type IS NULL
            OR assessment_type IN (
                'credit',
                'exam',
                'graded_credit',
                'other'
            )
        );


-- 18. Навчальні плани

ALTER TABLE study_plan.study_plans
    ADD CONSTRAINT chk_plans_title
        CHECK (title ~ '[^[:space:]]'),

    ADD CONSTRAINT chk_plans_type
        CHECK (
            plan_type IN (
                'academic',
                'exam_preparation',
                'personal',
                'course',
                'project',
                'other'
            )
        ),

    ADD CONSTRAINT chk_plans_dates
        CHECK (
            start_date IS NULL
            OR end_date IS NULL
            OR end_date >= start_date
        );


-- 19. Конфігурація типів навчальних занять

ALTER TABLE study_plan.subject_class_types
    ADD CONSTRAINT chk_subject_class_types_type
        CHECK (
            class_type IN (
                'lecture',
                'practical',
                'laboratory',
                'consultation',
                'credit',
                'exam',
                'coursework',
                'other'
            )
        ),

    ADD CONSTRAINT chk_subject_class_types_total
        CHECK (
            total_classes IS NULL
            OR total_classes > 0
        );


-- 20. Навчальні модулі

ALTER TABLE study_plan.study_modules
    ADD CONSTRAINT chk_modules_title
        CHECK (title ~ '[^[:space:]]'),

    ADD CONSTRAINT chk_modules_position
        CHECK (position > 0),

    ADD CONSTRAINT uq_modules_position
        UNIQUE NULLS NOT DISTINCT (
            plan_id,
            subject_id,
            position
        )
        DEFERRABLE INITIALLY DEFERRED;


-- 21. Навчальні завдання

ALTER TABLE study_plan.study_tasks
    ADD CONSTRAINT chk_tasks_title
        CHECK (title ~ '[^[:space:]]'),

    ADD CONSTRAINT chk_tasks_type
        CHECK (
            task_type IN (
                'practical_work',
                'laboratory_work',
                'independent_work',
                'homework',
                'individual_task',
                'test_work',
                'course_paper',
                'course_project',
                'essay',
                'presentation',
                'other'
            )
        ),

    ADD CONSTRAINT chk_tasks_number
        CHECK (
            task_number IS NULL
            OR task_number > 0
        ),

    ADD CONSTRAINT chk_tasks_module_plan
        CHECK (
            module_id IS NULL
            OR plan_id IS NULL
        );


-- 22. Навчальний розклад

ALTER TABLE study_plan.scheduled_classes
    ADD CONSTRAINT chk_classes_type
        CHECK (
            class_type IN (
                'lecture',
                'practical',
                'laboratory',
                'consultation',
                'credit',
                'exam',
                'coursework',
                'other'
            )
        ),

    ADD CONSTRAINT chk_classes_education_format
        CHECK (
            education_format IS NULL
            OR education_format IN (
                'offline',
                'online',
                'hybrid'
            )
        ),

    ADD CONSTRAINT chk_classes_number
        CHECK (
            class_number IS NULL
            OR class_number > 0
        ),

    ADD CONSTRAINT chk_classes_time
        CHECK (end_at > start_at);


-- 23. Особисті навчальні сесії

ALTER TABLE study_plan.study_sessions
    ADD CONSTRAINT chk_sessions_title
        CHECK (title ~ '[^[:space:]]'),

    ADD CONSTRAINT chk_sessions_type
        CHECK (
            session_type IN (
                'self_study',
                'exam_preparation',
                'credit_preparation',
                'assignment_work',
                'defense_preparation',
                'report_preparation',
                'presentation_preparation',
                'test_preparation',
                'revision',
                'reading',
                'other'
            )
        ),

    ADD CONSTRAINT chk_sessions_time
        CHECK (end_at > start_at),

    ADD CONSTRAINT chk_sessions_task_context
        CHECK (
            task_id IS NULL
            OR (
                subject_id IS NULL
                AND plan_id IS NULL
            )
        );


-- 24. Важливі навчальні події

ALTER TABLE study_plan.important_events
    ADD CONSTRAINT chk_events_title
        CHECK (title ~ '[^[:space:]]'),

    ADD CONSTRAINT chk_events_type
        CHECK (
            event_type IN (
                'deadline',
                'submission',
                'defense',
                'exam',
                'credit',
                'test',
                'retake',
                'module_test',
                'other'
            )
        ),

    ADD CONSTRAINT chk_events_time_source
        CHECK (
            (
                class_id IS NULL
                AND event_date IS NOT NULL
                AND start_at IS NULL
                AND end_at IS NULL
            )
            OR
            (
                class_id IS NULL
                AND event_date IS NULL
                AND start_at IS NOT NULL
                AND (
                    end_at IS NULL
                    OR end_at > start_at
                )
            )
            OR
            (
                class_id IS NOT NULL
                AND event_date IS NULL
                AND start_at IS NULL
                AND end_at IS NULL
            )
        ),

    ADD CONSTRAINT chk_events_deadline
        CHECK (
            event_type <> 'deadline'
            OR (
                class_id IS NULL
                AND end_at IS NULL
            )
        ),

    ADD CONSTRAINT chk_events_class_subject
        CHECK (
            class_id IS NULL
            OR subject_id IS NULL
        ),

    ADD CONSTRAINT chk_events_task_plan
        CHECK (
            task_id IS NULL
            OR plan_id IS NULL
        );


-- =========================================================
-- ІНДЕКСИ
-- =========================================================


-- 25. Навчальні дисципліни

CREATE INDEX idx_subjects_user
    ON study_plan.subjects (user_id);


-- 26. Навчальні плани

CREATE INDEX idx_plans_user_type
    ON study_plan.study_plans (user_id, plan_type);

CREATE INDEX idx_plans_user_updated
    ON study_plan.study_plans (user_id, updated_at);


-- 27. Зв'язки навчальних планів із дисциплінами

CREATE INDEX idx_plan_subjects_subject
    ON study_plan.study_plan_subjects (subject_id);


-- 28. Навчальні модулі

CREATE INDEX idx_modules_plan_position
    ON study_plan.study_modules (plan_id, position);

CREATE INDEX idx_modules_subject
    ON study_plan.study_modules (subject_id);


-- 29. Навчальні завдання

CREATE INDEX idx_tasks_user_updated
    ON study_plan.study_tasks (user_id, updated_at);

CREATE INDEX idx_tasks_subject
    ON study_plan.study_tasks (subject_id);

CREATE INDEX idx_tasks_plan
    ON study_plan.study_tasks (plan_id);

CREATE INDEX idx_tasks_module
    ON study_plan.study_tasks (module_id);


-- 30. Навчальний розклад

CREATE INDEX idx_classes_subject_start
    ON study_plan.scheduled_classes (subject_id, start_at);

CREATE INDEX idx_classes_subject_type
    ON study_plan.scheduled_classes (subject_id, class_type);


-- 31. Особисті навчальні сесії

CREATE INDEX idx_sessions_user_start
    ON study_plan.study_sessions (user_id, start_at);

CREATE INDEX idx_sessions_subject
    ON study_plan.study_sessions (subject_id);

CREATE INDEX idx_sessions_plan
    ON study_plan.study_sessions (plan_id);

CREATE INDEX idx_sessions_task
    ON study_plan.study_sessions (task_id);


-- 32. Важливі навчальні події

CREATE INDEX idx_events_user_date
    ON study_plan.important_events (user_id, event_date);

CREATE INDEX idx_events_user_start
    ON study_plan.important_events (user_id, start_at);

CREATE INDEX idx_events_subject
    ON study_plan.important_events (subject_id);

CREATE INDEX idx_events_plan
    ON study_plan.important_events (plan_id);

CREATE INDEX idx_events_task_type
    ON study_plan.important_events (task_id, event_type);

CREATE INDEX idx_events_class
    ON study_plan.important_events (class_id);