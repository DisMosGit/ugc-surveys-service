# Опросы UGC

Сервис пользовательских опросов на Django и DRF. Ролей две, и на прохождение они не влияют: **автор** создаёт опросы, правит вопросы и варианты, читает статистику; **участник** отвечает на активные опросы по одному вопросу за раз, в том числе на опросы других авторов.

Пользователь определяется заголовком `X-Unsafe-User-Id`: запрос с новым значением заводит нового пользователя. Роль назначается в админке Django. Опрос состоит из названия, автора и даты создания; внутри - вопросы с вариантами ответов и возможностью своего варианта.

## Как запустить

Python 3.14 и [uv](https://docs.astral.sh/uv/). Настройки - в `.env`: скопируйте `.env.example`, там перечислены переменные с значениями по умолчанию. Без `DJANGO_SECRET_KEY` Django не стартует.

```bash
cp .env.example .env
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

Пока `DB_USER` пуст, всё работает на SQLite в `data/db/db.sqlite3`. Заполните `DB_USER`, `DB_PASSWORD`, `DB_HOST` - сервис пойдёт в PostgreSQL.

Админка на <http://127.0.0.1:8000/admin/>: `uv run python manage.py createsuperuser`. Роль «Автор» назначается в разделе **API-пользователи**.

Через Docker поднимается то же самое, но сразу с PostgreSQL:

```bash
docker compose up --build          # http://127.0.0.1:8000
docker compose exec web python manage.py createsuperuser
docker compose down
```

Исходники монтируются в контейнер только для чтения, сервер перезапускается сам при изменениях.

## Пример: опрос от создания до статистики

Автор - пользователь `1`, участник - `2`. Id в примерах заменены на `<survey-id>`, `<question-id>` и `<option-id>`.

### Автор

Создание опроса:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/surveys/ \
  -H 'X-Unsafe-User-Id: 1' -H 'Content-Type: application/json' \
  -d '{"title": "Овощи", "description": "Пример из задания"}'
```

```json
{
  "id": "01a1470e-be12-…",
  "title": "Овощи",
  "description": "Пример из задания",
  "is_active": true,
  "version": 1,
  "questions_count": 0,
  "session": null,
  "created_at": "2026-10-16T23:31:50.930654Z",
  "updated_at": "2026-10-16T23:31:50.930675Z"
}
```

Добавление вопроса:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/surveys/<survey-id>/questions/ \
  -H 'X-Unsafe-User-Id: 1' -H 'Content-Type: application/json' \
  -d '{"text": "Ты любишь огурцы?", "allows_custom_answer": true}'
```

```json
{
  "id": "01a1470e-bee5-…",
  "text": "Ты любишь огурцы?",
  "order": 1,
  "kind": 1,
  "kind_display": "Одиночный выбор",
  "allows_custom_answer": true,
  "is_required": true,
  "options": []
}
```

Варианты вопроса:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/questions/<question-id>/options/ \
  -H 'X-Unsafe-User-Id: 1' -H 'Content-Type: application/json' \
  -d '{"text": "Да"}'
```

```json
{"id": "01a1470e-bfb2-…", "text": "Да", "order": 1, "is_active": true}
```

`kind`: `1` - одиночный выбор, `2` - свободный ответ. У свободного вопроса вариантов нет. Порядок меняется полным списком id: `POST /api/v1/surveys/{id}/questions/reorder/` с телом `{"order": ["<id-1>", "<id-2>"]}` пишет `1..N`; частичный список - `400`.

### Прохождение

Участник забирает следующий вопрос - сессия создаётся сама:

```bash
curl http://127.0.0.1:8000/api/v1/surveys/<survey-id>/next-question/ \
  -H 'X-Unsafe-User-Id: 2'
```

```json
{
  "session": "01a1470f-0b51-…",
  "survey": "01a1470e-be12-…",
  "status": 1,
  "status_display": "Активно",
  "answered_count": 0,
  "questions_count": 3,
  "question": {
    "id": "01a1470e-bee5-…",
    "text": "Ты любишь огурцы?",
    "order": 1,
    "kind": 1,
    "kind_display": "Одиночный выбор",
    "allows_custom_answer": true,
    "is_required": true,
    "options": [
      {"id": "01a1470e-bfb2-…", "text": "Да", "order": 1},
      {"id": "01a1470e-bf7c-…", "text": "Нет", "order": 2},
      {"id": "01a1470e-bff3-…", "text": "Только в коктейлях", "order": 3}
    ]
  }
}
```

Ответ на вопрос: либо `option`, либо `custom_text`, но не оба сразу.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/surveys/<survey-id>/answers/ \
  -H 'X-Unsafe-User-Id: 2' -H 'Content-Type: application/json' \
  -d '{"question": "<question-id>", "option": "<option-id>"}'
```

```json
{
  "session": "01a1470f-0b51-…",
  "survey": "01a1470e-be12-…",
  "status": 1,
  "status_display": "Активно",
  "answered_count": 1,
  "questions_count": 3
}
```

Свой вариант - вместо `option` идёт `custom_text`, если вопрос это допускает.

```bash
curl -X POST http://127.0.0.1:8000/api/v1/surveys/<survey-id>/answers/ \
  -H 'X-Unsafe-User-Id: 2' -H 'Content-Type: application/json' \
  -d '{"question": "<question-id>", "custom_text": "Сельдерей"}'
```

Повторный ответ заменяет старый, счётчики переезжают. Последний ответ закрывает прохождение: `status` = `2`, дальше `next-question` - `204`. В закрытом прохождении ответить нельзя: `409`.

Новый проход открывается явно:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/surveys/<survey-id>/sessions/ \
  -H 'X-Unsafe-User-Id: 2'
```

```json
{
  "session": "01a1470f-141e-…",
  "survey": "01a1470e-be12-…",
  "status": 1,
  "status_display": "Активно",
  "answered_count": 0,
  "questions_count": 3
}
```

Такой же запрос при уже открытой сессии вернёт её же с кодом `200`, а новый проход - `201`.

### Статистика

Статистика по опросу:

```bash
curl http://127.0.0.1:8000/api/v1/surveys/<survey-id>/statistics/ \
  -H 'X-Unsafe-User-Id: 1'
```

```json
{
  "survey": {"id": "01a1470e-be12-…", "title": "Овощи"},
  "statistics": {
    "answers_count": 6,
    "completed_count": 2,
    "duration_sum_ms": 1457,
    "average_duration_ms": 728,
    "updated_at": "2026-10-16T23:32:12.704383Z"
  },
  "questions": [
    {
      "id": "01a1470e-bee5-…",
      "text": "Ты любишь огурцы?",
      "order": 1,
      "answers_count": 2,
      "updated_at": "2026-10-16T23:32:12.021516Z",
      "options": [
        {"id": "01a1470e-bfb2-…", "text": "Да", "order": 1, "selected_count": 2, "updated_at": "..."}
      ]
    }
  ]
}
```

- `answers_count` - сколько раз ответили на вопрос и на опрос целиком.
- `selected_count` - популярность варианта; варианты идут в порядке отображения.
- `duration_sum_ms` и `completed_count` - сколько времени заняли все прохождения суммарно и сколько их закрыто; `average_duration_ms` считается из них и равен `null`, пока ничего не завершено.
- Свой ответ попадает в `answers_count`, но ни одному варианту не приписывается - варианта у него просто нет.
- Пока ответов нет, `statistics` равен `null`.

Счётчики растут в том же запросе, который пишет ответ. Разъехавшиеся данные пересобирает идемпотентная задача:

```bash
uv run python manage.py shell -c "
from analytics.tasks import recalculate_survey_statistics
recalculate_survey_statistics.enqueue(survey_id='<survey-id>')
"
```

## Запросы

| Метод | Путь | Кто | Что делает |
|---|---|---|---|
| GET | `/api/v1/` | любой | корень API со ссылками |
| GET | `/api/v1/me/` | любой | кто я: `id`, `unsafe_id`, `role` |
| GET | `/api/v1/surveys/` | любой | активные опросы, страницами по 20, с моим прогрессом |
| POST | `/api/v1/surveys/` | автор | создать опрос |
| GET | `/api/v1/surveys/mine/` | автор | свои опросы, включая черновики |
| GET | `/api/v1/surveys/{id}/` | любой | один опрос |
| PATCH, PUT | `/api/v1/surveys/{id}/` | владелец | править |
| DELETE | `/api/v1/surveys/{id}/` | владелец | удалить, пока по нему не отвечали |
| GET | `/api/v1/surveys/{id}/questions/` | владелец | дерево вопросов со всеми вариантами |
| POST | `/api/v1/surveys/{id}/questions/` | владелец | добавить вопрос |
| POST | `/api/v1/surveys/{id}/questions/reorder/` | владелец | переставить вопросы |
| PATCH, PUT, DELETE | `/api/v1/questions/{id}/` | владелец | править или удалить вопрос |
| GET, POST | `/api/v1/questions/{id}/options/` | владелец | варианты вопроса |
| POST | `/api/v1/questions/{id}/options/reorder/` | владелец | переставить варианты |
| PATCH, PUT, DELETE | `/api/v1/answer-options/{id}/` | владелец | править или удалить вариант |
| GET | `/api/v1/surveys/{id}/next-question/` | любой | следующий вопрос или `204` |
| POST | `/api/v1/surveys/{id}/sessions/` | любой | начать новый проход |
| POST | `/api/v1/surveys/{id}/answers/` | любой | ответить на вопрос |
| GET | `/api/v1/surveys/{id}/statistics/` | владелец | агрегаты по опросу |

Идентификаторы в путях и телах принимаются и в виде из ответов API, и в исходном ULID.

## Модели

| Модель | Что это | Ключевые поля |
|---|---|---|
| `accounts.ApiUser` | пользователь сервиса | `unsafe_id`, `role` |
| `accounts.AdminUser` | вход в админку | стандартный Django-пользователь |
| `surveys.Survey` | опрос | `author`, `title`, `description`, `is_active`, `version` |
| `surveys.Question` | вопрос | `survey`, `text`, `order`, `kind`, `allows_custom_answer`, `is_required` |
| `surveys.AnswerOption` | вариант ответа | `question`, `text`, `order`, `is_active` |
| `answers.SurveySession` | прохождение опроса | `survey`, `user`, `status`, `answered_count`, `completed_at` |
| `answers.Answer` | ответ | `session`, `question`, `option`, `custom_text` |
| `analytics.SurveyStatistics` | агрегат по опросу | `completed_count`, `answers_count`, `duration_sum_ms` |
| `analytics.QuestionStatistics` | агрегат по вопросу | `answers_count` |
| `analytics.OptionStatistics` | агрегат по варианту | `selected_count` |

Первичные ключи - ULID, в ответах API они выглядят как UUID. Порядок хранится только в полях `order` у вопросов и вариантов: его ведёт сервисный слой, снаружи он только читается.

В базе закреплено остальное: уникальность `(survey, order)` и `(question, order)`, одно открытое прохождение на пару «пользователь - опрос», один ответ на вопрос в рамках прохождения и ровно один источник ответа - вариант или свой текст. Ссылки на вопрос и вариант защищены `PROTECT`: объект, на который уже отвечали, не удаляется, а деактивируется.

## Под нагрузкой

Расчётный объём: 1 000 000 опросов × 15 вопросов × 5 вариантов, 15 000 000 пользователей × 5 прохождений, до ~1,1 млрд ответов.

Сейчас: индексы под все горячие запросы, агрегатные таблицы статистики вместо `COUNT` по `Answer`, счётчики в транзакции ответа, ULID-ключи, ограничение одновременных запросов воркера. Дальше:

- `Answer` и `SurveySession` - партиционировать по дате или сессии.
- Статистику и каталог опросов - вынести на read-реплики, запись оставить на мастере.
- Структуру опроса и метаданные следующего вопроса - кэшировать.
- Ответы и счётчики - писать пачками вместо одиночных вставок.
- Соединения - PgBouncer перед PostgreSQL: при большом числе воркеров пула на процесс не хватает.
- Фоновые задачи - вынести в Celery: сейчас статистика считается в процессе запроса.
- Views и селекторы - переписать на async и убрать синхронные вызовы ORM.
- Объёмы - мерить `EXPLAIN ANALYZE` на критичных запросах и прогонять нагрузочные тесты до изменений.
