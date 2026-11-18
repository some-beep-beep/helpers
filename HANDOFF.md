# Handoff: helpers / Invest

Дата: 2026-11-18  
Репо: `helpers` · ветка `main` · всё закоммичено и запушено, локальных правок нет  
GitHub Pages: https://some-beep-beep.github.io/helpers/  
Локально: `python3 -m http.server 8765` → http://127.0.0.1:8765/  
Пароль страниц: `906090` (cookie `portfolio_auth`)

Таблица Google:  
https://docs.google.com/spreadsheets/d/1eGVr8mF5SCemBEC8jxdFZyG-8eEq6QigdLILv3SnfBs/  
Лист курсов: **ITOGO** (`gid=1022596974`)

---

## Контекст

Статический личный портфель (не CoachEye). Данные — Google Sheets + Apps Script Web App.  
Токен API в `api.js` / `Code.gs` (сайт публичный — осознанно).

Навбар: Plan · Budget · **Invest**. Отдельной страницы MOEX нет (`index.html` → `invest.html`).

| Файл | Роль |
|------|------|
| `invest.html` | Весь портфель + UI + расчёты |
| `invest.css` | Стили Invest (вынесены 03.11) |
| `api.js` | Sheets API + FX (`fetchAllFx`, `loadItogoQuotes`) |
| `apps-script/Code.gs` | Web App backend |
| `budget.html` / `plan.html` | Бюджет / план |
| `scripts/seed-invest.py` | Сид Invest-листов |
| `docs/TELEGRAM-DIGEST.md` | ТЗ утреннего дайджеста (код не сделан) |
| `w-to-t/index.html` | Страница «✈️ Tickets»: таблица цен Ryanair (читает лист `FlightPrices`) |
| `tools/RA-check_WtoT/` | Мониторинг цен Ryanair (`check.py`, `config.json`, README) |
| `.github/workflows/ra-check.yml` | Запуск мониторинга по расписанию |
| `CLAUDE.md`, `.cursor/rules/` | Правила проекта |

---

## Deploy Apps Script (критично)

URL Web App **не менять** (лежит в `api.js`).

При правке `Code.gs`:
1. Вставить файл в Apps Script **этой** таблицы  
2. **Deploy → Manage deployments → ✏️ Edit → New version → Deploy**  
3. Не делать New deployment (сменится URL)

**Деплой с чтением листа `ITOGO` сделан** (проверено 16.11.2026: `?sheet=ITOGO` отдаёт `quotes`). После любой правки `Code.gs` деплой нужно повторить.  
Если New version не выложен, `?sheet=ITOGO` → `unknown_sheet`, страница падает на er-api.

Проверка в консоли браузера: `[FX] bundle source=ITOGO` (норма) или `ITOGO FAIL` / `er-api` (старый деплой).

---

## Листы Google Sheets

### Обычные (header + rows) — `ALLOWED_SHEETS`

| Лист | Назначение |
|------|------------|
| `InvestAssets` | Позиции bond/token/deposit/gold/cash |
| `InvestIncome` | Купоны/выплаты |
| `InvestMeta` | `start_date` = `14.10.2025` |
| `InvestValue` | Дневной снимок «Всего Invest» без НЗ |
| `Portfolio` | Сделки акций MOEX |
| `BTC` | `amount`, `cost_usd` |
| `Dividends` | Дивиденды |
| `FlightPrices` | История цен Ryanair (пишет `tools/RA-check_WtoT/check.py`) |
| Budget / BudgetSettings / Plan | Бюджет и план |

`InvestAssets`: `category` = `bond|token|deposit|gold|cash`, `status` = `active|withdrawn`.  
Золото: `count` = граммы, `amount_usd` = **себестоимость**. НЗ = cash $5000.

### ITOGO — особый лист (только чтение)

Строка 1, пары подпись → значение (GOOGLEFINANCE / скрипт IMOEX / GLD→$/г):

| Подпись | Пример | Поле API |
|---------|--------|----------|
| BTC | $77 297 | `btc` |
| USD / BYN | 2,94 | `usdByn` |
| RUR / USD | 80,3 | `usdRub` |
| MOEX | 2511 | `imoex` |
| GOLD | $124,47 /г | `goldPerGram` |

Формулы в таблице пользователя:

```
=ROUND(GOOGLEFINANCE("CURRENCY:BTCUSD");2)
=ROUND(GOOGLEFINANCE("CURRENCY:USDRUB");2)
=ROUND(GOOGLEFINANCE("CURRENCY:USDBYN");2)
=GET_IMOEX_CURRENT()
=ROUND(GOOGLEFINANCE("NYSEARCA:GLD") / 31,1035 / 0,0919; 2)
```

