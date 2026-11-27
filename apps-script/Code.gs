/**
 * helpers-finance API (bound to the spreadsheet)
 *
 * Deploy: Deploy → New deployment → Web app
 *   Execute as: Me
 *   Who has access: Anyone
 *
 * Auth: query/body/header param `token` must match API_TOKEN below.
 * Note: on a static GitHub Pages site the token is visible in JS —
 * the sheet itself stays private; protect the token as a shared secret.
 */

const API_TOKEN = 'h7Kp9mQ2xR4vL8nB3wY6tA1cE5uJ0sZ';

/** Таблица с листом ITOGO (GOOGLEFINANCE в шапке). */
const ITOGO_SPREADSHEET_ID = '1eGVr8mF5SCemBEC8jxdFZyG-8eEq6QigdLILv3SnfBs';

const ALLOWED_SHEETS = {
  Portfolio: ['ticker', 'shares', 'price', 'date'],
  BTC: ['amount', 'cost_usd'],
  Dividends: ['ticker', 'name', 'amount_usd', 'date'],
  Budget: ['id', 'name', 'byn'],
  BudgetSettings: ['total_byn', 'usd_rate', 'eur_rate'],
  Plan: ['month', 'item', 'amount', 'type'],
  // Invest page (everything except RU stocks + BTC)
  InvestAssets: [
    'id', 'name', 'category', 'ticker', 'amount_usd', 'amount_local',
    'currency', 'count', 'rate_pct', 'maturity', 'status', 'note'
  ],
  InvestIncome: ['asset', 'date', 'amount', 'currency', 'amount_byn', 'note'],
  InvestMeta: ['key', 'value'],
  // Одна строка в день: стоимость Invest без НЗ. Повтор за ту же дату клиент не пишет.
  InvestValue: ['date', 'value_usd'],
  // tools/RA-check_WtoT: история цен Ryanair (пишет GitHub Actions два раза в день).
  FlightPrices: [
    'checked_at', 'out_date', 'out_flight', 'out_price_usd',
    'ret_date', 'ret_flight', 'ret_price_usd', 'pax', 'total_usd', 'note'
  ],
  // tools/astro-forum-watch: уже отправленные в Telegram темы Астрофорума.
  ForumSeen: ['topic_id', 'title', 'url', 'seen_at'],
  // Найденные объявления (🎯/🔎) для страницы /astro/: пишет tools/astro-forum-watch.
  ForumAds: [
    'topic_id', 'posted', 'author', 'title', 'url', 'level', 'bundle',
    'rules', 'models', 'price', 'score', 'snippet', 'seen_at'
  ]
};

/** Колонки (1-based), которые держим текстом, чтобы Sheets не превращал их в даты. */
const TEXT_COLUMNS = { FlightPrices: [1, 2, 3, 5, 6, 10], ForumSeen: [2, 3, 4], ForumAds: [2, 3, 4, 5, 6, 7, 8, 9, 12, 13] };

function doGet(e) {
  try {
    const auth = authorize_(e);
    if (!auth.ok) return json_(auth.status, { ok: false, error: auth.error });

    const sheetName = String((e.parameter && e.parameter.sheet) || '').trim();
    if (!sheetName) {
      return json_(200, {
        ok: true,
        sheets: Object.keys(ALLOWED_SHEETS).concat(['ITOGO'])
      });
    }
    // Курсы из шапки листа ITOGO (GOOGLEFINANCE / GLD / IMOEX) — только чтение.
    if (sheetName === 'ITOGO') {
      return json_(200, { ok: true, sheet: 'ITOGO', quotes: readItogoQuotes_() });
    }
    // Котировки MOEX (TQBR + IMOEX) запрашиваются сервером Apps Script, а не браузером.
    if (sheetName === 'MOEX') {
      return json_(200, { ok: true, sheet: 'MOEX', quotes: readMoexQuotes_(e.parameter.tickers) });
    }
    if (!ALLOWED_SHEETS[sheetName]) {
      return json_(400, { ok: false, error: 'unknown_sheet', sheet: sheetName });
    }

    return json_(200, {
      ok: true,
      sheet: sheetName,
      rows: readSheet_(sheetName)
    });
  } catch (err) {
    return json_(500, { ok: false, error: String(err && err.message ? err.message : err) });
  }
}

