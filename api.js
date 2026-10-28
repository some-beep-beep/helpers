/**
 * Shared Google Apps Script API helper for helpers-finance pages.
 */
(function (global) {
  const API_URL =
    'https://script.google.com/macros/s/AKfycbzHSEqB8DimeQ7T3R5Eh5G8Yv1tT3PVkZW1fBffSna2w75RYMDihslBDORLJvIOaLdWTQ/exec';
  const API_TOKEN = 'h7Kp9mQ2xR4vL8nB3wY6tA1cE5uJ0sZ';

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

  async function fetchJsonTimed(url, timeoutMs) {
    const ctrl = new AbortController();
    const timer = setTimeout(function () { ctrl.abort(); }, timeoutMs || 4000);
    try {
      const resp = await fetch(url, { signal: ctrl.signal, redirect: 'follow' });
      if (!resp.ok) throw new Error('http_' + resp.status);
      return await resp.json();
    } finally {
      clearTimeout(timer);
    }
  }

  function validRate(n) {
    return Number.isFinite(n) && n > 0;
  }

  /**
   * USD→BYN and EUR→BYN.
   * NBRB first (short timeout — often blocked under VPN), then open.er-api.com.
   * Returns { usdByn, eurByn, source: 'nbrb'|'er-api'|'fallback' }.
   */
  async function fetchFxRates(fallback) {
    const fb = fallback || {};
    const usdFb = validRate(Number(fb.usdByn)) ? Number(fb.usdByn) : 2.95;
    const eurFb = validRate(Number(fb.eurByn)) ? Number(fb.eurByn) : 3.25;

    try {
      const [usdData, eurData] = await Promise.all([
        fetchJsonTimed('https://api.nbrb.by/exrates/rates/USD?parammode=2', 3500),
        fetchJsonTimed('https://api.nbrb.by/exrates/rates/EUR?parammode=2', 3500)
      ]);
      const usdByn = Number(usdData.Cur_OfficialRate) / (Number(usdData.Cur_Scale) || 1);
      const eurByn = Number(eurData.Cur_OfficialRate) / (Number(eurData.Cur_Scale) || 1);
      if (validRate(usdByn) && validRate(eurByn)) {
        return { usdByn: usdByn, eurByn: eurByn, source: 'nbrb' };
      }
    } catch (e) {
      console.warn('NBRB FX unavailable, trying er-api', e);
    }

    try {
      const data = await fetchJsonTimed('https://open.er-api.com/v6/latest/USD', 6000);
      const bynPerUsd = Number(data && data.rates && data.rates.BYN);
      const eurPerUsd = Number(data && data.rates && data.rates.EUR);
      if (!validRate(bynPerUsd) || !validRate(eurPerUsd)) throw new Error('er_api_bad');
      // EUR/BYN = (BYN per USD) / (EUR per USD)
      const eurByn = bynPerUsd / eurPerUsd;
      return { usdByn: bynPerUsd, eurByn: eurByn, source: 'er-api' };
    } catch (e) {
      console.warn('er-api FX unavailable, using fallback', e);
      return { usdByn: usdFb, eurByn: eurFb, source: 'fallback' };
    }
  }

  global.HelpersAPI = {
    API_URL: API_URL,
    loadSheet: loadSheet,
    saveSheet: saveSheet,
    fetchFxRates: fetchFxRates
  };
})(window);