`GET /?sheet=ITOGO` → `{ ok, quotes: { btc, usdByn, usdRub, imoex, goldPerGram } }`.  
POST на ITOGO запрещён (`itogo_read_only`) — не затирать формулы.

---

## Курсы на странице (приоритет)

1. **ITOGO** (как в таблице) → BTC, $/₽, $/Br, GOLD $/г, IMOEX в ленте  
2. **er-api** — запасной пакет + всегда **€/Br** (в ITOGO нет)  
3. Константы fallback  

Акции **цен** — MOEX ISS TQBR; в USD делятся на `usdRub` из ITOGO/er-api.  
Обновление котировок ~60 с. Кэш FX в `api.js` ~30 с. Логи: префикс `[FX]`.

---

## Поведение Invest

Секции: облигации → токены → вклады → золото → акции → BTC → НЗ.

- **Всего Invest** — текущая оценка **без НЗ** (bond/token/deposit по `amount_usd`; gold/акции/BTC — mark).  
- **Заработал** = купоны + дивиденды + P&L золота/акций/BTC (выплаты в капитал не входят).  
- **Все сбережения** = Invest + НЗ.  
- **Годовых** = earned / себестоимость без НЗ × 365 / дни с `start_date`.  
- Ближайшие выплаты (30 дн + расписание) и погашения — баннеры.  
- **Рост капитала** — `InvestValue`, график неделя/месяц/год.  
- Миграции при загрузке (могут писать в Sheets): `ensureCashReserve`, `ensureVgdoPair`, `ensureGoldCost`.

### Блок расхождений — удалён

`TABLE_SNAPSHOT` / `#tableDrift` убраны. Вклады BYN и Ювилс (1500 BYN) пересчитываются в USD по текущему $/Br (`revalueBynAssets`, только отображение, Sheets не трогаем).

### Выплаты по месяцам

Аккордеон «📆 Выплаты по месяцам» (купоны + дивиденды, BYN → USD по текущему курсу, только прошедшие даты). Старый блок «История выплат» убран; данные — в `InvestIncome` / `Dividends`. Дивиденд TATN 894,34 RUB ($10,95) — 29.10.2026.

### Вклады BYN и данные таблицы

Вклады и Ювилс (1500 BYN) хранятся в BYN (`amount_local` / `count`), на странице пересчёт по текущему $/Br. Вклады BNB «Такса»: 12.6% капит. (5159,54 BYN), 14.5% доход (5220,46 BYN), 12.9% доход (215 BYN — сумма подтверждена); новые Нео Банк Азия, ВТБ капит. (ср + 3.85), ВТБ фикс — по 100 BYN, ставки/даты погашения внесены.

### Как вносить выплаты

Выплаты — лист `InvestIncome` (`asset, date, amount, currency, amount_byn, note`), дивиденды — `Dividends`. Пользователь присылает таблицу «Доход всего от инвестиций»; сверка: купоны + дивиденды = его «Доход всего» (на 16.11: $966,11 + $23,74 = $989,85). Ноябрь 2026 внесён полностью (ERT1, ERT3, Ювилс, Такса капит. и 12.9%, Евротайм, Бутикавто, ГУРМИНА finstore/файнекс). Даты в листе могут вернуться как `10.8.2026` (без нуля) — это нормально. Запись в лист: POST `saveSheet` заменяет лист целиком (читать → добавить → писать).

«Доход в день / в месяц» на странице = (выплаты + P&L акций/золота/BTC) / дни, не только выплаты; «За 30 дн (выплаты)» — только выплаты.

### Правила проекта

Лежат в `.cursor/rules/`, `CLAUDE.md` их подключает: `capital-asof.mdc` (серая строка «выплаты на …») и `monthly-payouts-check.mdc` (после смены месяца проверять «Выплаты по месяцам» и самому добавлять недостающие выплаты прошедшего месяца в `InvestIncome` с пометкой «расчётно»).

### Билеты Ryanair (RA-check)

Мониторинг: Варшава-Модлин (WMI) ⇄ Тенерифе-Южный (TFS), 22.05.2027 → 15.06.2027, 2 взр + 1 реб (4 года, как взрослый), только перелёт, прямые, USD. Подробности и настройка — `tools/RA-check_WtoT/README.md`.

