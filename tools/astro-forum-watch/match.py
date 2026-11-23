"""Матчинг объявлений: три независимых правила и общий пакет для комплектов.

  camera — охлаждаемая моно-камера на Sony IMX533;
  wheel  — электронное колесо фильтров на 7 или 8 позиций;
  scope  — телескоп Sharpstar 61 EDPH II / III.

Нормализация: нижний регистр, NFKC (Ⅱ → ii), кириллические алиасы брендов, кириллические
омоглифы → латиница, без дефисов/точек/лишних пробелов; римские цифры после «61edph»
(ll, ii, lll, iii, mk2, mk3) приводятся к 2 и 3.

У каждого правила своя тир-схема: A (точное совпадение, +10), B («проверь вручную», +4, не выше 9),
бонусы начисляются только при совпадении A/B, исключение без явного совпадения даёт −10.
Уровень: счёт ≥ 10 — «found», 4–9 — «check», иначе «plain».
Если совпали два правила и больше — это комплект («bundle»), приоритет повышается.
"""
import re
import unicodedata

HOMOGLYPHS = str.maketrans({
    "а": "a", "с": "c", "м": "m", "е": "e", "о": "o", "р": "p",
    "т": "t", "х": "x", "в": "b", "к": "k", "н": "h", "і": "i",
})

# Кириллические написания брендов → латиница (до замены омоглифов).
ALIASES = [
    (r"плеер\s?ван|плейер\s?ван", "player one"),
    (r"куэйчайвай|кьюэйчуай", "qhy"),
    (r"тоуптек|тупток", "touptek"),
    (r"альтаир", "altair"),
    (r"омегон", "omegon"),
    (r"шарп\s?стар|sharp\s?star", "sharpstar"),
    (r"асай|аси(?![а-я])", "asi"),
    (r"зво", "zwo"),
]

RULE_NAMES = {"camera": "камера на 533", "wheel": "колесо фильтров", "scope": "Sharpstar 61 EDPH"}


def normalize(text):
    """(ru, mix, lat): ru — оригинал в нижнем регистре; mix — с алиасами брендов, кириллица сохранена;
    lat — «латиницей» для поиска моделей."""
    t = unicodedata.normalize("NFKC", text or "").lower().replace("ё", "е")
    ru = re.sub(r"\s+", " ", t).strip()
    aliased = ru
    for pattern, repl in ALIASES:
        aliased = re.sub(pattern, repl, aliased)
    mix = re.sub(r"\s+", " ", re.sub(r"[-._]", "", aliased)).strip()
    lat = aliased.translate(HOMOGLYPHS)
    lat = re.sub(r"\s+", " ", re.sub(r"[-._]", "", lat)).strip()
    # Римские цифры после 61edph: lll/iii/mk3 → 3, ll/ii/mk2 → 2
    lat = re.sub(r"(61\s?ed\s?ph)\s?(?:mk\s?)?(?:lll|iii|3)(?![a-z0-9])", r"\1 3", lat)
    lat = re.sub(r"(61\s?ed\s?ph)\s?(?:mk\s?)?(?:ll|ii|2)(?![a-z0-9])", r"\1 2", lat)
    return ru, mix, lat


PRICE_NUM = r"(\d{1,3}(?:[ .]\d{3})+|\d{3,7})"


def _to_int(num):
    return int(re.sub(r"[ .]", "", num))


def extract_price(text):
    """Цена в рублях из текста: «Цена 5500», «3.000 руб», «100 тысяч рублей», «3 тыс». None, если нет.

    Осторожный разбор: число должно стоять рядом со словом «цена» или с «₽/руб/р/тыс».
    """
    low = (text or "").lower().replace("\xa0", " ")
    candidates = []
    for m in re.finditer(r"(?<![\d.,])(\d{1,3})\s?(?:тыс|т\.\s?р)", low):
        candidates.append((m.start(), int(m.group(1)) * 1000))
    for m in re.finditer(r"цена[^\d]{0,20}" + PRICE_NUM + r"(\s?(?:тыс|т\.\s?р))?", low):
        value = _to_int(m.group(1)) * (1000 if m.group(2) else 1)
        candidates.append((m.start(), value))
    for m in re.finditer(r"(?<![\d.,])" + PRICE_NUM + r"\s?(?:₽|руб|р\b)", low):
        candidates.append((m.start(), _to_int(m.group(1))))
    candidates = [c for c in candidates if 100 <= c[1] <= 5_000_000]
    if not candidates:
        return None
    return min(candidates)[1]


