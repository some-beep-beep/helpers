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

  global.HelpersAPI = {
    API_URL: API_URL,
    loadSheet: loadSheet,
    saveSheet: saveSheet
  };
})(window);
