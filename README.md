
# StudyPlanner Microservices

## 1. Опис проєкту

StudyPlanner — вебсистема планування навчання та навчальних сесій із можливістю ділитися успіхами з батьками, колегами та друзями.

Проєкт розробляється в межах дисципліни «Мікросервісна архітектура та розподілені системи».

Архітектура системи базується на мікросервісному підході з урахуванням таких принципів проєктування:

- High Coherence — висока внутрішня зв'язність компонентів сервісу;
- Low Coupling — низька взаємна залежність мікросервісів;
- Secure-by-Design — врахування вимог безпеки на етапі проєктування.

Інфраструктура системи розгортається за допомогою Docker Compose.

## 2. Основні компоненти системи

| Компонент | Призначення |
|---|---|
| Auth Service | Автентифікація та авторизація користувачів, управління профілями та ролями |
| Study Plan Service | Управління навчальними планами, сесіями, заняттями та важливими подіями |
| Progress Service | Відстеження навчального прогресу, виконаних завдань та їхніх статусів |
| Frontend | Єдиний користувацький вебінтерфейс |
| PostgreSQL | Зберігання даних мікросервісів |
| RabbitMQ | Асинхронний обмін повідомленнями |
| Prometheus | Збирання та зберігання метрик |
| Grafana | Візуалізація метрик та моніторинг |
| Docker Compose | Конфігурування та розгортання інфраструктури |

На поточному етапі реалізовано програмну основу мікросервісів та інфраструктуру системи. Повна бізнес-логіка та вебінтерфейс належать до наступних етапів розробки.

## 3. Технологічний стек

### Серверна частина

- Python 3.12;
- FastAPI;
- Uvicorn;
- SQLAlchemy;
- psycopg;
- pika;
- prometheus-fastapi-instrumentator;
- REST API;
- JSON.

### Клієнтська частина

- ReactJS — запроєктований вебінтерфейс.

### Інфраструктура

| Технологія | Перевірена версія |
|---|---|
| PostgreSQL | 17.11 |
| RabbitMQ | 4.4.0 |
| Erlang | 29.1.2 |
| Prometheus | 3.16.0 |
| Grafana | 13.3.1 |
| Docker Engine | 29.9.3 |
| Docker Compose | 5.7.0 |
| Git | 2.54.0 |

Наведені версії зафіксовано під час тестування інфраструктури 24.11.2026. Фактичні версії можуть відрізнятися під час наступних розгортань, оскільки частина Docker-образів використовує плаваючі теги.

## 4. Структура проєкту

```text
StudyPlanner-Microservices/
├── auth-service/
│   ├── database.py
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── study-plan-service/
│   ├── database.py
│   ├── Dockerfile
│   ├── main.py
│   ├── rabbitmq.py
│   ├── requirements.txt
│   └── test_rabbitmq.py
├── progress-service/
│   ├── database.py
│   ├── Dockerfile
│   ├── main.py
│   ├── rabbitmq.py
│   ├── requirements.txt
│   └── test_rabbitmq.py
├── frontend/
├── infrastructure/
│   ├── postgres/
│   │   └── init/
│   │       ├── 01-create-schemas.sql
│   │       └── 02-create-users.sh
│   ├── prometheus/
│   │   └── prometheus.yml
│   └── grafana/
│       ├── dashboards/
│       │   ├── auth-service-dashboard.json
│       │   ├── study-plan-service-dashboard.json
│       │   └── progress-service-dashboard.json
│       └── provisioning/
│           ├── dashboards/
│           │   └── dashboards.yml
│           └── datasources/
│               └── datasources.yml
├── compose.yaml
├── .env.example
├── .gitignore
├── .gitattributes
└── README.md
```

Локальні резервні копії, конфіденційні файли та службові директорії Git у структурі не наведено.

## 5. Підготовка середовища розробки

Для запуску проєкту необхідно встановити:

- Git;
- Docker Desktop із підтримкою Docker Compose;
- Visual Studio Code або інший редактор програмного коду.

Для Windows рекомендовано використовувати Docker Desktop із WSL 2.

Перевірка встановлених інструментів:

```cmd
git --version
docker --version
docker compose version
```

## 6. Завантаження проєкту

Клонувати репозиторій:

```cmd
git clone https://github.com/daria-hlyha/StudyPlanner-Microservices.git
```

Перейти до директорії проєкту:

```cmd
cd StudyPlanner-Microservices
```

Відкрити проєкт у Visual Studio Code:

```cmd
code .
```

## 7. Налаштування змінних середовища

