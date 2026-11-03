/**
 * Shared Google Apps Script API helper for helpers-finance pages.
 */
(function (global) {
  const API_URL =
    'https://script.google.com/macros/s/AKfycbzHSEqB8DimeQ7T3R5Eh5G8Yv1tT3PVkZW1fBffSna2w75RYMDihslBDORLJvIOaLdWTQ/exec';
  const API_TOKEN = 'h7Kp9mQ2xR4vL8nB3wY6tA1cE5uJ0sZ';

  /** One FX bundle for the whole page (USD/BYN, EUR/BYN, USD/RUB). */
  let fxCache = null;
  let fxCacheAt = 0;
  const FX_CACHE_MS = 30000;

  async function parseJsonResponse(resp) {
    const text = await resp.text();
    try {
      return JSON.parse(text);
    } catch (e) {
      throw new Error('bad_api_response');
    }
  }

  async function loadSheet(sheet) {
    const url =
      API_URL +
      '?token=' +
      encodeURIComponent(API_TOKEN) +
      '&sheet=' +
      encodeURIComponent(sheet);
    const resp = await fetch(url, { method: 'GET', redirect: 'follow' });
    const data = await parseJsonResponse(resp);
    if (!data.ok) throw new Error(data.error || 'load_failed');
    return Array.isArray(data.rows) ? data.rows : [];
  }

  /**
   * Курсы из листа ITOGO (GOOGLEFINANCE / GLD / IMOEX в шапке таблицы).
   * Returns { btc, usdByn, usdRub, imoex, goldPerGram } or null if unavailable.
   */
  async function loadItogoQuotes() {
    const url =
      API_URL +
      '?token=' +
      encodeURIComponent(API_TOKEN) +
      '&sheet=' +
      encodeURIComponent('ITOGO');
    console.log('[FX] → ITOGO sheet');
    const started = Date.now();
    try {
      const resp = await fetch(url, { method: 'GET', redirect: 'follow' });
      const data = await parseJsonResponse(resp);
      if (!data.ok) throw new Error(data.error || 'itogo_failed');
      const q = data.quotes || null;
      console.log('[FX] ← ITOGO OK', Date.now() - started + 'ms', q);
      return q;
    } catch (e) {
      console.warn('[FX] ← ITOGO FAIL', Date.now() - started + 'ms', e && e.message ? e.message : e);
      return null;
    }
  }

  async function saveSheet(sheet, rows) {
    // text/plain avoids CORS preflight with Apps Script Web Apps
    const resp = await fetch(API_URL, {
      method: 'POST',
      redirect: 'follow',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' },
      body: JSON.stringify({
        token: API_TOKEN,
        sheet: sheet,
        rows: rows
      })
    });
    const data = await parseJsonResponse(resp);
    if (!data.ok) throw new Error(data.error || 'save_failed');
    return data;
  }

  async function fetchJsonTimed(url, timeoutMs, label) {
    const tag = label || url;
    const started = Date.now();
    const ctrl = new AbortController();
    const timer = setTimeout(function () { ctrl.abort(); }, timeoutMs || 4000);
    console.log('[FX] →', tag, url, 'timeout=' + (timeoutMs || 4000) + 'ms');
    try {
      const resp = await fetch(url, { signal: ctrl.signal, redirect: 'follow' });
      const ms = Date.now() - started;
      if (!resp.ok) {
        console.warn('[FX] ←', tag, 'HTTP', resp.status, ms + 'ms');
        throw new Error('http_' + resp.status);
      }
      const data = await resp.json();
      console.log('[FX] ←', tag, 'OK', ms + 'ms');
      return data;
    } catch (e) {
      const ms = Date.now() - started;
      console.warn('[FX] ←', tag, 'FAIL', ms + 'ms', e && e.name, e && e.message ? e.message : e);
      throw e;
    } finally {
      clearTimeout(timer);
    }
  }

  function validRate(n) {
    return Number.isFinite(n) && n > 0;
  }

  function ratesFromErApiUsd(data) {
    const byn = Number(data && data.rates && data.rates.BYN);
    const eur = Number(data && data.rates && data.rates.EUR);
    const rub = Number(data && data.rates && data.rates.RUB);
    return {
      usdByn: validRate(byn) ? byn : null,
      eurByn: validRate(byn) && validRate(eur) ? byn / eur : null,
      usdRub: validRate(rub) ? rub : null
    };
  }

  /**
   * Курсы для страницы.
   * 1) ITOGO (GOOGLEFINANCE из таблицы) — приоритет
   * 2) open.er-api.com — запасной (и EUR/BYN, которого нет в ITOGO)
   * Returns { usdByn, eurByn, usdRub, source, live, btc?, imoex?, goldPerGram? }.
   */
  async function fetchAllFx(fallback) {
    const now = Date.now();
    if (fxCache && now - fxCacheAt < FX_CACHE_MS) {
      console.log('[FX] cache hit', fxCache.source, {
        usdByn: fxCache.usdByn,
        eurByn: fxCache.eurByn,
        usdRub: fxCache.usdRub,
        ageMs: now - fxCacheAt
      });
      return fxCache;
    }

    const fb = fallback || {};
    const usdBynFb = validRate(Number(fb.usdByn)) ? Number(fb.usdByn) : 2.95;
    const eurBynFb = validRate(Number(fb.eurByn)) ? Number(fb.eurByn) : 3.25;
    const usdRubFb = validRate(Number(fb.usdRub)) ? Number(fb.usdRub) : 80.5;

    let eurByn = null;
    try {
      const data = await fetchJsonTimed('https://open.er-api.com/v6/latest/USD', 6000, 'er-api-all');
      const r = ratesFromErApiUsd(data);
      if (r.eurByn) eurByn = r.eurByn;
      // Если ITOGO недоступен — весь пакет с er-api.
      if (!fb.preferItogoOnly) {
        // continue below after ITOGO attempt
      }
      fb._er = r;
    } catch (e) {
      console.warn('[FX] er-api unavailable', e && e.message ? e.message : e);
    }

    const itogo = await loadItogoQuotes();
    if (itogo && validRate(itogo.usdByn) && validRate(itogo.usdRub)) {
      fxCache = {
        usdByn: itogo.usdByn,
        eurByn: eurByn || eurBynFb,
        usdRub: itogo.usdRub,
        source: 'ITOGO',
        live: true,
        btc: validRate(itogo.btc) ? itogo.btc : null,
        imoex: validRate(itogo.imoex) ? itogo.imoex : null,
        goldPerGram: validRate(itogo.goldPerGram) ? itogo.goldPerGram : null
      };
      fxCacheAt = Date.now();
      console.log('[FX] bundle source=ITOGO', fxCache);
      return fxCache;
    }

    const er = fb._er;
    if (er && er.usdByn && er.eurByn && er.usdRub) {
      fxCache = {
        usdByn: er.usdByn,
        eurByn: er.eurByn,
        usdRub: er.usdRub,
        source: 'er-api',
        live: true,
        btc: null,
        imoex: null,
        goldPerGram: null
      };
      fxCacheAt = Date.now();
      console.log('[FX] bundle source=er-api', fxCache);
      return fxCache;
    }

    fxCache = {
      usdByn: usdBynFb,
      eurByn: eurBynFb,
      usdRub: usdRubFb,
      source: 'fallback',
      live: false,
      btc: null,
      imoex: null,
      goldPerGram: null
    };
    fxCacheAt = Date.now();
    console.log('[FX] bundle source=fallback', fxCache);
    return fxCache;
  }

  /** @deprecated use fetchAllFx — kept for older callers */
  async function fetchFxRates(fallback) {
    const all = await fetchAllFx(fallback);
    return { usdByn: all.usdByn, eurByn: all.eurByn, source: all.source };
  }

  /** @deprecated use fetchAllFx — kept for older callers */
  async function fetchUsdRub(fallbackRub) {
    const all = await fetchAllFx({ usdRub: fallbackRub });
    return { usdRub: all.usdRub, source: all.source, live: all.live };
  }

  global.HelpersAPI = {
    API_URL: API_URL,
    loadSheet: loadSheet,
    loadItogoQuotes: loadItogoQuotes,
    saveSheet: saveSheet,
    fetchAllFx: fetchAllFx,
    fetchFxRates: fetchFxRates,
    fetchUsdRub: fetchUsdRub
  };
})(window);
