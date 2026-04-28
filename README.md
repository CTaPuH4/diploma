# CodeCheck

CodeCheck - дипломный проект для проверки учебных программных решений. Система позволяет преподавателям создавать задания с автотестами, студентам отправлять решения, а преподавателям получать результаты запуска, LLM-анализ кода и выставлять итоговую оценку.

## Возможности

- регистрация и вход пользователей по JWT;
- роли `student`, `teacher`, `admin`;
- управление учебными группами;
- создание заданий с дедлайном и тест-кейсами;
- отправка решений на `python`, `cpp` или `other`;
- автоматический запуск решений в изолированном Docker-контейнере;
- LLM-анализ решения с общим комментарием и построчными замечаниями;
- ручная итоговая проверка преподавателем с оценкой и финальным комментарием;
- веб-интерфейс на React и REST API на FastAPI.

## Стек

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, pytest.
- Frontend: React 18, TypeScript, Vite, Tailwind CSS.
- Judge: Docker-контейнер с Python и `g++` для запуска решений.
- LLM: Yandex Cloud AI через OpenAI-compatible API.

## Структура проекта

```text
.
├── backend/          # FastAPI API, модели, схемы, миграции, тесты
├── frontend/         # React/Vite приложение
├── judge/            # Dockerfile песочницы для автопроверки
├── docker-compose.yml
└── README.md
```

## Быстрый запуск через Docker

Требования:

- Docker и Docker Compose;
- доступ backend-контейнера к Docker socket, потому что автопроверка запускает отдельные judge-контейнеры.

1. Создайте `.env` в корне проекта:

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres123@db:5432/codecheck
SECRET_KEY=change-me
ALGORITHM=HS256

# Опционально, нужно для LLM-анализа
YANDEX_API_KEY=
YANDEX_FOLDER_ID=
YANDEX_MAIN_MODEL=aliceai-llm/latest
YANDEX_FALLBACK_MODEL=deepseek-v32/latest
```

2. Соберите image для автопроверки:

```bash
docker build -t judge-box ./judge
```

3. Запустите приложение:

```bash
docker compose up --build
```

После запуска доступны:

- frontend: http://localhost:3000
- backend API: http://localhost:8000
- Swagger/OpenAPI: http://localhost:8000/docs

Backend при старте автоматически выполняет `alembic upgrade head`.

## Первый администратор

Регистрация через UI/API создаёт пользователя с ролью `student`. Чтобы выдать первому пользователю права администратора, зарегистрируйтесь и выполните:

```bash
docker compose exec db psql -U postgres -d codecheck -c "UPDATE users SET role = 'admin' WHERE username = 'your-login';"
```

После этого администратор может создавать группы, удалять группы, просматривать пользователей и менять роли пользователей через веб-интерфейс.

## Основные сценарии

1. Администратор создаёт учебные группы и назначает роли пользователям.
2. Преподаватель создаёт задание для группы, добавляет открытые и скрытые тест-кейсы.
3. Студент отправляет решение.
4. Backend запускает LLM-анализ, а для `python` и `cpp` при наличии тестов дополнительно запускает автопроверку в `judge-box`.
5. Преподаватель смотрит результат, комментарии, код студента и выставляет оценку.

Решения со статусом `other` или задания без тест-кейсов не проходят автозапуск, но всё равно отправляются на LLM-анализ и ручную проверку.

## Полезные команды

Остановить контейнеры:

```bash
docker compose down
```

Остановить контейнеры и удалить данные PostgreSQL:

```bash
docker compose down -v
```

Посмотреть логи backend:

```bash
docker compose logs -f backend
```

Применить миграции вручную:

```bash
docker compose exec backend alembic upgrade head
```

## Тесты и проверки

Backend-тесты:

```bash
docker compose exec backend pytest
```

Сборка frontend:

```bash
docker compose run --rm frontend npm run build
```

Локальный запуск backend без Docker:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```

Локальный запуск frontend:

```bash
cd frontend
npm ci
npm run dev
```

Для полноценной локальной работы backend всё равно нужна PostgreSQL-база с `DATABASE_URL`, а для автопроверки - Docker и заранее собранный image `judge-box`.

## API

Основные группы эндпоинтов:

- `/auth` - регистрация и вход;
- `/users` - профиль, смена пароля, администрирование пользователей;
- `/groups` - учебные группы;
- `/tasks` - задания и тест-кейсы;
- `/submissions` - отправки решений, результаты проверки и оценивание.

Полная интерактивная документация доступна после запуска backend по адресу http://localhost:8000/docs.

## Переменные окружения

| Переменная | Назначение |
| --- | --- |
| `DATABASE_URL` | строка подключения SQLAlchemy к базе данных |
| `SECRET_KEY` | ключ подписи JWT |
| `ALGORITHM` | алгоритм JWT, по умолчанию `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | время жизни access token |
| `JUDGE_IMAGE` | Docker image для автопроверки, по умолчанию `judge-box` |
| `JUDGE_TIMEOUT_SECONDS` | лимит времени на запуск команды проверки |
| `JUDGE_MEMORY_LIMIT` | лимит памяти judge-контейнера |
| `JUDGE_CPU_LIMIT` | лимит CPU judge-контейнера |
| `JUDGE_PIDS_LIMIT` | лимит процессов judge-контейнера |
| `YANDEX_API_KEY` | API-ключ Yandex Cloud AI |
| `YANDEX_FOLDER_ID` | folder id Yandex Cloud |
| `YANDEX_MAIN_MODEL` | основная LLM-модель |
| `YANDEX_FALLBACK_MODEL` | резервная LLM-модель |
| `YANDEX_BASE_URL` | base URL OpenAI-compatible API |
| `LLM_TEMPERATURE` | температура LLM-ответа |
| `LLM_MAX_OUTPUT_TOKENS` | лимит токенов LLM-ответа |
| `LLM_REQUEST_TIMEOUT_SECONDS` | timeout LLM-запроса |
| `LLM_RETRY_DELAY_SECONDS` | задержка перед повторной попыткой LLM-запроса |
| `LLM_MAX_RETRIES` | количество повторных попыток LLM-запроса |
| `LLM_DEBUG_LOGGING` | подробное логирование LLM-запросов |

## Безопасность

Файл `.env` игнорируется Git. Не храните реальные ключи и production-секреты в репозитории. Для production-окружения обязательно замените `SECRET_KEY`, ограничьте доступ к Docker socket и настройте отдельные секреты для базы данных и LLM-провайдера.