Створити файл `.env` на основі `.env.example`, якщо файл `.env` ще не існує:

```cmd
if not exist .env copy .env.example .env
```

Відкрити файл:

```cmd
code .env
```

У файлі необхідно встановити власні значення паролів та облікових даних.

| Змінна | Призначення |
|---|---|
| POSTGRES_DB | Назва бази даних |
| POSTGRES_USER | Адміністративний користувач PostgreSQL |
| POSTGRES_PASSWORD | Пароль адміністративного користувача |
| AUTH_DB_PASSWORD | Пароль користувача Auth Service |
| STUDY_PLAN_DB_PASSWORD | Пароль користувача Study Plan Service |
| PROGRESS_DB_PASSWORD | Пароль користувача Progress Service |
| RABBITMQ_USER | Користувач RabbitMQ |
| RABBITMQ_PASSWORD | Пароль RabbitMQ |
| GRAFANA_ADMIN_USER | Адміністратор Grafana |
| GRAFANA_ADMIN_PASSWORD | Пароль адміністратора Grafana |

Файл `.env` містить конфіденційні налаштування та не повинен завантажуватися до GitHub.

Файл `.env.example` є шаблоном і не містить фактичних паролів.

Зміна паролів у `.env` після першої ініціалізації постійних сховищ не змінює автоматично вже створені облікові записи.

## 8. Запуск проєкту

Запустити Docker Desktop.

Перевірити конфігурацію Docker Compose:

```cmd
docker compose config --quiet
```

Переглянути перелік компонентів:

```cmd
docker compose config --services
```

Створити Docker-образи та запустити інфраструктуру:

```cmd
docker compose up -d --build
```

Перевірити стан контейнерів:

```cmd
docker compose ps
```

До складу інфраструктури входять сім контейнерів:

- auth-service;
- study-plan-service;
- progress-service;
- postgres;
- rabbitmq;
- prometheus;
- grafana.

Після успішного запуску п'ять контейнерів із налаштованим Healthcheck повинні отримати статус `healthy`, а Prometheus і Grafana — статус `Up`.

## 9. Доступ до компонентів системи

| Компонент | Адреса |
|---|---|
| Auth Service | http://127.0.0.1:8000 |
| Study Plan Service | http://127.0.0.1:8001 |
| Progress Service | http://127.0.0.1:8002 |
| Auth Service — Swagger UI | http://127.0.0.1:8000/docs |
| Study Plan Service — Swagger UI | http://127.0.0.1:8001/docs |
| Progress Service — Swagger UI | http://127.0.0.1:8002/docs |
| RabbitMQ Management | http://127.0.0.1:15672 |
| Prometheus | http://127.0.0.1:9090 |
| Grafana | http://127.0.0.1:3000 |

### Внутрішні мережеві адреси

| Компонент | Адреса всередині Docker |
|---|---|
| Auth Service | auth-service:8000 |
| Study Plan Service | study-plan-service:8000 |
| Progress Service | progress-service:8000 |
| PostgreSQL | postgres:5432 |
| RabbitMQ | rabbitmq:5672 |
| RabbitMQ Management | rabbitmq:15672 |
| Prometheus | prometheus:9090 |
| Grafana | grafana:3000 |

Усі контейнери взаємодіють через внутрішню мережу Docker Compose.

PostgreSQL та AMQP-порт RabbitMQ не публікуються на комп'ютері користувача.

## 10. REST API мікросервісів

На поточному етапі реалізовано діагностичні маршрути для перевірки працездатності компонентів.

| Метод | Маршрут | Auth | Study Plan | Progress |
|---|---|---|---|---|
| GET | / | Так | Так | Так |
| GET | /db-check | Так | Так | Так |
| GET | /rabbitmq-check | Ні | Так | Так |
| GET | /metrics | Так | Так | Так |
| GET | /docs | Так | Так | Так |
| GET | /redoc | Так | Так | Так |
| GET | /openapi.json | Так | Так | Так |

Призначення маршрутів:

- `/` — перевірка доступності мікросервісу;
- `/db-check` — перевірка підключення до PostgreSQL;
- `/rabbitmq-check` — перевірка підключення до RabbitMQ;
- `/metrics` — надання метрик для Prometheus;
- `/docs` — інтерактивна документація Swagger UI;
- `/redoc` — альтернативна документація API;
- `/openapi.json` — специфікація OpenAPI.

Успішна діагностична перевірка повертає HTTP 200 OK. Оброблені помилки підключення до компонентів інфраструктури повертають HTTP 503 Service Unavailable.

