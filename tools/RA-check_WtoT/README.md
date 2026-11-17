# RA-check_WtoT — мониторинг цен Ryanair

Два раза в день (08:00 и 20:00 по Минску) GitHub Actions проверяет цену на рейсы и присылает отчёт в Telegram. Каждая проверка пишется в лист `FlightPrices` Google Sheets.

**Маршрут:** Варшава-Модлин (WMI) → Тенерифе-Южный (TFS) **22.05.2027**, обратно **15.06.2027**, 2 взрослых + 1 ребёнок (4 года). Менять даты/маршрут — в `config.json`.

## Что считается

- Самый дешёвый тариф на каждый рейс (публичный поиск тарифов Ryanair `farfnd`), **только перелёт**, без багажа и мест, в USD.
- Итог = (туда + обратно) × 3 пассажира. Ребёнок 2–15 лет оплачивается у Ryanair как взрослый.
- Цена «от»: окончательная сумма при бронировании может отличаться (сборы, тариф).
- Если рейса на дату нет, в Telegram придёт сообщение об этом.
- Это публичный эндпоинт без авторизации, формат может измениться. Скрипт делает по 2 запроса за запуск.

## Файлы

| Файл | Назначение |
|------|------------|
| `check.py` | Скрипт (только стандартная библиотека Python, зависимостей нет) |
| `config.json` | Маршрут, даты, пассажиры |
| `../../.github/workflows/ra-check.yml` | Расписание GitHub Actions |
| `../../apps-script/Code.gs` | Добавлен лист `FlightPrices` |

## Настройка (один раз)

### 1. Telegram-бот
1. В Telegram откройте `@BotFather` → `/newbot` → задайте имя → получите **токен**.
2. Создайте канал (или откройте существующий) и добавьте бота **администратором** с правом публикации.
3. Узнайте chat id канала: отправьте в канал любое сообщение, затем откройте  
   `https://api.telegram.org/bot<ТОКЕН>/getUpdates`  
   и найдите `"chat":{"id":-100...}` (для канала число начинается с `-100`). Для личного чата с ботом: напишите боту `/start` и возьмите `chat.id` из `getUpdates`.

### 2. Google Sheets (обновить Apps Script)
1. Откройте Apps Script таблицы и вставьте новую версию `apps-script/Code.gs`.
2. **Deploy → Manage deployments → ✏️ Edit → New version → Deploy.** Не создавайте New deployment: URL должен остаться прежним.
3. Лист `FlightPrices` создастся сам при первой записи.

### 3. GitHub Secrets
Repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret | Значение |
|--------|----------|
| `TG_BOT_TOKEN` | токен бота из BotFather |
| `TG_CHAT_ID` | chat id канала |
| `SHEETS_API_URL` | URL Web App из `api.js` (`API_URL`) |
| `SHEETS_API_TOKEN` | `API_TOKEN` из `api.js` |

### 4. Первый запуск
Repo → Actions → **RA-check WMI-TFS** → **Run workflow**. В канал придёт отчёт, в таблице появится первая строка.

## Локально

```bash
python3 tools/RA-check_WtoT/check.py --dry-run   # только печать, без Telegram и Sheets
```

С переменными окружения (`TG_BOT_TOKEN`, `TG_CHAT_ID`, `SHEETS_API_URL`, `SHEETS_API_TOKEN`) скрипт без `--dry-run` работает как в Actions.

## Лист FlightPrices

`checked_at, out_date, out_flight, out_price_usd, ret_date, ret_flight, ret_price_usd, pax, total_usd, note` — по строке на проверку. Скрипт читает всю историю, добавляет строку и записывает лист целиком (так работает общий Apps Script).

## Заметки

- Cron в GitHub Actions может опаздывать на несколько минут. Расписание: `0 5,17 * * *` UTC.
- В GitHub Actions в публичных репозиториях запуски по расписанию отключаются, если 60 дней нет активности. Если проверки встали, запустите workflow вручную.
- История цен хранится в приватной таблице, не в репозитории.