function doPost(e) {
  try {
    const auth = authorize_(e);
    if (!auth.ok) return json_(auth.status, { ok: false, error: auth.error });

    const body = parseBody_(e);
    const sheetName = String(body.sheet || (e.parameter && e.parameter.sheet) || '').trim();
    // ITOGO содержит формулы — запись через API запрещена.
    if (sheetName === 'ITOGO') {
      return json_(400, { ok: false, error: 'itogo_read_only' });
    }
    if (!ALLOWED_SHEETS[sheetName]) {
      return json_(400, { ok: false, error: 'unknown_sheet', sheet: sheetName });
    }
    if (!Array.isArray(body.rows)) {
      return json_(400, { ok: false, error: 'rows_must_be_array' });
    }

    // Prevent accidental wipe without explicit empty array intent is fine;
    // empty rows[] clears data and keeps headers — allowed by design.
    const lock = LockService.getDocumentLock();
    lock.waitLock(15000);
    try {
      writeSheet_(sheetName, body.rows);
    } finally {
      lock.releaseLock();
    }

    return json_(200, {
      ok: true,
      sheet: sheetName,
      saved: body.rows.length,
      rows: readSheet_(sheetName)
    });
  } catch (err) {
    return json_(500, { ok: false, error: String(err && err.message ? err.message : err) });
  }
}

/** Optional CORS preflight — some browsers send OPTIONS before POST. */
function doOptions() {
  return ContentService.createTextOutput('')
    .setMimeType(ContentService.MimeType.TEXT);
}

function authorize_(e) {
  const expected = String(API_TOKEN || '');
  if (!expected) {
    return { ok: false, status: 500, error: 'token_not_configured' };
  }

  const fromParam = e && e.parameter ? e.parameter.token : '';
  // Custom headers often trigger CORS preflight; prefer ?token= or JSON body.token.
  const fromHeader = e && e.headers
    ? (e.headers.Authorization || e.headers.authorization || e.headers['X-Api-Token'] || e.headers['x-api-token'] || '')
    : '';
  let fromBody = '';
  try {
    const body = parseBody_(e);
    if (body && body.token) fromBody = body.token;
  } catch (_) {}

  let headerToken = String(fromHeader || '');
  if (/^Bearer\s+/i.test(headerToken)) {
    headerToken = headerToken.replace(/^Bearer\s+/i, '');
  }

  const provided = String(fromParam || fromBody || headerToken || '');
  if (!provided || provided !== expected) {
    return { ok: false, status: 401, error: 'unauthorized' };
  }
  return { ok: true };
}

function parseBody_(e) {
  if (!e || !e.postData || !e.postData.contents) return {};
  const raw = e.postData.contents;
  try {
    return JSON.parse(raw);
  } catch (_) {
    // Also accept form-encoded fallbacks if ever needed.
    return {};
  }
}

/**
 * Шапка ITOGO (строка 1): пары подпись|значение
 * BTC | $… | USD / BYN | … | RUR / USD | … | MOEX | … | GOLD | $…/г
 */
function findItogoSheet_(ss) {
  var names = ['ITOGO', 'Itogo', 'itogo', 'ИТОГО', 'Итого'];
  for (var i = 0; i < names.length; i++) {
    var sh = ss.getSheetByName(names[i]);
    if (sh) return sh;
  }
  // Fallback: tab name contains ITOGO / ИТОГ (без учёта регистра)
  var all = ss.getSheets();
  for (var j = 0; j < all.length; j++) {
    var n = String(all[j].getName() || '');
    var u = n.toUpperCase();
    if (u.indexOf('ITOGO') !== -1 || n.indexOf('ИТОГ') !== -1) return all[j];
  }
  return null;
}

function sheetNames_(ss) {
  return ss.getSheets().map(function (s) { return s.getName(); });
}

/**
 * Котировки MOEX (акции TQBR + индекс IMOEX) с ISS по HTTP: по HTTPS серверы Google
 * не принимают сертификат MOEX, а по HTTP те же публичные данные отдаются без него.
 * Результат кэшируется на 60 с. Если ISS не ответил, цены берём с вкладки «Цены MOEX».
 * tickers — строка "SBER,PLZL,..." (только латиница/цифры, до 40 штук).
 * Возвращает { prices: { TICKER: { last, dayPct } }, imoex }.
 */