## 11. PostgreSQL

Система використовує один сервер PostgreSQL із базою даних `studyplanner`.

Для забезпечення ізоляції даних кожен мікросервіс використовує окрему схему та окрему роль PostgreSQL.

| Мікросервіс | Схема | Користувач PostgreSQL |
|---|---|---|
| Auth Service | auth | auth_user |
| Study Plan Service | study_plan | study_plan_user |
| Progress Service | progress | progress_user |

### 11.1. Ініціалізація бази даних

Під час першого запуску з порожнім Docker-томом PostgreSQL автоматично виконує скрипти з директорії:

```text
infrastructure/postgres/init/
```

Призначення скриптів:

- `01-create-schemas.sql` — створення окремих схем;
- `02-create-users.sh` — створення ролей, налаштування прав доступу та схем за замовчуванням.

### 11.2. Розмежування прав доступу

Кожному користувачу надаються права `USAGE` та `CREATE` для власної схеми.

| Користувач | auth | study_plan | progress |
|---|---|---|---|
| auth_user | Дозволено | Заборонено | Заборонено |
| study_plan_user | Заборонено | Дозволено | Заборонено |
| progress_user | Заборонено | Заборонено | Дозволено |

Матриця відображає права USAGE та CREATE для трьох предметних схем.

Користувачі мікросервісів не мають прав суперкористувача, створення баз даних або створення інших ролей.

Параметр `search_path` забезпечує вибір відповідної схеми за замовчуванням.

### 11.3. Перевірка підключення

```cmd
curl http://localhost:8000/db-check
curl http://localhost:8001/db-check
curl http://localhost:8002/db-check
```

Приклад відповіді Study Plan Service:

```json
{
  "status": "connected",
  "user": "study_plan_user",
  "database": "studyplanner",
  "current_schema": "study_plan"
}
```

### 11.4. Оновлення наявної бази даних

Скрипти ініціалізації PostgreSQL виконуються лише під час першого створення бази даних у порожньому сховищі.

Для застосування оновленого search_path до вже створеної бази даних необхідно відкрити консоль PostgreSQL:

```cmd
docker compose exec postgres sh -c "psql -U $POSTGRES_USER -d $POSTGRES_DB -v ON_ERROR_STOP=1"
```

Виконати:

```sql
ALTER ROLE auth_user SET search_path TO auth;
ALTER ROLE study_plan_user SET search_path TO study_plan;
ALTER ROLE progress_user SET search_path TO progress;
```

Вийти з консолі:

```text
\q
```

Перезапустити мікросервіси:

```cmd
docker compose restart auth-service study-plan-service progress-service
```

### 11.5. Поточний стан

Реалізовано інфраструктуру зберігання даних, створення схем і ролей, розмежування прав та підключення мікросервісів до PostgreSQL.

Створення предметних таблиць і реалізація операцій над навчальними даними належать до наступних етапів розробки.

## 12. RabbitMQ

RabbitMQ призначений для асинхронного обміну повідомленнями між мікросервісами.

Для Study Plan Service та Progress Service реалізовано програмні модулі підключення до брокера повідомлень із використанням бібліотеки pika.

### 12.1. Перевірка доступності RabbitMQ

```cmd
docker compose exec rabbitmq rabbitmq-diagnostics -q ping
```

Перевірка підключення мікросервісів:

```cmd
curl http://localhost:8001/rabbitmq-check
curl http://localhost:8002/rabbitmq-check
```

Очікувана відповідь:

```json
{"status":"connected"}
```

### 12.2. Тестування повідомлень

Тестування Study Plan Service:

```cmd
docker compose exec study-plan-service python test_rabbitmq.py
```

Очікуваний результат:

```text
Sent: Study Plan Service test message
Received: Study Plan Service test message
```

Тестування Progress Service:

```cmd
docker compose exec progress-service python test_rabbitmq.py
```

Очікуваний результат:

```text
Sent: Progress Service test message
Received: Progress Service test message
```

### 12.3. Тестові черги

| Черга | Мікросервіс | Тип |
|---|---|---|
| study_plan_test | Study Plan Service | Classic, Durable |
| progress_test | Progress Service | Classic, Durable |

Перевірка стану черг:

```cmd
docker compose exec rabbitmq rabbitmqctl list_queues name durable messages_ready messages_unacknowledged
```

Тестові скрипти перевіряють надсилання та отримання повідомлень через власні тестові черги.

Повноцінний обмін бізнес-подіями між мікросервісами належить до наступних етапів розробки.


