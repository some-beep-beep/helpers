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
  InvestValue: ['date', 'value_usd']
};

function doGet(e) {
  try {
    const auth = authorize_(e);
    if (!auth.ok) return json_(auth.status, { ok: false, error: auth.error });

    const sheetName = String((e.parameter && e.parameter.sheet) || '').trim();
    if (!sheetName) {
      return json_(200, { ok: true, sheets: Object.keys(ALLOWED_SHEETS) });
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
    InvestValue: { value_usd: true }
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