function readMoexQuotes_(tickersParam) {
  const list = String(tickersParam || '')
    .split(',')
    .map(function (t) { return t.trim().toUpperCase(); })
    .filter(function (t) { return /^[A-Z0-9]{1,12}$/.test(t); })
    .slice(0, 40);

  const cache = CacheService.getScriptCache();
  const cacheKey = 'moex_' + Utilities.base64Encode(
    Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, list.join(',')));
  const cached = cache.get(cacheKey);
  if (cached) {
    try { return JSON.parse(cached); } catch (e) { /* пересчитаем */ }
  }

  const out = { prices: {}, imoex: null };

  function iss_(path) {
    const resp = UrlFetchApp.fetch('http://iss.moex.com/iss/' + path, {
      muteHttpExceptions: true,
      headers: { 'User-Agent': 'Mozilla/5.0' }
    });
    if (resp.getResponseCode() !== 200) throw new Error('moex_http_' + resp.getResponseCode());
    return JSON.parse(resp.getContentText()).marketdata || {};
  }

  if (list.length) {
    try {
      const md = iss_('engines/stock/markets/shares/boards/TQBR/securities.json?iss.meta=off&iss.only=marketdata' +
        '&marketdata.columns=SECID,LAST,LCURRENTPRICE,LASTTOPREVPRICE&securities=' + encodeURIComponent(list.join(',')));
      const cols = md.columns || [];
      const iSec = cols.indexOf('SECID');
      const iLast = cols.indexOf('LAST');
      const iCur = cols.indexOf('LCURRENTPRICE');
      const iPct = cols.indexOf('LASTTOPREVPRICE');
      (md.data || []).forEach(function (row) {
        const ticker = iSec >= 0 ? row[iSec] : null;
        const last = iLast >= 0 ? Number(row[iLast]) : 0;
        const cur = iCur >= 0 ? Number(row[iCur]) : 0;
        const price = last > 0 ? last : cur;
        if (ticker && price > 0) {
          out.prices[ticker] = {
            last: price,
            dayPct: iPct >= 0 && row[iPct] != null ? Number(row[iPct]) : 0
          };
        }
      });
    } catch (e) {
      // ISS недоступен — ниже подставим цены с вкладки.
    }
  }

  try {
    const im = iss_('engines/stock/markets/index/securities/IMOEX.json?iss.meta=off&iss.only=marketdata' +
      '&marketdata.columns=CURRENTVALUE,LASTVALUE');
    const row = (im.data || [])[0];
    if (row) {
      const icols = im.columns || [];
      const cur = Number(row[icols.indexOf('CURRENTVALUE')]);
      const last = Number(row[icols.indexOf('LASTVALUE')]);
      out.imoex = cur > 0 ? cur : (last > 0 ? last : null);
    }
  } catch (e) {
    out.imoex = null;
  }

  // Запасной источник для тикеров, которых ISS не вернул: вкладка «Цены MOEX» таблицы INVEST.
  const missing = list.filter(function (t) { return !out.prices[t]; });
  if (missing.length) {
    try {
      const sh = SpreadsheetApp.openById(ITOGO_SPREADSHEET_ID).getSheetByName('Цены MOEX');
      const lastRow = sh ? sh.getLastRow() : 1;
      if (lastRow >= 2) {
        sh.getRange(2, 1, lastRow - 1, 2).getValues().forEach(function (row) {
          const ticker = String(row[0] || '').trim().toUpperCase();
          const price = Number(row[1]);
          if (ticker && missing.indexOf(ticker) !== -1 && price > 0 && !out.prices[ticker]) {
            out.prices[ticker] = { last: price, dayPct: 0 };
          }
        });
      }
    } catch (e) {
      // Вкладки нет или недоступна — эти тикеры просто не отдаём.
    }
  }

  if (Object.keys(out.prices).length) cache.put(cacheKey, JSON.stringify(out), 60);
  return out;
}

function readItogoQuotes_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = findItogoSheet_(ss);
  var tried = 'active:' + sheetNames_(ss).join('|');

  // Лист ITOGO может быть в основной таблице портфеля (другой файл / тот же ID).
  if (!sh && ITOGO_SPREADSHEET_ID) {
    try {
      ss = SpreadsheetApp.openById(ITOGO_SPREADSHEET_ID);
      sh = findItogoSheet_(ss);
      tried += '; openById:' + sheetNames_(ss).join('|');
    } catch (e) {
      tried += '; openById_fail:' + String(e && e.message ? e.message : e);
    }
  }

  if (!sh) {
    throw new Error('missing_sheet:ITOGO; ' + tried);
  }

  const lastCol = Math.max(sh.getLastColumn(), 12);
  const labels = sh.getRange(1, 1, 1, lastCol).getDisplayValues()[0];
  const values = sh.getRange(1, 1, 1, lastCol).getValues()[0];

  function normLabel(s) {
    return String(s || '')
      .toUpperCase()
      .replace(/\s+/g, '')
      .replace(/\//g, '');
  }

  function asNumber(v) {
    if (typeof v === 'number' && isFinite(v)) return v;
    const raw = String(v == null ? '' : v)
      .replace(/\$/g, '')
      .replace(/\s/g, '')
      .replace(',', '.');
    const n = Number(raw);
    return isFinite(n) ? n : null;
  }

  const out = {
    btc: null,
    usdByn: null,
    usdRub: null,
    imoex: null,
    goldPerGram: null
  };

  for (var i = 0; i < labels.length; i++) {
    const key = normLabel(labels[i]);
    const num = asNumber(values[i + 1]);
    if (num == null) continue;
    if (key === 'BTC') out.btc = num;
    else if (key === 'USDBYN') out.usdByn = num;
    else if (key === 'RURUSD' || key === 'USDRUB' || key === 'RUBUSD') out.usdRub = num;
    else if (key === 'MOEX' || key === 'IMOEX') out.imoex = num;
    else if (key === 'GOLD' || key === 'GLD') out.goldPerGram = num;
  }

  if (out.btc == null && out.usdByn == null && out.usdRub == null) {
    throw new Error('itogo_empty');
  }
  return out;
}