### 12.4. Збереження даних RabbitMQ

Для контейнера RabbitMQ у файлі `compose.yaml` встановлено постійне ім'я хоста:

```yaml
hostname: rabbitmq
```

Це забезпечує стабільне ім'я вузла RabbitMQ та використання відповідної директорії даних у постійному сховищі `rabbitmq_data` після перестворення контейнера.

Для перевірки збереження тестових черг використовується команда:

```cmd
docker compose up -d --force-recreate rabbitmq
```

Після завершення запуску брокера виконується перевірка:

```cmd
docker compose exec rabbitmq rabbitmqctl list_queues name durable messages_ready messages_unacknowledged
```

Під час тестування підтверджено збереження черг `study_plan_test` та `progress_test` після перестворення контейнера RabbitMQ.


## 13. Моніторинг системи

Для моніторингу мікросервісів використовуються Prometheus та Grafana.

### 13.1. Prometheus

Prometheus збирає метрики через маршрут `/metrics`.

Конфігурація зберігається у файлі:

```text
infrastructure/prometheus/prometheus.yml
```

Налаштовано чотири джерела метрик:

| Джерело | Адреса |
|---|---|
| Auth Service | auth-service:8000 |
| Study Plan Service | study-plan-service:8000 |
| Progress Service | progress-service:8000 |
| Prometheus | localhost:9090 |

Інтервал збирання метрик становить 15 секунд.

Перевірка готовності Prometheus:

```cmd
curl http://localhost:9090/-/healthy
curl http://localhost:9090/-/ready
```

Перевірка джерел метрик:

http://localhost:9090/targets

Для перевірки доступності джерел використовується запит PromQL:

```promql
up
```

Значення `1` означає успішне отримання метрик, а `0` — невдалу спробу їх отримання.

Для перегляду кількості HTTP-запитів використовується метрика:

```promql
http_requests_total
```

### 13.2. Grafana

Grafana використовується для графічного відображення метрик, отриманих із Prometheus.

Адреса джерела даних у внутрішній мережі Docker:

```text
http://prometheus:9090
```

Для кожного мікросервісу створено окрему інформаційну панель:

- StudyPlanner — Auth Service;
- StudyPlanner — Study Plan Service;
- StudyPlanner — Progress Service.

Кожна панель містить три показники:

| Показник | Призначення |
|---|---|
| Availability | Доступність джерела метрик |
| HTTP Requests | Середня інтенсивність HTTP-запитів за секунду |
| Request Duration | Середня тривалість обробки HTTP-запитів |

Для розрахунку інтенсивності та середньої тривалості запитів використовується п'ятихвилинне вікно.

Поточні показники включають автоматичні діагностичні запити та запити збирання метрик.

### 13.3. Автоматичне налаштування Grafana

У проєкті передбачено механізм provisioning для автоматичного налаштування джерела даних та завантаження інформаційних панелей.

Конфігураційні файли:

```text
infrastructure/grafana/provisioning/datasources/datasources.yml
infrastructure/grafana/provisioning/dashboards/dashboards.yml
```

JSON-файли інформаційних панелей:

```text
infrastructure/grafana/dashboards/auth-service-dashboard.json
infrastructure/grafana/dashboards/study-plan-service-dashboard.json
infrastructure/grafana/dashboards/progress-service-dashboard.json
```

Перевірка працездатності Grafana:

```cmd
curl http://localhost:3000/api/health
```

Працездатність трьох інформаційних панелей та їх підключення до Prometheus підтверджено в розгорнутій інфраструктурі.

## 14. Автоматична перевірка працездатності

Для п'яти компонентів інфраструктури налаштовано Healthcheck.

| Компонент | Перевірка | Інтервал |
|---|---|---|
| PostgreSQL | pg_isready | 10 секунд |
| RabbitMQ | rabbitmq-diagnostics check_port_connectivity | 10 секунд |
| Auth Service | /db-check | 30 секунд |
| Study Plan Service | /db-check, /rabbitmq-check | 30 секунд |
| Progress Service | /db-check, /rabbitmq-check | 30 секунд |

Для запуску мікросервісів використовується параметр `depends_on` з умовою `service_healthy`.

Auth Service очікує готовності PostgreSQL.

Study Plan Service та Progress Service очікують готовності PostgreSQL і RabbitMQ.

Перевірка стану контейнерів:

```cmd
docker compose ps
```

Можливі стани:

- `starting` — виконується початкова перевірка;
- `healthy` — автоматична перевірка успішна;
- `unhealthy` — автоматична перевірка не пройдена;
- `Up` — контейнер запущено.