- GitHub Actions `RA-check WMI-TFS`: 08:00 и 20:00 по Минску (cron `0 5,17 * * *` UTC) и вручную (`gh workflow run "RA-check WMI-TFS"`).
- Цена: публичный поиск тарифов `farfnd/v4/oneWayFares` (самый дешёвый тариф на рейс за человека). Закрытый `booking/.../availability` не используем: отвечает отказом, обходить защиту нельзя. Сверка с сайтом Ryanair 17.11: 22.05 FR6121 zł529,30 и 15.06 FR6122 zł590,50 совпадают с farfnd в PLN.
- Итог = (туда + обратно) × 3. Отчёт в Telegram-бот `@w_t_tickets_bot` (личный чат), строка в лист `FlightPrices`, страница `https://some-beep-beep.github.io/helpers/w-to-t/` (минимум за всё время подсвечен зелёным). Кнопка «✈️ Tickets» есть в шапке всех страниц.
- Секреты GitHub (Settings → Secrets → Actions): `TG_BOT_TOKEN`, `TG_CHAT_ID`, `SHEETS_API_URL`, `SHEETS_API_TOKEN`. В репозиторий токены не класть (репозиторий публичный).
- Лист `FlightPrices` добавлен в `Code.gs`; деплой New version сделан (версия 6, 17.11.2026). Apps Script-проект с API — тот, где `helpers-finance API`/`doGet`; отдельный проект с `GET_IMOEX_CURRENT`/`GET_PRICE` (формулы таблицы) не трогать.
- Первый запуск 17.11: $854,61 на троих (туда $132,29, обратно $152,58 за человека).

### ВГДО

Две позиции `#1` / `#2` по ~$1000, выплаты 29.12 и 29.06 по $38.44 на каждую.  
Купоны сверка: **$876.03** + дивиденды **$12.79** ≈ **$888.82** база «выплат» (P&L сверху плавает).

---

## Что сделано недавно (всё в git, `main`)

1. FX: единый `fetchAllFx`; приоритет **ITOGO**, иначе er-api (VPN ломал ЦБ/НБРБ). Лента курсов: IMOEX, BTC, Gold $/г, $/₽, $/Br, €/Br.  
2. Блок расхождений с таблицей удалён; BYN-активы пересчитываются по живому курсу.  
3. CSS → `invest.css`, cache-bust через `?v=` в `invest.html`.  
4. `Code.gs`: `readItogoQuotes_`, read-only ITOGO.  
5. «Заработал»: слева 30 дн + ср./мес и /день, справа купоны, акции + дивиденды, золото, биткоин.  
6. Аккордеон «Выплаты по месяцам»; старая «История выплат» убрана.  
7. `logo-invest-dnevnik.png` (вырезан из макета, пока нигде не используется).  
8. Карточки акций: справа вверху доля бумаги в общей стоимости акций (в ₽).  
9. Кнопка «✈️ Tickets» в шапке; на экранах до 520 px логотип в шапке скрыт, чтобы поместились четыре кнопки.  
10. Данные в Sheets до 18.11.2026: вклад «Такса» 14.5% — выплата $18,15 (54,46 BYN); купоны $984,24 + дивиденды $23,74 = $1 007,98 (= «Купоны всего» в таблице пользователя).

---

## Известные нюансы

1. Немецкий VPN: NBRB/CBR часто abort → не опираться на них.  
2. Книжные суммы вкладов/Ювилс в Sheets могут отставать от строки ITOGO/Excel.  
3. Пароль и API token в клиенте — не секрет от тех, кто открыл Pages.  
4. После правки `api.js` / css — hard refresh (Cmd+Shift+R).

---

## Возможные следующие задачи

- [ ] Ожидаются выплаты: Ювилс 05.12, ERT1/ERT3 и вклад 12.6% — 10.12, ГУРМИНА/Бутикавто/Евротайм — 15.12, вклады 12.9% — 16.12, 14.5% — 18.12; ВГДО 29.12 (в прогноз попадёт с 29.11; в коде купон $38,23 на бумагу, факт $38,44 — пользователь решил не менять).  
- [ ] Следить за ценами на `/w-to-t/`; идея: чаще проверять во время распродаж (конец ноября), сменить версии `actions/checkout`/`setup-python` (предупреждение Node 20).  
- [ ] Telegram-дайджест — `docs/TELEGRAM-DIGEST.md` (код не сделан).  
- [ ] Логотип в шапку/фавикон (по желанию).  
- [ ] Аллокация % сверху / цель «до НГ» (предлагалось, не делали).

---

## Стартовый промпт для нового чата

```
Продолжаем helpers (личный портфель, GitHub Pages).
Рабочая директория: /Users/ivan/MY/helpers
Прочитай HANDOFF.md и продолжай с текущего состояния.
Отвечай по-русски.
Не коммить/не пушь без явной просьбы.

Курсы идут с листа ITOGO таблицы (деплой Code.gs сделан):
https://docs.google.com/spreadsheets/d/1eGVr8mF5SCemBEC8jxdFZyG-8eEq6QigdLILv3SnfBs/
Код закоммичен и запушен. Данные (выплаты, вклады) — в Google Sheets; формат внесения см. в «Как вносить выплаты».
```