function ensureSheet_(sheetName) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(sheetName);
  const headers = ALLOWED_SHEETS[sheetName];
  if (!sh) {
    sh = ss.insertSheet(sheetName);
    if (headers && headers.length) {
      sh.getRange(1, 1, 1, headers.length).setValues([headers]);
    }
  }
  return sh;
}

function readSheet_(sheetName) {
  const sh = ensureSheet_(sheetName);

  const values = sh.getDataRange().getDisplayValues();
  if (!values.length) return [];

  const headers = values[0].map(function (h) { return String(h || '').trim(); });
  const expected = ALLOWED_SHEETS[sheetName];
  expected.forEach(function (col) {
    if (headers.indexOf(col) === -1) {
      throw new Error('missing_header:' + sheetName + ':' + col);
    }
  });

  const rows = [];
  for (var r = 1; r < values.length; r++) {
    const line = values[r];
    const empty = line.every(function (c) { return String(c).trim() === ''; });
    if (empty) continue;

    const obj = {};
    headers.forEach(function (h, i) {
      if (!h) return;
      obj[h] = coerce_(sheetName, h, line[i]);
    });
    rows.push(obj);
  }
  return rows;
}

function writeSheet_(sheetName, rows) {
  const sh = ensureSheet_(sheetName);
  const headers = ALLOWED_SHEETS[sheetName];
  const lastRow = Math.max(sh.getLastRow(), 1);
  const lastCol = Math.max(sh.getLastColumn(), headers.length);

  // Keep header row; clear old data rows only.
  // 4-arg getRange(row, column, numRows, numColumns) — NOT end-row/end-col.
  if (lastRow > 1) {
    const numDataRows = lastRow - 1;
    sh.getRange(2, 1, numDataRows, lastCol).clearContent();
  }
  sh.getRange(1, 1, 1, headers.length).setValues([headers]);
  // Дата текстом, иначе Sheets превратит 29.10.2026 в дату и при чтении формат поплывёт.
  if (sheetName === 'InvestValue') {
    sh.getRange(1, 1, Math.max(rows.length + 1, 2), 1).setNumberFormat('@');
  }

  if (TEXT_COLUMNS[sheetName]) {
    TEXT_COLUMNS[sheetName].forEach(function (col) {
      sh.getRange(1, col, Math.max(rows.length + 1, 2), 1).setNumberFormat('@');
    });
  }

  if (!rows.length) return;

  const matrix = rows.map(function (row) {
    return headers.map(function (h) {
      var v = row[h];
      return v === undefined || v === null ? '' : v;
    });
  });
  sh.getRange(2, 1, matrix.length, headers.length).setValues(matrix);
}

function coerce_(sheetName, header, value) {
  const raw = value === null || value === undefined ? '' : String(value).trim();
  if (raw === '') return '';

  const numericHeaders = {
    Portfolio: { shares: true, price: true },
    BTC: { amount: true, cost_usd: true },
    Dividends: { amount_usd: true },
    Budget: { byn: true },
    BudgetSettings: { total_byn: true, usd_rate: true, eur_rate: true },
    Plan: { amount: true },
    InvestAssets: {
      amount_usd: true, amount_local: true, count: true, rate_pct: true
    },
    InvestIncome: { amount: true, amount_byn: true },
    InvestValue: { value_usd: true },
    FlightPrices: { out_price_usd: true, ret_price_usd: true, pax: true, total_usd: true },
    ForumSeen: { topic_id: true },
    ForumAds: { topic_id: true, price: true, score: true }
  };

  if (numericHeaders[sheetName] && numericHeaders[sheetName][header]) {
    // Support "1 035,00" / "1035.00"
    const normalized = raw.replace(/\s/g, '').replace(',', '.');
    const num = Number(normalized);
    return Number.isFinite(num) ? num : raw;
  }
  return raw;
}

function json_(status, obj) {
  // Apps Script ContentService cannot set HTTP status reliably for Web Apps.
  // Embed status in body; clients should check `ok`.
  const out = Object.assign({ status: status }, obj);
  return ContentService
    .createTextOutput(JSON.stringify(out))
    .setMimeType(ContentService.MimeType.JSON);
}