Статус healthy підтверджує успішність налаштованих перевірок, але не гарантує відсутності всіх можливих помилок.

## 15. Постійне зберігання даних

Для збереження даних використовуються Docker Volume.

| Docker Volume | Призначення |
|---|---|
| postgres_data | Дані PostgreSQL |
| rabbitmq_data | Дані RabbitMQ |
| prometheus_data | Зібрані метрики Prometheus |
| grafana_data | Внутрішні дані та налаштування Grafana |

Docker Volume забезпечують збереження даних під час звичайної зупинки, повторного запуску та перестворення контейнерів.

## 16. Безпека інфраструктури

На поточному етапі передбачено такі механізми безпеки:

- використання окремих користувачів PostgreSQL;
- розмежування прав доступу до схем;
- обмеження адміністративних привілеїв;
- зберігання паролів у змінних середовища;
- виключення файлу `.env` із Git;
- використання внутрішньої мережі Docker;
- відсутність публікації портів PostgreSQL та AMQP;
- прив'язка опублікованих портів до локальної адреси 127.0.0.1;
- повернення узагальнених повідомлень про оброблені помилки підключення.

Механізми автентифікації, авторизації та контролю доступу до предметних даних належать до наступного етапу реалізації програмної функціональності.

## 17. Управління інфраструктурою

### Перегляд стану контейнерів

```cmd
docker compose ps
```

### Перегляд журналів роботи

```cmd
docker compose logs --tail=50
```

### Перегляд журналів окремого сервісу

```cmd
docker compose logs --tail=50 study-plan-service
```

### Перезапуск окремого сервісу

```cmd
docker compose restart study-plan-service
```

### Оновлення сервісу після зміни програмного коду

```cmd
docker compose build study-plan-service
docker compose up -d --no-deps study-plan-service
```

### Зупинка інфраструктури

```cmd
docker compose down
```

### Повторний запуск

```cmd
docker compose up -d
```

Не використовуйте `docker compose down -v` без необхідності, оскільки параметр `-v` видаляє постійні Docker-томи зі збереженими даними.

## 18. Git-гілки

| Гілка | Призначення |
|---|---|
| main | Основна гілка проєкту |
| feature/infrastructure | Розроблення загальної інфраструктури |
| feature/auth-service | Розроблення Auth Service |
| feature/study-plan-service | Розроблення Study Plan Service |
| feature/progress-service | Розроблення Progress Service |
| feature/grafana-dashboards | Розроблення інформаційних панелей моніторингу |
| integration/studyplanner | Інтеграція компонентів |
| fix/infrastructure-pz2 | Виправлення та тестування інфраструктури ПЗ № 2 |

## 19. Поточний стан проєкту

### Реалізовано та перевірено

- програмну основу трьох мікросервісів FastAPI;
- контейнеризацію мікросервісів;
- розгортання семи контейнерів через Docker Compose;
- підключення трьох мікросервісів до PostgreSQL;
- створення трьох окремих схем PostgreSQL;
- створення окремих ролей PostgreSQL;
- розмежування прав доступу до схем;
- налаштування search_path;
- підключення Study Plan Service та Progress Service до RabbitMQ;
- тестове надсилання та отримання повідомлень;
- автоматичні перевірки працездатності п'яти контейнерів;
- збирання метрик Prometheus із чотирьох джерел;
- підключення Grafana до Prometheus;
- відображення трьох інформаційних панелей Grafana;
- постійне зберігання даних у Docker Volume;
- діагностичні маршрути REST API;
- налаштування постійного імені вузла RabbitMQ;
- збереження тестових черг після перестворення контейнера RabbitMQ;
- автоматичну документацію Swagger UI.


### Налаштовано конфігураційними файлами

- автоматичну ініціалізацію PostgreSQL;
- автоматичне підключення джерела даних Grafana;
- автоматичне завантаження інформаційних панелей Grafana.

### Наступні етапи розробки

- реалізація повної бізнес-логіки мікросервісів;
- створення предметних таблиць бази даних;
- реалізація автентифікації та авторизації;
- реалізація операцій управління навчальними планами;
- реалізація відстеження навчального прогресу;
- реалізація міжсервісного обміну бізнес-подіями;
- розроблення вебінтерфейсу ReactJS;
- реалізація додаткової функціональності;
- розгортання системи за допомогою Kubernetes.

Поточна версія проєкту формує інфраструктурну та програмну основу для подальшої реалізації функціональності мікросервісної системи StudyPlanner.
