#!/usr/bin/env python3
"""Seed InvestAssets / InvestIncome / InvestMeta via Apps Script Web App."""
import json
import urllib.request

TOKEN = "h7Kp9mQ2xR4vL8nB3wY6tA1cE5uJ0sZ"
BASE = (
    "https://script.google.com/macros/s/"
    "AKfycbzHSEqB8DimeQ7T3R5Eh5G8Yv1tT3PVkZW1fBffSna2w75RYMDihslBDORLJvIOaLdWTQ/exec"
)


def post(sheet, rows):
    body = json.dumps({"token": TOKEN, "sheet": sheet, "rows": rows}).encode()
    req = urllib.request.Request(
        BASE,
        data=body,
        headers={"Content-Type": "text/plain;charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode())
    print(sheet, "->", data.get("ok"), "saved", data.get("saved"), "err", data.get("error"))
    if not data.get("ok"):
        raise SystemExit(1)
    return data


assets = [
    {"id": "a0", "name": "НЗ (запас наличкой)", "category": "cash", "ticker": "CASH", "amount_usd": 5000, "amount_local": 0, "currency": "USD", "count": 0, "rate_pct": 0, "maturity": "", "status": "active", "note": "не инвестировано · подушка"},
    {"id": "a1", "name": "ВГДО 331 (Айгенис) #1", "category": "bond", "ticker": "VGDO-331", "amount_usd": 1000, "amount_local": 2980, "currency": "BYN", "count": 0, "rate_pct": 4, "maturity": "29.06.2027", "status": "active", "note": "2980 BYN"},
    {"id": "a1b", "name": "ВГДО 331 (Айгенис) #2", "category": "bond", "ticker": "VGDO-331", "amount_usd": 1000, "amount_local": 2980, "currency": "BYN", "count": 0, "rate_pct": 4, "maturity": "29.06.2027", "status": "active", "note": "2980 BYN"},
    {"id": "a2", "name": "ГУРМИНА (файнес)", "category": "token", "ticker": "GURMINA.USD.2025.02", "amount_usd": 2000, "amount_local": 0, "currency": "USD", "count": 0, "rate_pct": 10, "maturity": "14.06.2028", "status": "active", "note": ""},
    {"id": "a3", "name": "ГУРМИНА (finstore)", "category": "token", "ticker": "GURMINA_(USD_721)", "amount_usd": 999.5, "amount_local": 0, "currency": "USD", "count": 0, "rate_pct": 9.25, "maturity": "15.05.2028", "status": "active", "note": ""},
    {"id": "a4", "name": "Бутикавто (finstore)", "category": "token", "ticker": "BUTIKAVTO_(USD_830)", "amount_usd": 2480, "amount_local": 0, "currency": "USD", "count": 0, "rate_pct": 10, "maturity": "15.12.2029", "status": "active", "note": ""},
    {"id": "a5", "name": "Евротайм (finstore)", "category": "token", "ticker": "EUROTM_(USD_774)", "amount_usd": 1000, "amount_local": 0, "currency": "USD", "count": 0, "rate_pct": 7.5, "maturity": "15.07.2030", "status": "active", "note": ""},
    {"id": "a6", "name": "Ювилс (finstore)", "category": "token", "ticker": "YOWHEELS_(BYN_840)", "amount_usd": 508, "amount_local": 0, "currency": "BYN", "count": 1500, "rate_pct": 19.5, "maturity": "10.05.2030", "status": "active", "note": ""},
    {"id": "a7", "name": "HELLO (байнекс)", "category": "token", "ticker": "HEL2USD27 (HEL2)", "amount_usd": 0, "amount_local": 0, "currency": "USD", "count": 0, "rate_pct": 9.5, "maturity": "", "status": "withdrawn", "note": "вывел 06.09.2026 · комиссия 7$"},
    {"id": "a8", "name": "Евротайм ERT1 (байнекс)", "category": "token", "ticker": "ERT1USD27 (ERT1)", "amount_usd": 1000, "amount_local": 0, "currency": "USD", "count": 0, "rate_pct": 6.5, "maturity": "20.08.2027", "status": "active", "note": ""},
    {"id": "a9", "name": "Евротайм ERT3 (байнекс)", "category": "token", "ticker": "ERT3USD30 (ERT3)", "amount_usd": 1200, "amount_local": 0, "currency": "USD", "count": 0, "rate_pct": 7.5, "maturity": "31.08.2028", "status": "active", "note": ""},
    {"id": "a10", "name": "Вклад BNB «Такса» капит. 12.6%", "category": "deposit", "ticker": "", "amount_usd": 1749, "amount_local": 5159.54, "currency": "BYN", "count": 0, "rate_pct": 12.6, "maturity": "10.07.2027", "status": "active", "note": ""},
    {"id": "a11", "name": "Вклад BNB «Такса» доход 14.5%", "category": "deposit", "ticker": "", "amount_usd": 1431, "amount_local": 4220.46, "currency": "BYN", "count": 0, "rate_pct": 14.5, "maturity": "18.07.2029", "status": "active", "note": ""},
    {"id": "a12", "name": "Вклад BNB «Такса» доход 12.9%", "category": "deposit", "ticker": "", "amount_usd": 73, "amount_local": 215, "currency": "BYN", "count": 0, "rate_pct": 12.9, "maturity": "16.09.2027", "status": "active", "note": ""},
    {"id": "a13", "name": "Золото слитки (5+5)", "category": "gold", "ticker": "GLD", "amount_usd": 1306.7, "amount_local": 0, "currency": "GLD", "count": 10, "rate_pct": 0, "maturity": "", "status": "active", "note": ""},
]


def add(inc, asset, date, amount, currency="USD", amount_byn=0, note=""):
    if amount or note:
        inc.append(
            {
                "asset": asset,
                "date": date,
                "amount": amount,
                "currency": currency,
                "amount_byn": amount_byn or "",
                "note": note,
            }
        )


inc = []
add(inc, "ВГДО 331 (Айгенис) #1", "29.12.2025", 38.44)
add(inc, "ВГДО 331 (Айгенис) #1", "29.06.2026", 38.44, "USD", 107.08)
add(inc, "ВГДО 331 (Айгенис) #2", "29.12.2025", 38.44)
add(inc, "ВГДО 331 (Айгенис) #2", "29.06.2026", 38.44, "USD", 107.08)
for d, a in [
    ("15.01.2026", 3.12), ("15.02.2026", 16.14), ("15.03.2026", 14.58), ("15.04.2026", 16.14),
    ("15.05.2026", 15.62), ("15.06.2026", 16.14), ("15.07.2026", 15.62), ("15.08.2026", 16.14),
    ("15.09.2026", 16.14), ("15.10.2026", 15.62),
]:
    add(inc, "ГУРМИНА (файнес)", d, a)
for d, a in [
    ("10.12.2025", 0.53), ("10.01.2026", 5.08), ("10.02.2026", 8.15), ("10.03.2026", 7.36),
    ("10.04.2026", 8.15), ("10.05.2026", 7.89), ("10.06.2026", 8.15), ("10.07.2026", 7.89),
    ("10.08.2026", 8.15), ("10.09.2026", 8.15), ("10.10.2026", 1.05),
]:
    add(inc, "HELLO (байнекс)", d, a)
add(inc, "HELLO (байнекс)", "06.09.2026", 0, "USD", 0, "вывел 993$ · комиссия 7$")
for d, a in [
    ("10.01.2026", 3.12), ("10.02.2026", 5.52), ("10.03.2026", 4.99), ("10.04.2026", 5.52),
    ("10.05.2026", 5.34), ("10.06.2026", 5.52), ("10.07.2026", 5.34), ("10.08.2026", 5.52),
    ("10.09.2026", 5.52), ("10.10.2026", 5.34),
]:
    add(inc, "Евротайм ERT1 (байнекс)", d, a)
for d, a in [
    ("10.02.2026", 3.95), ("10.03.2026", 6.9), ("10.04.2026", 7.64), ("10.05.2026", 7.4),
    ("10.06.2026", 7.64), ("10.07.2026", 7.4), ("10.08.2026", 7.64), ("10.09.2026", 7.64),
    ("10.10.2026", 7.4),
]:
    add(inc, "Евротайм ERT3 (байнекс)", d, a)
for d, a in [
    ("15.02.2026", 3.7), ("15.03.2026", 5.75), ("15.04.2026", 6.16), ("15.05.2026", 6.16),
    ("15.06.2026", 6.37), ("15.07.2026", 6.16), ("15.08.2026", 6.37), ("15.09.2026", 6.37),
    ("15.10.2026", 6.16),
]:
    add(inc, "Евротайм (finstore)", d, a)
for d, a in [
    ("15.02.2026", 10.41), ("15.03.2026", 15.34), ("15.04.2026", 16.99), ("15.05.2026", 16.44),
    ("15.06.2026", 19.35), ("15.07.2026", 20.38), ("15.08.2026", 21.06), ("15.09.2026", 21.06),
    ("15.10.2026", 20.38),
]:
    add(inc, "Бутикавто (finstore)", d, a)
for d, a, b in [
    ("05.03.2026", 5.53, 16.03), ("05.04.2026", 8.57, 24.84), ("05.05.2026", 8.56, 24.04),
    ("05.06.2026", 8.84, 24.84), ("05.07.2026", 8.56, 24.04), ("05.08.2026", 8.56, 24.04),
    ("05.09.2026", 7.88, 24.04), ("05.10.2026", 7.88, 24.04),
]:
    add(inc, "Ювилс (finstore)", d, a, "USD", b)
for d, a in [
    ("15.06.2026", 4.56), ("15.07.2026", 7.6), ("15.08.2026", 7.86), ("15.09.2026", 7.86),
    ("15.10.2026", 7.6),
]:
    add(inc, "ГУРМИНА (finstore)", d, a)
for d, a, b in [
    ("18.07.2026", 6.4, 18.31), ("18.08.2026", 6.24, 18.73), ("18.09.2026", 6.18, 18.54),
    ("18.10.2026", 8.51, 25.52),
]:
    add(inc, "Вклад BNB «Такса» доход 14.5%", d, a, "USD", b)
for d, a, b in [
    ("10.07.2026", 11.46, 32.77), ("10.08.2026", 13.12, 37.53), ("10.09.2026", 12.3, 37.53),
    ("10.10.2026", 11.73, 35.79),
]:
    add(inc, "Вклад BNB «Такса» капит. 12.6%", d, a, "USD", b)
for d, a, b in [("16.09.2026", 0.36, 1.1), ("16.10.2026", 0.35, 1.06)]:
    add(inc, "Вклад BNB «Такса» доход 12.9%", d, a, "USD", b)

meta = [{"key": "start_date", "value": "14.10.2025"}]

print("income rows", len(inc))
post("InvestAssets", assets)
post("InvestIncome", inc)
post("InvestMeta", meta)
print("DONE")
