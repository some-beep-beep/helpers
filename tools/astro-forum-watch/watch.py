#!/usr/bin/env python3
"""Астрофорум, «Доска объявлений»: присылает каждое новое объявление в Telegram.

Раз в запуск: читает страницу раздела, находит темы, которых ещё не видели,
забирает текст первого сообщения, шлёт в Telegram и запоминает в листе ForumSeen
(Google Sheets). Объявления с «533» помечаются 🔥.

Переменные окружения (GitHub Secrets):
  FORUM_TG_BOT_TOKEN, FORUM_TG_CHAT_ID  — Telegram (если нет, берутся TG_BOT_TOKEN / TG_CHAT_ID)
  SHEETS_API_URL, SHEETS_API_TOKEN      — Apps Script Web App (лист ForumSeen)

Запуск:  python3 watch.py            # боевой
         python3 watch.py --dry-run  # только печать: без Telegram и без записи состояния
"""
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from pathlib import Path

import match

UA = "astro-forum-watch/1.0 (personal notifier, 1 request per 5 min, respects Crawl-delay)"
SHEET = "ForumSeen"
MINSK = timezone(timedelta(hours=3))
CRAWL_DELAY = 3  # robots.txt: Crawl-delay: 3


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    last = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except (urllib.error.URLError, TimeoutError) as err:
            last = err
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Форум не ответил: {url}: {last}")


def http_json(url, data=None, headers=None, timeout=30):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def clean_url(url):
    """Убираем PHPSESSID и якоря: ссылка должна быть стабильной."""
    url = html.unescape(url)
    url = re.sub(r"[?&]PHPSESSID=[^&#]*", "", url)
    return url.split("#")[0].rstrip("?&")


def parse_board(page):
    """Список тем раздела: id, название, автор, ссылка (в порядке на странице)."""
    topics, seen = [], set()
    for m in re.finditer(
        r'<span id="msg_\d+"><a href="([^"]*topic,(\d+)\.\d+\.html[^"]*)"[^>]*>(.*?)</a></span>'
        r'(?:.{0,500}?Просмотр профиля ([^"]+)")?',
        page, re.S,
    ):
        tid = int(m.group(2))
        if tid in seen:
            continue
        seen.add(tid)
        title = html.unescape(re.sub(r"<.*?>", "", m.group(3))).strip()
        author = html.unescape(m.group(4) or "").strip()
        topics.append({"id": tid, "title": title, "author": author,
                       "url": f"https://astronomy.ru/forum/index.php/topic,{tid}.0.html"})
    return topics