SOLD_RE = re.compile(r"продано|продан|\bsold\b|закрыт|в резерве")


def is_sold(title):
    return bool(SOLD_RE.search((title or "").lower()))


def _search_any(patterns, text):
    return [p for p in patterns if re.search(p, text)]


def _price_bonus(price, rule_cfg):
    lo, hi = (rule_cfg or {}).get("price_min"), (rule_cfg or {}).get("price_max")
    if price is None or (lo is None and hi is None):
        return 0
    return 2 if (lo is None or price >= lo) and (hi is None or price <= hi) else 0


def _level(score):
    return "found" if score >= 10 else ("check" if score >= 4 else "plain")


def _finish(tier_a, tier_b, bonus, excluded):
    """A +10, B +4 (≤9); бонусы только при совпадении; исключение без явного A даёт −10."""
    base = 10 if tier_a else (4 if tier_b else 0)
    score = base + (bonus if base else 0)
    if excluded and not tier_a:
        score -= 10
    if not tier_a:
        score = min(score, 9)
    return score, _level(score)


# ---------------------------------------------------------------- камера на IMX533
CAMERA_A = [
    ("ZWO ASI533MM", r"asi\s?533\s?mm"),
    ("Player One Ares-M", r"ares\s?m\b"),
    ("QHY533M", r"qhy\s?533\s?m(?!c)"),
    ("ToupTek ATR533M", r"atr\s?533\s?m(?!c)"),
    ("Altair Hypercam 533M", r"hypercam\s?533\s?m(?!c)"),
    ("Omegon 533M", r"omegon.{0,30}533\s?m(?!c)"),
]
CAMERA_COLOR = [
    r"533\s?mc", r"533\s?c\b", r"ares\s?c\b", r"atr\s?533\s?c\b", r"hypercam\s?533\s?c",
    r"\bcolou?r\b", r"\bosc\b", r"one\s?shot",
]
CAMERA_COLOR_RU = [r"цветн"]
CAMERA_OTHER = [r"asi\s?(?:585|294|183|071|2600|2400|1600|178|174)"]
MONO_RU = r"\bmono\b|моно|ч/б|чб|черно-?бел"
CAMERA_WORDS = r"камера|camera|cooled|охлажд"
CAMERA_BONUS_PRO = r"\bpro\b|cooled|охлажд"
CAMERA_BONUS_SET = r"колесо|efw|фильтр|комплект"


def analyze_camera(ru, mix, lat, price, rule_cfg):
    models = [name for name, pat in CAMERA_A if re.search(pat, lat)]
    colors = _search_any(CAMERA_COLOR, lat) + _search_any(CAMERA_COLOR_RU, ru)
    excluded = bool(colors or _search_any(CAMERA_OTHER, lat))
    reasons = []
    if re.search(r"imx\s?533", lat) and re.search(MONO_RU, ru):
        reasons.append("IMX533 + моно")
    if re.search(r"(?<!\d)533(?!\d)", lat) and re.search(CAMERA_WORDS, ru) and not colors:
        reasons.append("533 + камера/охлаждение")
    if re.search(r"(?:asi|qhy)\s?533(?!\s?(?:mm|mc|m\b|c\b))", lat):
        reasons.append("asi533/qhy533 без суффикса M/C")
    if re.search(r"svbony.{0,40}?533", lat):
        reasons.append("Svbony на 533")
    # слабые сигналы: лучше лишнее уведомление, чем пропуск
    if not colors and not reasons:
        if re.search(r"imx\s?533", lat):
            reasons.append("упоминается IMX533")
        elif re.search(r"(?<![\d.,])533\s?(?:mm|m)(?![a-z0-9])", lat):
            reasons.append("533M/MM без бренда")
        elif re.search(r"(?<![\d.,])533(?![\d.,])", lat):
            reasons.append("число 533 в тексте (проверить)")
    bonus = 0
    if re.search(CAMERA_BONUS_PRO, f"{ru} {lat}"):
        bonus += 4
    if re.search(CAMERA_BONUS_SET, ru):
        bonus += 3
    bonus += _price_bonus(price, rule_cfg)
    score, level = _finish(bool(models), bool(reasons), bonus, excluded)
    return {"level": level, "score": score, "models": models, "reasons": reasons,
            "ambiguous": bool(models) and excluded}


