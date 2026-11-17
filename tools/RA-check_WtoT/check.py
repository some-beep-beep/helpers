#!/usr/bin/env python3
"""Проверка цены Ryanair на фиксированные даты, история в Google Sheets, отчёт в Telegram.

Берёт самый дешёвый тариф на конкретный рейс (публичный поиск тарифов Ryanair),
считает итог на всех пассажиров и сравнивает с прошлой проверкой.

Переменные окружения (GitHub Secrets):
  TG_BOT_TOKEN, TG_CHAT_ID  — Telegram
  SHEETS_API_URL, SHEETS_API_TOKEN — Apps Script Web App (лист FlightPrices)

Запуск:  python3 check.py            # боевой
         python3 check.py --dry-run  # только печать, без Telegram и Sheets
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

FARE_URL = "https://www.ryanair.com/api/farfnd/v4/oneWayFares"
UA = "ra-check-personal/1.0 (personal price monitor, 2 requests per run)"
HEADERS = ["checked_at", "out_date", "out_flight", "out_price_usd",
           "ret_date", "ret_flight", "ret_price_usd", "pax", "total_usd", "note"]
SHEET = "FlightPrices"
MINSK = timezone(timedelta(hours=3))


def http_json(url, data=None, headers=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_fare(origin, dest, day, currency):
    """Самый дешёвый тариф на человека на рейс в этот день. None — рейса нет."""
    qs = urllib.parse.urlencode({
        "departureAirportIataCode": origin,
        "arrivalAirportIataCode": dest,
        "outboundDepartureDateFrom": day,
        "outboundDepartureDateTo": day,
        "currency": currency,
    })
    last_err = None
    for attempt in range(3):
        try:
            data = http_json(f"{FARE_URL}?{qs}", headers={"User-Agent": UA, "Accept": "application/json"})
            fares = data.get("fares") or []
            if not fares:
                return None
            best = min(fares, key=lambda f: f["summary"]["price"]["value"])
            out = best["outbound"]
            return {
                "price": float(best["summary"]["price"]["value"]),
                "flight": out.get("flightNumber", ""),
                "departure": out.get("departureDate", ""),
                "arrival": out.get("arrivalDate", ""),
            }
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as err:
            last_err = err
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Ryanair не ответил для {origin}-{dest} {day}: {last_err}")


def money(x):
    return "$" + f"{x:,.2f}".replace(",", " ").replace(".", ",")


def ru_date(iso):
    y, m, d = iso.split("-")
    return f"{d}.{m}.{y}"


def hhmm(iso):
    return iso[11:16] if len(iso) >= 16 else "?"


def sheets_call(method, payload=None):
    base = os.environ["SHEETS_API_URL"]
    token = os.environ["SHEETS_API_TOKEN"]
    if method == "GET":
        url = f"{base}?token={urllib.parse.quote(token)}&sheet={SHEET}"
        data = http_json(url)
    else:
        body = json.dumps({"token": token, "sheet": SHEET, "rows": payload}, ensure_ascii=False).encode("utf-8")
        data = http_json(base, data=body, headers={"Content-Type": "text/plain;charset=utf-8"}, timeout=60)
    if not data.get("ok"):
        raise RuntimeError(f"Sheets: {data.get('error', data)}")
    return data.get("rows", [])


def send_telegram(text):
    token = os.environ["TG_BOT_TOKEN"]
    chat = os.environ["TG_CHAT_ID"]
    body = urllib.parse.urlencode({"chat_id": chat, "text": text, "disable_web_page_preview": "true"}).encode()
    http_json(f"https://api.telegram.org/bot{token}/sendMessage", data=body)


def build_message(cfg, out, ret, pax, total, prev_total, min_total, is_new_min):
    head = (f"✈️ {cfg['origin_name']} ({cfg['origin']}) ⇄ {cfg['destination_name']} ({cfg['destination']})\n"
            f"{ru_date(cfg['out_date'])} → {ru_date(cfg['ret_date'])} · {cfg['adults']} взр + {cfg['children']} реб\n")
    lines = [head]
    lines.append(f"Туда {out['flight']} {hhmm(out['departure'])}: {money(out['price'])} / чел")
    lines.append(f"Обратно {ret['flight']} {hhmm(ret['departure'])}: {money(ret['price'])} / чел")
    lines.append(f"\nИтого на {pax}: {money(total)}")
    if prev_total is not None:
        diff = total - prev_total
        if abs(diff) < 0.005:
            lines.append("С прошлой проверки: без изменений")
        else:
            arrow = "▼" if diff < 0 else "▲"
            lines.append(f"С прошлой проверки: {arrow} {money(abs(diff))}")
    if is_new_min:
        lines.append("🔥 Новый минимум за всё время наблюдений")
    elif min_total is not None:
        lines.append(f"Минимум за всё время: {money(min_total)}")
    lines.append("\nЦена: самый дешёвый тариф за рейс, только перелёт (без багажа и мест). "
                 "Ребёнок 4 года оплачивается как взрослый.")
    return "\n".join(lines)


def main():
    dry = "--dry-run" in sys.argv
    cfg = json.loads((Path(__file__).parent / "config.json").read_text(encoding="utf-8"))
    pax = cfg["adults"] + cfg["children"]
    now = datetime.now(MINSK).strftime("%d.%m.%Y %H:%M")

    out = fetch_fare(cfg["origin"], cfg["destination"], cfg["out_date"], cfg["currency"])
    ret = fetch_fare(cfg["destination"], cfg["origin"], cfg["ret_date"], cfg["currency"])

    if out is None or ret is None:
        missing = []
        if out is None:
            missing.append(f"туда {cfg['out_date']}")
        if ret is None:
            missing.append(f"обратно {cfg['ret_date']}")
        text = (f"✈️ {cfg['origin']} ⇄ {cfg['destination']}: рейса на эти даты сейчас нет "
                f"({', '.join(missing)}). Проверка {now}.")
        print(text)
        if not dry:
            send_telegram(text)
        return 0

    total = round((out["price"] + ret["price"]) * pax, 2)

    history = []
    if not dry and os.environ.get("SHEETS_API_URL"):
        history = sheets_call("GET")
    totals = [float(r["total_usd"]) for r in history if str(r.get("total_usd", "")).strip() != ""]
    prev_total = totals[-1] if totals else None
    min_total = min(totals) if totals else None
    is_new_min = bool(totals) and total < min_total

    text = build_message(cfg, out, ret, pax, total, prev_total, min_total, is_new_min)
    print(text)

    if dry:
        print("\n[dry-run] Sheets и Telegram пропущены")
        return 0

    history.append({
        "checked_at": now, "out_date": cfg["out_date"], "out_flight": out["flight"],
        "out_price_usd": out["price"], "ret_date": cfg["ret_date"], "ret_flight": ret["flight"],
        "ret_price_usd": ret["price"], "pax": pax, "total_usd": total, "note": "",
    })
    sheets_call("POST", history)
    send_telegram(text)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 — в Actions нужна понятная ошибка и сообщение в канал
        print(f"ОШИБКА: {exc}", file=sys.stderr)
        if "--dry-run" not in sys.argv and os.environ.get("TG_BOT_TOKEN") and os.environ.get("TG_CHAT_ID"):
            try:
                send_telegram(f"⚠️ Проверка цен Ryanair упала: {exc}")
            except Exception:  # noqa: BLE001
                pass
        sys.exit(1)