class FirstPost(HTMLParser):
    """Текст первого сообщения темы (первый div.inner) и время публикации."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.active = False
        self.done = False
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        a = dict(attrs)
        if not self.active and tag == "div" and "inner" in (a.get("class") or "").split():
            self.active, self.depth = True, 1
            return
        if self.active:
            if tag == "div":
                self.depth += 1
                self.parts.append("\n")
            elif tag in ("br", "p", "li"):
                self.parts.append("\n")

    def handle_endtag(self, tag):
        if self.active and tag == "div":
            self.parts.append("\n")
            self.depth -= 1
            if self.depth == 0:
                self.active, self.done = False, True

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def text(self):
        raw = "".join(self.parts).replace("\xa0", " ")
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n\s*\n+", "\n", raw)
        return raw.strip()


def post_time(page):
    m = re.search(r'class="smalltext">&#171;(.*?)&#187;', page, re.S)
    if not m:
        return ""
    text = html.unescape(re.sub(r"<.*?>", "", m.group(1))).replace("\xa0", " ")
    return re.sub(r"^[\s:]+", "", re.sub(r"\s+", " ", text)).strip()


def fetch_post(url):
    page = http_get(url)
    fp = FirstPost()
    fp.feed(page)
    return fp.text(), post_time(page)


def esc(s):
    return html.escape(s, quote=False)


def rule_line(name, r):
    label = match.RULE_NAMES[name]
    detail = ", ".join(r["models"] or r["reasons"]) or label
    if r["level"] == "found":
        return f"🎯 <b>НАЙДЕНО ({esc(label)}): {esc(detail)}</b> (счёт {r['score']})"
    return f"🔎 <b>Проверь вручную ({esc(label)}): {esc(detail)}</b> (счёт {r['score']})"


def build_message(cfg, topic, body, when, res):
    lines = []
    if res["bundle"]:
        names = " + ".join(match.RULE_NAMES[n] for n in res["items"])
        lines.append("📦 <b>КОМПЛЕКТ, высокий приоритет: " + esc(names) + "</b>")
    for name in res["items"]:
        lines.append(rule_line(name, res[name]))
    if any(res[n]["ambiguous"] for n in res["items"]):
        lines.append("⚠️ В тексте есть и подходящая модель, и исключение (цветная/другая модель): смотри текст")
    lines.append("🔭 <b>" + esc(topic["title"]) + "</b>")
    meta = " · ".join(x for x in (topic.get("author"), when) if x)
    if meta:
        lines.append(esc(meta))
    if res["price"]:
        lines.append(f"Цена в тексте: ~{res['price']:,} ₽".replace(",", " "))
    if body.lower().startswith(topic["title"].lower()):
        body = body[len(topic["title"]):].strip()
    snippet = body[: cfg.get("snippet_chars", 500)].strip()
    if len(body) > len(snippet):
        snippet += "…"
    if snippet:
        lines.append("")
        lines.append(esc(snippet))
    lines.append("")
    lines.append(topic["url"])
    return "\n".join(lines)


def sheets(method, rows=None):
    base = os.environ["SHEETS_API_URL"]
    token = os.environ["SHEETS_API_TOKEN"]
    if method == "GET":
        data = http_json(f"{base}?token={urllib.parse.quote(token)}&sheet={SHEET}")
    else:
        body = json.dumps({"token": token, "sheet": SHEET, "rows": rows}, ensure_ascii=False).encode("utf-8")
        data = http_json(base, data=body, headers={"Content-Type": "text/plain;charset=utf-8"}, timeout=60)
    if not data.get("ok"):
        raise RuntimeError(f"Sheets: {data.get('error', data)}")
    return data.get("rows", [])


def send_telegram(text):
    token = os.environ.get("FORUM_TG_BOT_TOKEN") or os.environ["TG_BOT_TOKEN"]
    chat = os.environ.get("FORUM_TG_CHAT_ID") or os.environ["TG_CHAT_ID"]
    body = urllib.parse.urlencode({
        "chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true",
    }).encode()
    http_json(f"https://api.telegram.org/bot{token}/sendMessage", data=body)


def main():
    dry = "--dry-run" in sys.argv
    cfg = json.loads((Path(__file__).parent / "config.json").read_text(encoding="utf-8"))
    topics = parse_board(http_get(cfg["board_url"]))
    if not topics:
        raise RuntimeError("На странице раздела не найдено ни одной темы: разметка форума изменилась?")

    history = [] if dry else sheets("GET")
    seen_ids = {int(r["topic_id"]) for r in history if str(r.get("topic_id", "")).strip() != ""}
    max_seen = max(seen_ids) if seen_ids else 0
    window = cfg.get("recent_id_window", 3000)

    if not dry and not seen_ids:
        # Первый запуск: запоминаем всё, что уже висит на доске, и не шлём старое.
        now = datetime.now(MINSK).strftime("%d.%m.%Y %H:%M")
        rows = [{"topic_id": t["id"], "title": t["title"], "url": t["url"], "seen_at": now} for t in topics]
        sheets("POST", rows)
        send_telegram(f"🔭 Слежение за «Доской объявлений» запущено. Сейчас на доске {len(topics)} тем, "
                      "дальше присылаю только новые.")
        print(f"Первый запуск: запомнил {len(topics)} тем")
        return 0

    if dry:
        new = sorted(topics, key=lambda t: t["id"])[-3:]  # пробный прогон: три самые свежие темы
    else:
        new = [t for t in topics if t["id"] not in seen_ids and t["id"] > max_seen - window]
        new.sort(key=lambda t: t["id"])
        new = new[-cfg.get("max_per_run", 15):]
    print(f"Тем на странице: {len(topics)}, новых: {len(new)}")

    now = datetime.now(MINSK).strftime("%d.%m.%Y %H:%M")
    added = []
    for t in new:
        if cfg.get("skip_sold", True) and match.is_sold(t["title"]):
            print(f"Пропускаю проданное: {t['id']} {t['title']}")
            if not dry:
                added.append({"topic_id": t["id"], "title": t["title"], "url": t["url"], "seen_at": now})
            continue
        time.sleep(CRAWL_DELAY)
        try:
            body, when = fetch_post(t["url"])
        except RuntimeError as err:
            print(f"Пропускаю {t['id']} до следующего запуска: {err}")
            continue
        res = match.analyze(t["title"], body, cfg)
        text = build_message(cfg, t, body, when, res)
        print("\n" + text)
        if dry:
            continue
        if res["level"] == "plain" and not cfg.get("post_all", True):
            added.append({"topic_id": t["id"], "title": t["title"], "url": t["url"], "seen_at": now})
            continue
        try:
            send_telegram(text)
        except Exception as err:  # noqa: BLE001 — не помечаем как увиденное, повторим в следующий раз
            print(f"Telegram не принял {t['id']}: {err}")
            continue
        added.append({"topic_id": t["id"], "title": t["title"], "url": t["url"], "seen_at": now})

    if added and not dry:
        history.extend(added)
        history = history[-cfg.get("keep_rows", 400):]
        sheets("POST", history)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ОШИБКА: {exc}", file=sys.stderr)
        sys.exit(1)