# ---------------------------------------------------------------- колесо фильтров
# Названия сверены с сайтами продавцов/производителей: у Player One колёса называются Phoenix Wheel,
# у ToupTek — AFW, у ZWO 8x31 и 8x1.25" — одно и то же колесо EFW.
WHEEL_A = [
    ("ZWO EFW", r"efw\s?(?:7\s?x\s?36|8\s?x\s?(?:31|1\.?25))"),
    ("QHY CFW3", r"cfw\s?3\s?(?:m\s?us|s|l)"),
    ("Player One Phoenix", r"player\s?one.{0,30}(?:filter|колес|phoenix)|phoenix\s?(?:wheel|filter)"),
    ("Atik EFW2", r"atik.{0,10}efw"),
    ("ToupTek AFW", r"afw\s?m?\s?(?:7\s?x\s?36|8\s?x)"),
    ("ToupTek/Altair/Svbony", r"(?:toup|touptek|altair|svbony).{0,30}(?:\bfw\b|filter\s?wheel|колес)"),
]
WHEEL_B = [
    ("EFW без размера (проверить число позиций)", r"\befw\b"),
    ("QHY CFW2/CFW3 (проверить число позиций)", r"cfw\s?[23]"),
    ("электронное колесо", r"(?:электрон|motori|automatic|авто).{0,20}(?:колес|filter\s?wheel)"),
]
WHEEL_POSITIONS = r"(?:7|8)\s?(?:поз|позиц|pos|position|slot|x\s?(?:31|36))"
WHEEL_WORD = r"колес|wheel|\befw\b|cfw|\bafw\b"
WHEEL_EXCLUDE = [
    r"manual|ручн|mechanical|механич",              # ручные
    r"(?<!\d)5\s?x|5\s?pos|5\s?поз|\bmini\b",        # на 5 позиций и меньше, в том числе 5x1.25 и 5x2
    r"cfw\s?3\s?[sm]\s?(?:us|sr)\s?[56]\b",          # QHY CFW3M-US5 / S-US6 / M-SR5: 5-6 позиций
    r"cfw\s?3\s?m\s?sr",                             # QHY CFW3M-SR: 5 позиций, 2"
]
WHEEL_FILTERS = r"\b(?:lrgb|ha|oiii|sii|astronomik|baader|antlia|optolong)\b|zwo.{0,10}(?:фильтр|filter)"


