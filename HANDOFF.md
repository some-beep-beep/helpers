# Handoff: helpers / Invest

Дата: 2026-11-03  
Репо: `helpers` · ветка `main` · последний **запушенный** коммит: `9c0d3ca`  
Локально есть **незакоммиченные** правки: `invest.html`, `invest.css` (новый), `api.js`, `apps-script/Code.gs`  
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

---

## Deploy Apps Script (критично)

URL Web App **не менять** (лежит в `api.js`).

При правке `Code.gs`:
1. Вставить файл в Apps Script **этой** таблицы  
2. **Deploy → Manage deployments → ✏️ Edit → New version → Deploy**  
3. Не делать New deployment (сменится URL)

**Сейчас в локальном `Code.gs` есть чтение листа `ITOGO`.**  
Пока New version не задеплоен, `?sheet=ITOGO` → `unknown_sheet`, страница падает на er-api.

Проверка в консоли браузера: `[FX] bundle source=ITOGO` (успех) или `ITOGO FAIL` / `er-api` (ещё старый деплой).

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

### ВГДО

Две позиции `#1` / `#2` по ~$1000, выплаты 29.12 и 29.06 по $38.44 на каждую.  
Купоны сверка: **$876.03** + дивиденды **$12.79** ≈ **$888.82** база «выплат» (P&L сверху плавает).

---

## Что сделано недавно (локально, не в git)

1. FX: единый `fetchAllFx`; приоритет **ITOGO**, иначе er-api (VPN ломал ЦБ/НБРБ).  
2. Баннер расхождений `TABLE_SNAPSHOT` без записи в Sheets.  
3. CSS → `invest.css`, cache-bust `?v=20261103b` на css/api.  
4. `Code.gs`: `readItogoQuotes_`, read-only ITOGO.  
5. Ранее на `main`: Invest+MOEX+BTC, график капитала, алерты выплат/погашений (`9c0d3ca`).

Pages = то, что запушено; локальные правки ITOGO/drift **ещё не commit/push**.

---

## Известные нюансы

1. Немецкий VPN: NBRB/CBR часто abort → не опираться на них.  
2. Книжные суммы вкладов/Ювилс в Sheets могут отставать от строки ITOGO/Excel.  
3. Пароль и API token в клиенте — не секрет от тех, кто открыл Pages.  
4. После правки `api.js` / css — hard refresh (Cmd+Shift+R).

---

## Возможные следующие задачи

- [ ] Задеплоить New version `Code.gs` (ITOGO).  
- [ ] Commit + push локальных правок (по просьбе).  
- [ ] Подтянуть в Sheets актуальные вклады/Ювилс **или** обновлять `TABLE_SNAPSHOT`.  
- [ ] Telegram-дайджест — `docs/TELEGRAM-DIGEST.md`.  
- [ ] Аллокация % сверху / цель «до НГ» (предлагалось, не делали).

---

## Стартовый промпт для нового чата

```
Продолжаем helpers (личный портфель, GitHub Pages).
Рабочая директория: /Users/ivan/MY/helpers
Прочитай HANDOFF.md и продолжай с текущего состояния.
Отвечай по-русски.
Не коммить/не пушь без явной просьбы.

Важно: курсы с листа ITOGO таблицы
https://docs.google.com/spreadsheets/d/1eGVr8mF5SCemBEC8jxdFZyG-8eEq6QigdLILv3SnfBs/
Нужен Deploy → Edit → New version для Code.gs с readItogoQuotes_.
Локально есть незакоммиченные invest.html / invest.css / api.js / Code.gs.
```
