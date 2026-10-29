# Handoff: helpers / Invest

Дата: 2026-10-29  
Репо: `helpers` · ветка `main` · последний коммит: `f9e34cc`  
GitHub Pages: https://some-beep-beep.github.io/helpers/  
Локально: `python3 -m http.server 8765` → http://127.0.0.1:8765/  
Пароль страниц: `906090` (cookie `portfolio_auth`)

## Контекст проекта

Статический сайт личного портфеля (не CoachEye). Данные живут в Google Sheets через Apps Script Web App. Токен API лежит в `api.js` / `apps-script/Code.gs` (осознанно, сайт публичный).

### Страницы

| Файл | Роль |
|------|------|
| `index.html` | Редирект на `invest.html` |
| `invest.html` | Весь портфель: облигации, токены, вклады, золото, акции MOEX, BTC, НЗ |
| `budget.html` | Бюджет + курсы |
| `plan.html` | План |
| `api.js` | Sheets API + `fetchFxRates` (НБРБ → er-api) |
| `apps-script/Code.gs` | Backend Web App |
| `scripts/seed-invest.py` | Сид Invest-листов |

Навбар везде: Plan · Budget · **Invest**. Отдельной страницы MOEX нет.

## Google Sheets / Apps Script

- Deployment уже обновлён (Version 2, 29.10.2026), **URL тот же** — в `api.js`.
- Не создавать New deployment без нужды: только Edit → New version, иначе сменится URL.
- Листы Invest автосоздаются через `ensureSheet_`.

### InvestAssets

Колонки: `id, name, category, ticker, amount_usd, amount_local, currency, count, rate_pct, maturity, status, note`

- `category`: `bond` | `token` | `deposit` | `gold` | `cash`
- `status`: `active` | `withdrawn`
- Золото: `count` = граммы, `amount_usd` = **себестоимость** покупки
- НЗ: `category=cash`, $5000, «подушка» наличкой

### InvestIncome

Колонки: `asset, date, amount, currency, amount_byn, note`  
`asset` должен совпадать с `InvestAssets.name`.

### InvestMeta

`key, value` → `start_date` = `14.10.2025`

### InvestValue

`date, value_usd` — одна строка в день, стоимость **Всего Invest** без НЗ. Клиент не перезаписывает дату, которая уже есть.

Старые листы без изменений: Portfolio, BTC, Dividends, Budget, BudgetSettings, Plan.

## Поведение Invest (важно)

Одна страница. Секции: облигации → токены → вклады → золото → акции MOEX → BTC → НЗ.

- **Всего Invest** — текущая стоимость всех позиций **без НЗ**. Облигации/токены/вклады по `amount_usd`, золото и акции и BTC — по живой цене.
- Купоны и дивиденды в капитал **не** входят. Они в «Заработал».
- **Все сбережения** = Invest + НЗ. Разбивка: акции / BTC / прочие / НЗ.
- **Годовых (выплаты + P&L)** = (купоны + дивиденды + нереализованный P&L золота, акций и BTC) / себестоимость без НЗ × 365 / дни. Старт — `InvestMeta.start_date` (14.10.2025).
- На карточках bond/token/deposit и на SBER/YDEX: строка **Заработал**.
- Золото: PAXG/Binance → $/г. Акции: MOEX TQBR, USD/RUB — ЦБ. BTC: Binance. Обновление раз в 60 с. Если котировка не пришла — запасная цена, в итоге позиция остаётся по себестоимости.
- История выплат (купоны + дивиденды) и история сделок — аккордеоны, свёрнуты.
- Курсы BYN: НБРБ с таймаутом → fallback `open.er-api.com` (VPN).
- При загрузке миграции: `ensureCashReserve`, `ensureVgdoPair` → save в Sheets. Листы Portfolio / BTC / Dividends только читаются.
- **Рост капитала** — аккордеон над историей выплат, свёрнут. Раз в локальный день пишет в лист `InvestValue` (`date`, `value_usd`) сумму **Всего Invest** (без НЗ). Если строка за сегодня уже есть — не перезаписывает. График: неделя / месяц / год.
- Лист `InvestValue` заработает только после вставки `Code.gs` и **Deploy → Manage deployments → Edit → New version** (URL не менять).

### ВГДО

Две отдельные облигации, не дубль в таблице доходов:

- `ВГДО 331 (Айгенис) #1` и `#2`
- По ~$1000 + `amount_local` 2980 BYN
- По 2 выплаты на каждую (29.12.2025 и 29.06.2026 по $38.44)

### Сверка дохода с исходным файлом пользователя

| | USD |
|--|-----|
| Купоны Invest (с 2×ВГДО) | **876.03** |
| Дивиденды SBER + Яндекс | +12.79 |
| Итого в файле пользователя | **888.82** |

На Invest «Заработал» = **888.82** (купоны 876.03 + дивиденды 12.79).  
Если купоны ещё ~$799 — миграция ВГДО не применилась: hard refresh (`Cmd+Shift+R`).

## Что уже сделано

1. Страница Invest + листы + Code.gs + сид. Commit+push: `f9e34cc` (ещё без объединения с MOEX).
2. MOEX и BTC влиты в `invest.html`. `index.html` редиректит на Invest. Навбар без MOEX.
3. Локально проверено 29.10.2026: заработал $888.82, два ВГДО, НЗ $5000 отдельно, итог сбережений = Invest + НЗ.
4. Эти правки **не закоммичены**. GitHub Pages пока показывает старый сайт.

## Известные нюансы

1. Если `amount_usd` золота ≈ текущей оценке — P&L около нуля, пока не поправить себестоимость в Sheets.
2. HELLO — `withdrawn`, выплаты в истории остаются.
3. Токен API виден в статике.

## Возможные следующие задачи

- Закоммитить и запушить объединение, когда пользователь попросит — иначе Pages остаётся старым.
- Править капитал/выплаты в Sheets.
- Не трогать URL Web App без необходимости.
- UI/расчёты по запросу пользователя.

## Стартовый промпт для нового чата

Скопируй в новый агент-чат:

```
Продолжаем helpers (личный портфель, GitHub Pages).
Рабочая директория: /Users/ivan/MY/helpers
Прочитай HANDOFF.md и продолжай с текущего состояния.
Отвечай по-русски.
Не коммить/не пушь без явной просьбы.
```