def analyze_wheel(ru, mix, lat, price, rule_cfg, camera):
    both = f"{mix} {lat}"
    models = [name for name, pat in WHEEL_A if re.search(pat, lat) or re.search(pat, mix)]
    reasons = [name for name, pat in WHEEL_B if re.search(pat, lat) or re.search(pat, mix)]
    if re.search(WHEEL_POSITIONS, both) and re.search(WHEEL_WORD, both):
        reasons.append("7-8 позиций + колесо")
    if not models and not reasons and re.search(r"колес\w*\s+фильтр|filter\s?wheel|колесо\s+(?:для\s+)?фильтр", both):
        reasons.append("колесо фильтров (проверить число позиций)")
    excluded = bool(models or reasons) and bool(_search_any(WHEEL_EXCLUDE, both))
    bonus = 0
    if re.search(WHEEL_FILTERS, both):
        bonus += 5
    if camera["level"] != "plain":  # продаётся вместе с камерой на 533
        bonus += 3
    bonus += _price_bonus(price, rule_cfg)
    score, _ = _finish(bool(models), bool(reasons), bonus, False)
    if excluded:  # ручное колесо или 5 позиций: −10 при любом совпадении
        score -= 10
    return {"level": _level(score), "score": score, "models": models, "reasons": reasons,
            "ambiguous": False}


# ---------------------------------------------------------------- телескоп Sharpstar 61 EDPH II / III
SCOPE_B = [
    ("61EDPH без указания II/III (возможно первая версия)", r"61\s?ed\s?ph(?!\s?[23])"),
]
SCOPE_OTHER = [r"(?:76|94|120)\s?edph", r"15028", r"13028", r"\bhnt\b", r"130\s?(?:edph|ed\b|mm)"]
SCOPE_ACCESSORY = r"сумк|кейс|кольц|ring|fokuser|focuser|ссылк"
SCOPE_WORDS = r"телескоп|труб|рефрактор|tube|\bota\b|refractor|telescope"
SCOPE_BONUS = r"редуктор|корректор|reducer|flattener|кольц|\bring"


def analyze_scope(ru, mix, lat, price, rule_cfg):
    models = []
    m = re.search(r"61\s?ed\s?ph\s?([23])(?![a-z0-9])", lat)
    if m:
        models.append("Sharpstar 61EDPH " + ("II" if m.group(1) == "2" else "III"))
    both = f"{mix} {lat}"
    reasons = [name for name, pat in SCOPE_B if re.search(pat, lat)]
    if re.search(r"sharpstar", lat) and re.search(r"61\s?mm.{0,15}(?:apo|ed|refractor|рефрактор)", both):
        reasons.append("Sharpstar 61 мм рефрактор")
    if not models and not reasons and re.search(r"sharp\s?star", lat) and re.search(SCOPE_WORDS, both):
        reasons.append("Sharpstar (проверить модель)")
    excluded = bool(_search_any(SCOPE_OTHER, lat))
    accessory_only = bool(re.search(SCOPE_ACCESSORY, both)) and not re.search(SCOPE_WORDS, both)
    bonus = 4 if re.search(SCOPE_BONUS, both) else 0
    bonus += _price_bonus(price, rule_cfg)
    score, level = _finish(bool(models), bool(reasons), bonus, excluded or accessory_only)
    return {"level": level, "score": score, "models": models, "reasons": reasons,
            "ambiguous": bool(models) and excluded}


# ---------------------------------------------------------------- общий разбор
def analyze(title, body, cfg=None):
    cfg = cfg or {}
    rules = cfg.get("rules", {})
    ru, mix, lat = normalize(f"{title}\n{body}")
    price = extract_price(body)
    plain = {"level": "plain", "score": 0, "models": [], "reasons": [], "ambiguous": False}

    def enabled(name):
        return rules.get(name, {}).get("enabled", True)

    camera = analyze_camera(ru, mix, lat, price, rules.get("camera")) if enabled("camera") else dict(plain)
    wheel = analyze_wheel(ru, mix, lat, price, rules.get("wheel"), camera) if enabled("wheel") else dict(plain)
    scope = analyze_scope(ru, mix, lat, price, rules.get("scope")) if enabled("scope") else dict(plain)

    results = {"camera": camera, "wheel": wheel, "scope": scope}
    items = [name for name, r in results.items() if r["level"] != "plain"]
    levels = [results[n]["level"] for n in items]
    level = "found" if "found" in levels else ("check" if "check" in levels else "plain")
    return {**results, "items": items, "bundle": len(items) >= 2, "level": level, "price": price}
