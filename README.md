# StudyPlanner Microservices

## Опис проєкту

StudyPlanner — вебсистема планування навчання та навчальних сесій із можливістю ділитися успіхами з батьками, колегами та друзями.

Проєкт розробляється в межах дисципліни «Мікросервісна архітектура та розподілені системи».

## Основні компоненти

- **Auth Service** — автентифікація та авторизація користувачів.
- **Study Plan Service** — управління навчальними планами, заняттями, сесіями та дедлайнами.
- **Progress Service** — відстеження навчального прогресу.
- **Frontend** — вебінтерфейс користувача.
- **Infrastructure** — конфігурація бази даних, брокера повідомлень, моніторингу та контейнеризації.

## Технології

- Python, FastAPI
- React (запланований вебінтерфейс)
- PostgreSQL 17
- RabbitMQ
- Prometheus
- Grafana
- Docker, Docker Compose
- Git, GitHub

## Структура проєкту

```text
StudyPlanner-Microservices/
├── auth-service/
├── study-plan-service/
│   ├── Dockerfile
│   ├── main.py
│   ├── database.py
│   ├── rabbitmq.py
│   ├── test_rabbitmq.py
│   └── requirements.txt
├── progress-service/
├── frontend/
├── infrastructure/
│   ├── postgres/
│   │   └── init/
│   │       ├── 01-create-schemas.sql
│   │       └── 02-create-users.sh
│   └── prometheus/
│       └── prometheus.yml
├── compose.yaml
├── .env.example
├── .gitignore
├── .gitattributes
└── README.md
```

## Підготовка до запуску

Для запуску необхідно встановити Git та Docker Desktop із підтримкою Docker Compose.

1. Завантажити репозиторій із GitHub.
2. Перейти до папки проєкту.
3. Створити файл `.env` на основі `.env.example`.
4. Заповнити у `.env` паролі PostgreSQL, RabbitMQ і Grafana.
5. Запустити Docker Desktop.

Файл `.env` містить конфіденційні налаштування та не повинен завантажуватися на GitHub.

## Запуск проєкту

У терміналі, відкритому в кореневій папці проєкту, виконати:

```bash
docker compose config --quiet
docker compose up -d --build
```

Перевірити запущені контейнери:

```bash
docker compose ps
```

## Доступ до сервісів

| Компонент | Адреса |
|---|---|
| Auth Service | http://127.0.0.1:8000 |
| Study Plan Service | http://127.0.0.1:8001 |
| Progress Service | http://127.0.0.1:8002 |
| Study Plan Service — перевірка БД | http://127.0.0.1:8001/db-check |
| Study Plan Service — метрики | http://127.0.0.1:8001/metrics |
| RabbitMQ Management | http://127.0.0.1:15672 |
| Prometheus | http://127.0.0.1:9090 |
| Grafana | http://127.0.0.1:3000 |

PostgreSQL доступний мікросервісам у внутрішній Docker-мережі та не публікує порт на комп'ютері користувача.

## PostgreSQL

Система використовує базу даних `studyplanner` із трьома окремими схемами:

- `auth` — для Auth Service.
- `study_plan` — для Study Plan Service.
- `progress` — для Progress Service.

Для кожного сервісу передбачена окрема роль бази даних.

Під час першого запуску з порожнім Docker-томом PostgreSQL автоматично виконує скрипти з папки `infrastructure/postgres/init`.

## RabbitMQ

RabbitMQ використовується для асинхронного обміну повідомленнями між мікросервісами.

Для перевірки тестового обміну повідомленнями Study Plan Service можна виконати:

```bash
docker compose exec study-plan-service python test_rabbitmq.py
```

Тест надсилає повідомлення до RabbitMQ та перевіряє його отримання.

## Моніторинг

Prometheus використовується для збирання метрик, а Grafana — для їх візуалізації.

Для Study Plan Service налаштовано збирання метрик через маршрут `/metrics`.

Створено Dashboard `StudyPlanner — Monitoring` із трьома показниками:

- **Availability** — доступність мікросервісу.
- **HTTP Requests** — кількість HTTP-запитів за секунду.
- **Request Duration** — середній час обробки HTTP-запитів.

Dashboard наразі створено вручну. Його автоматичне розгортання для інших учасників команди ще потрібно налаштувати.

## Зупинка проєкту

Зупинити контейнери можна командою:

```bash
docker compose down
```

Для повторного запуску:

```bash
docker compose up -d
```

Не використовуйте `docker compose down -v` без необхідності, оскільки параметр `-v` видаляє Docker-томи зі збереженими даними.

## Git-гілки

- `main` — основна гілка проєкту.
- `feature/infrastructure` — налаштування загальної інфраструктури.
- `feature/auth-service` — розробка Auth Service.
- `feature/study-plan-service` — розробка Study Plan Service.
- `feature/progress-service` — розробка Progress Service.
- `integration/studyplanner` — інтеграція та перевірка компонентів системи.

## Поточний стан

На поточному етапі реалізовано та перевірено:

- запуск семи контейнерів через Docker Compose;
- автоматичне створення схем і ролей PostgreSQL;
- підключення Study Plan Service до PostgreSQL;
- тестовий обмін повідомленнями через RabbitMQ;
- збирання метрик Prometheus;
- відображення показників у Grafana.

Повна бізнес-логіка мікросервісів, їхня взаємодія та вебінтерфейс перебувають на наступних етапах розробки.