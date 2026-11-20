from flask import Flask, jsonify, request
from bs4 import BeautifulSoup
import httpx
import math
import re
import os
import json
import threading
import time
from datetime import datetime, timezone

app = Flask(__name__)

# ==========================================
# 1. إعدادات السيارة (Fiat Ducato L4H2)
# ==========================================
MAX_PAYLOAD_KG = 1360.0
MAX_LENGTH_CM = 375.0
MAX_WIDTH_CM = 170.0
MAX_HEIGHT_CM = 195.0

HEAVY_TRUCK_KEYWORDS = [
    "7.5t", "7.5 t", "12t", "12 t", "18t", "18 t", "24t", "24 t",
    "40t", "40 t", "sattel", "saddle", "mega", "jumbo", "tautliner",
    "planensattel", "kühl", "frigo", "reefer", "wechselbrücke", "bdf",
    "container", "kipper", "autotransporter", "schwertransport",
    "lkw", "truck", "شاحنة", "تريلا", "مقطورة"
]

LOADING_LABELS = {
    "loading", "loading:", "beladung", "beladung:",
    "laden", "laden:", "abholung", "abholung:",
    "abholort", "abholort:", "pickup", "pickup:",
    "von", "von:"
}
UNLOADING_LABELS = {
    "unloading", "unloading:", "entladung", "entladung:",
    "entladen", "entladen:", "zustellung", "zustellung:",
    "zielort", "zielort:", "delivery", "delivery:",
    "nach", "nach:"
}

# ==========================================
# 2. تخزين موقع حارث الحي والكوكي في الذاكرة
# ==========================================
hareth_live_location = {
    "lat": None,
    "lng": None,
    "timestamp": None,
    "accuracy": None,
    "speed": None,
    "device": "Hareth-Device"
}

_COOKIE_LOCK = threading.Lock()
_RUNTIME_COOKIE: str | None = None
_LAST_LOGIN_STATUS: str = "not_attempted"

# ==========================================
# 3. قاموس إحداثيات المدن الأوروبية وألمانيا
# ==========================================
EU_CITIES_COORDS = {
    # ألمانيا
    "berlin": (52.5200, 13.4050),
    "برلين": (52.5200, 13.4050),
    "münchen": (48.1351, 11.5820),
    "munich": (48.1351, 11.5820),
    "ميونخ": (48.1351, 11.5820),
    "hamburg": (53.5511, 9.9937),
    "هامبورغ": (53.5511, 9.9937),
    "köln": (50.9375, 6.9603),
    "cologne": (50.9375, 6.9603),
    "كولونيا": (50.9375, 6.9603),
    "frankfurt": (50.1109, 8.6821),
    "frankfurt am main": (50.1109, 8.6821),
    "فرانكفورت": (50.1109, 8.6821),
    "stuttgart": (48.7758, 9.1829),
    "شتوتغارت": (48.7758, 9.1829),
    "düsseldorf": (51.2277, 6.7735),
    "dusseldorf": (51.2277, 6.7735),
    "دوسلدورف": (51.2277, 6.7735),
    "dortmund": (51.5136, 7.4653),
    "دورتموند": (51.5136, 7.4653),
    "essen": (51.4556, 7.0116),
    "إيسن": (51.4556, 7.0116),
    "leipzig": (51.3397, 12.3731),
    "لايبزيغ": (51.3397, 12.3731),
    "bremen": (53.0793, 8.8017),
    "بريمن": (53.0793, 8.8017),
    "dresden": (51.0504, 13.7373),
    "دريسدن": (51.0504, 13.7373),
    "hannover": (52.3759, 9.7320),
    "هانوفر": (52.3759, 9.7320),
    "nürnberg": (49.4521, 11.0767),
    "nuremberg": (49.4521, 11.0767),
    "نورنبرغ": (49.4521, 11.0767),
    "duisburg": (51.4344, 6.7623),
    "دويسبورغ": (51.4344, 6.7623),
    "bochum": (51.4818, 7.2162),
    "wuppertal": (51.2562, 7.1508),
    "فوبرتال": (51.2562, 7.1508),
    "bielefeld": (52.0302, 8.5325),
    "bonn": (50.7374, 7.0982),
    "münster": (51.9607, 7.6261),
    "karlsruhe": (49.0069, 8.4037),
    "mannheim": (49.4875, 8.4660),
    "مانهايم": (49.4875, 8.4660),
    "augsburg": (48.3705, 10.8978),
    "أوغسبورغ": (48.3705, 10.8978),
    "wiesbaden": (50.0826, 8.2400),
    "mönchengladbach": (51.1805, 6.4428),
    "gelsenkirchen": (51.5177, 7.0857),
    "aachen": (50.7753, 6.0839),
    "braunschweig": (52.2689, 10.5268),
    "براونشفايغ": (52.2689, 10.5268),
    "chemnitz": (50.8278, 12.9214),
    "kiel": (54.3233, 10.1228),
    "halle": (51.4969, 11.9688),
    "magdeburg": (52.1205, 11.6276),
    "ماغديبورغ": (52.1205, 11.6276),
    "freiburg": (47.9990, 7.8421),
    "فرايبورغ": (47.9990, 7.8421),
    "krefeld": (51.3388, 6.5853),
    "lübeck": (53.8655, 10.6866),
    "oberhausen": (51.4963, 6.8638),
    "erfurt": (50.9848, 11.0299),
    "mainz": (49.9929, 8.2473),
    "rostock": (54.0924, 12.0991),
    "kassel": (51.3127, 9.4797),
    "hagen": (51.3671, 7.4633),
    "saarbrücken": (49.2401, 6.9969),
    "hamm": (51.6739, 7.8160),
    "ludwigshafen": (49.4774, 8.4452),
    "oldenburg": (53.1435, 8.2146),
    "mülheim": (51.4275, 6.8825),
    "osnabrück": (52.2799, 8.0472),
    "leverkusen": (51.0459, 6.9844),
    "heidelberg": (49.3988, 8.6724),
    "هايدلبرغ": (49.3988, 8.6724),
    "solingen": (51.1652, 7.0671),
    "سولينجن": (51.1652, 7.0671),
    "darmstadt": (49.8728, 8.6512),
    "herne": (51.5388, 7.2257),
    "regensburg": (49.0134, 12.1016),
    "ريغنسبورغ": (49.0134, 12.1016),
    "ingolstadt": (48.7665, 11.4258),
    "paderborn": (51.7189, 8.7575),
    "wolfsburg": (52.4227, 10.7865),
    "würzburg": (49.7913, 9.9534),
    "ulm": (48.4011, 9.9876),
    "heilbronn": (49.1427, 9.2109),
    "göttingen": (51.5413, 9.9158),
    "recklinghausen": (51.6141, 7.1979),
    "bottrop": (51.5215, 6.9292),
    "بوتروب": (51.5215, 6.9292),
    "remscheid": (51.1787, 7.1938),
    "bremerhaven": (53.5396, 8.5809),
    "koblenz": (50.3569, 7.5890),
    "bergisch gladbach": (50.9918, 7.1367),
    "jena": (50.9272, 11.5892),
    "erlangen": (49.5897, 11.0039),
    "إرلانجن": (49.5897, 11.0039),
    "trier": (49.7499, 6.6371),
    "moers": (51.4517, 6.6250),
    "siegen": (50.8744, 8.0243),
    "hildesheim": (52.1548, 9.9580),
    "salzgitter": (52.1503, 10.3595),
    "gütersloh": (51.9032, 8.3858),
    "passau": (48.5667, 13.4319),
    "leuna": (51.3167, 12.0167),
    "freiberg am neckar": (48.9333, 13.3333),
    "freiberg": (50.9119, 13.3428),
    "kelsterbach": (50.0642, 8.5311),
    "neutraubling": (48.9939, 12.2039),
    "bergkirchen": (48.2553, 11.3631),
    "freigericht": (50.1456, 9.1806),
    "sinntal": (50.2833, 9.6333),
    "rangendingen": (48.3817, 8.8861),
    "bühl": (48.6958, 8.1353),
    "baunatal": (51.2519, 9.4239),
    "driedorf": (50.6333, 8.1667),
    "einbeck": (51.8167, 9.8667),
    "ahlen": (51.7633, 7.8906),
    "spenge": (52.1419, 8.4819),
    "wilnsdorf": (50.8000, 8.1000),
    "bad waldsee": (47.9219, 9.7503),
    "trierweiler": (49.7764, 6.5636),
    "horb am neckar": (48.4453, 8.6906),
    "nordhorn": (52.4333, 7.0667),
    "lauterbach": (50.6383, 9.3972),
    "norderstedt": (53.7000, 10.0000),
    "billerbeck": (51.9772, 7.2911),
    "wimsheim": (48.8478, 8.8489),
    "amerang": (48.0000, 12.3167),
    "kleinlangheim": (49.7667, 10.2833),
    "rosswein": (51.0642, 13.1842),
    "gollhofen": (49.5500, 10.1667),
    "vierkirchen": (48.3667, 11.4500),
    "egelsbach": (49.9667, 8.6667),
    "atting": (48.8833, 12.5667),
    "marktheidenfeld": (49.8458, 9.6022),
    "geislingen": (48.6228, 9.8322),
    "sindelfingen": (48.7133, 9.0028),
    "ratingen": (51.3000, 6.8500),
    "melle": (52.2033, 8.3389),
    "velten": (52.6908, 13.1758),
    "nauen": (52.6064, 12.8758),
    "lahr": (48.3403, 7.8719),
    "eichstätt": (48.8919, 11.1878),
    "rheda-wiedenbrück": (51.8417, 8.3000),
    "röthenbach": (49.4833, 11.2333),
    "springe": (52.2089, 9.5558),
    "hösbach": (50.0089, 9.2169),
    "oberding": (48.3333, 11.7167),
    "röttingen": (49.5106, 9.9672),
    "burgwedel": (52.4917, 9.8583),
    "neuwied": (50.4286, 7.4614),
    "herten": (51.5964, 7.1369),
    "neufahrn": (48.3167, 11.6667),
    "neufahrn bei freising": (48.3167, 11.6667),
    "hürth": (50.8781, 6.8764),
    "dietzenbach": (50.0089, 8.7753),
    "bad säckingen": (47.5536, 7.9519),
    "schongau": (47.8136, 10.8969),
    "köthen": (51.7514, 11.9739),
    "bernau": (52.6792, 13.5872),
    "bernau bei berlin": (52.6792, 13.5872),
    "schwelm": (51.2889, 7.2944),
    "filderstadt": (48.6667, 9.2167),
    "pfreimd": (49.4936, 12.1819),
    "planegg": (48.1061, 11.4253),
    "troisdorf": (50.8161, 7.1556),
    "luckau": (51.8492, 13.7131),
    "gummersbach": (51.0239, 7.5628),
    "neunkirchen": (49.3447, 7.1797),
    "ungerhausen": (48.0167, 10.2667),
    "baden-baden": (48.7606, 8.2398),
    "sonnefeld": (50.2217, 11.1583),
    "herzebrock-clarholz": (51.8875, 8.2333),
    "bocholt": (51.8333, 6.6167),
    "zossen": (52.2167, 13.4500),

    # النمسا
    "wien": (48.2082, 16.3738),
    "vienna": (48.2082, 16.3738),
    "graz": (47.0707, 15.4395),
    "linz": (48.3069, 14.2858),
    "salzburg": (47.8095, 13.0550),
    "innsbruck": (47.2692, 11.4041),
    "klagenfurt": (46.6247, 14.3053),
    "schwechat": (48.1389, 16.4731),
    "zeltweg": (47.1922, 14.7497),

    # سويسرا
    "zürich": (47.3769, 8.5417),
    "zurich": (47.3769, 8.5417),
    "geneva": (46.2044, 6.1432),
    "genf": (46.2044, 6.1432),
    "basel": (47.5596, 7.5886),
    "bern": (46.9480, 7.4474),
    "lausanne": (46.5197, 6.6323),
    "winterthur": (47.4988, 8.7237),
    "lucerne": (47.0502, 8.3093),
    "luzern": (47.0502, 8.3093),
    "zuchwil": (47.2089, 7.5628),
    "schlieren": (47.3972, 8.4489),

    # هولندا
    "amsterdam": (52.3676, 4.9041),
    "rotterdam": (51.9244, 4.4777),
    "the hague": (52.0705, 4.3007),
    "den haag": (52.0705, 4.3007),
    "utrecht": (52.0907, 5.1214),
    "eindhoven": (51.4416, 5.4697),
    "tilburg": (51.5555, 5.0913),
    "groningen": (53.2194, 6.5665),
    "breda": (51.5719, 4.7683),
    "nijmegen": (51.8126, 5.8372),
    "arnhem": (51.9851, 5.8987),

    # بلجيكا
    "brussels": (50.8503, 4.3517),
    "bruxelles": (50.8503, 4.3517),
    "antwerp": (51.2194, 4.4025),
    "antwerpen": (51.2194, 4.4025),
    "ghent": (51.0543, 3.7174),
    "gent": (51.0543, 3.7174),
    "charleroi": (50.4108, 4.4446),
    "liège": (50.6326, 5.5797),
    "liege": (50.6326, 5.5797),
    "bruges": (51.2093, 3.2247),
    "willebroek": (51.0619, 4.3608),

    # فرنسا
    "paris": (48.8566, 2.3522),
    "marseille": (43.2965, 5.3698),
    "lyon": (45.7640, 4.8357),
    "toulouse": (43.6047, 1.4442),
    "nice": (43.7102, 7.2620),
    "nantes": (47.2184, -1.5536),
    "strasbourg": (48.5734, 7.7521),
    "montpellier": (43.6108, 3.8767),
    "bordeaux": (44.8378, -0.5792),
    "lille": (50.6292, 3.0573),

    # إيطاليا
    "milano": (45.4642, 9.1900),
    "milan": (45.4642, 9.1900),
    "roma": (41.9028, 12.4964),
    "rome": (41.9028, 12.4964),
    "torino": (45.0703, 7.6869),
    "turin": (45.0703, 7.6869),
    "napoli": (40.8518, 14.2681),
    "naples": (40.8518, 14.2681),
    "bologna": (44.4949, 11.3426),
    "firenze": (43.7696, 11.2558),
    "florence": (43.7696, 11.2558),
    "venezia": (45.4408, 12.3155),
    "venice": (45.4408, 12.3155),
    "verona": (45.4384, 10.9916),
    "genova": (44.4056, 8.9463),
    "palermo": (38.1157, 13.3615),
    "lucera": (41.5075, 15.3350),
    "livigno": (46.5389, 10.1356),

    # بولندا / التشيك / سلوفاكيا / المجر / رومانيا / السويد
    "warsaw": (52.2297, 21.0122),
    "warszawa": (52.2297, 21.0122),
    "krakow": (50.0647, 19.9450),
    "wroclaw": (51.1079, 17.0385),
    "praha": (50.0755, 14.4378),
    "prague": (50.0755, 14.4378),
    "brno": (49.1951, 16.6068),
    "zebrak": (49.8756, 13.8894),
    "rokycany": (49.7425, 13.5947),
    "bratislava": (48.1486, 17.1077),
    "budapest": (47.4979, 19.0402),
    "bucharest": (44.4268, 26.1025),
    "sighisoara": (46.2197, 24.7964),
    "uppsala": (59.8586, 17.6389),
    "أوبسالا": (59.8586, 17.6389),
    "stockholm": (59.3293, 18.0686),
    "gothenburg": (57.7089, 11.9746),
}

# ==========================================
# 4. التضمين التلقائي الآمن للمدن غير الموجودة
# ==========================================
DYNAMIC_CITIES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dynamic_cities.json")
_GEO_LOCK = threading.Lock()
_DYNAMIC_COORDS: dict[str, tuple[float, float]] = {}
_FAILED_CITIES: set[str] = set()


def _load_dynamic_coords() -> None:
    global _DYNAMIC_COORDS
    if os.path.exists(DYNAMIC_CITIES_FILE):
        try:
            with open(DYNAMIC_CITIES_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
                if isinstance(raw, dict):
                    _DYNAMIC_COORDS = {
                        str(k).strip().lower(): (float(v[0]), float(v[1]))
                        for k, v in raw.items()
                        if isinstance(v, (list, tuple)) and len(v) == 2
                    }
        except Exception:
            pass


def _save_dynamic_coords() -> None:
    try:
        with open(DYNAMIC_CITIES_FILE, "w", encoding="utf-8") as f:
            json.dump(
                {k: [v[0], v[1]] for k, v in sorted(_DYNAMIC_COORDS.items())},
                f,
                ensure_ascii=False,
                indent=2,
            )
    except Exception:
        pass


_load_dynamic_coords()


def _clean_cookie_value(raw_cookie: str) -> str:
    cleaned = (raw_cookie or "").replace("\r", "").replace("\n", "").strip()
    if len(cleaned) >= 2 and cleaned[0] == cleaned[-1] and cleaned[0] in ("'", '"'):
        cleaned = cleaned[1:-1].strip()
    return cleaned


def _get_active_cookie() -> str:
    with _COOKIE_LOCK:
        if _RUNTIME_COOKIE:
            return _RUNTIME_COOKIE
    return _clean_cookie_value(os.environ.get("EKURIER_COOKIE", ""))


def _set_runtime_cookie(new_cookie: str) -> str:
    global _RUNTIME_COOKIE
    cleaned = _clean_cookie_value(new_cookie)
    with _COOKIE_LOCK:
        _RUNTIME_COOKIE = cleaned
    return cleaned


def _merge_cookies_from_client(client: httpx.Client, current_cookie: str) -> str:
    jar_pairs = []
    seen = set()
    for c in client.cookies.jar:
        if c.name and c.value is not None:
            jar_pairs.append((c.name, c.value))
            seen.add(c.name)

    existing_parts = []
    if current_cookie:
        for part in current_cookie.split(";"):
            p = part.strip()
            if not p or "=" not in p:
                continue
            k = p.split("=", 1)[0].strip()
            if k not in seen:
                existing_parts.append(p)

    for name, val in jar_pairs:
        existing_parts.append(f"{name}={val}")

    merged = "; ".join(existing_parts)
    if merged:
        _set_runtime_cookie(merged)
    return merged


def _is_login_page(html_text: str) -> bool:
    low = (html_text or "").lower()
    return (
        ("e-mail" in low or "email" in low)
        and ("passwort" in low or "password" in low)
        and ("anmelden" in low or "login" in low)
    )


def _try_auto_login(client: httpx.Client, login_page_html: str, current_cookie: str) -> str:
    global _LAST_LOGIN_STATUS
    email = (os.environ.get("EKURIER_USER") or os.environ.get("EKURIER_EMAIL") or "").strip()
    password = (os.environ.get("EKURIER_PASS") or os.environ.get("EKURIER_PASSWORD") or "").strip()
    if not email or not password:
        _LAST_LOGIN_STATUS = "missing_credentials"
        return current_cookie

    soup = BeautifulSoup(login_page_html or "", "html.parser")
    csrf_token = ""
    meta_csrf = soup.find("meta", attrs={"name": "csrf-token"})
    if meta_csrf and meta_csrf.get("content"):
        csrf_token = meta_csrf["content"].strip()

    form = soup.find("form")
    action_url = "https://e-kurier.net/login"
    payload: dict[str, str] = {}

    if form:
        act = (form.get("action") or "").strip()
        if act.startswith("http"):
            action_url = act
        elif act.startswith("/"):
            action_url = f"https://e-kurier.net{act}"

        for inp in form.find_all("input"):
            name = (inp.get("name") or "").strip()
            if not name:
                continue
            itype = (inp.get("type") or "").lower()
            val = inp.get("value") or ""
            nlow = name.lower()
            if itype == "password" or "pass" in nlow:
                payload[name] = password
            elif itype == "email" or "mail" in nlow or "login" in nlow or "user" in nlow:
                payload[name] = email
            elif "token" in nlow or "csrf" in nlow:
                payload[name] = val or csrf_token
            elif itype in ("hidden", "checkbox", "radio"):
                payload[name] = val

    if not payload:
        payload = {"email": email, "password": password}
        if csrf_token:
            payload["_token"] = csrf_token

    post_headers = {
        "Referer": "https://e-kurier.net/portal/freights",
        "Origin": "https://e-kurier.net",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    if csrf_token:
        post_headers["X-CSRF-TOKEN"] = csrf_token

    try:
        resp = client.post(action_url, data=payload, headers=post_headers)
        merged = _merge_cookies_from_client(client, current_cookie)
        if resp.status_code in (200, 302, 303) and not _is_login_page(resp.text or ""):
            _LAST_LOGIN_STATUS = f"ok_{resp.status_code}"
            return merged
        _LAST_LOGIN_STATUS = f"failed_{resp.status_code}"
    except Exception as e:
        _LAST_LOGIN_STATUS = f"error:{type(e).__name__}"

    return current_cookie


def _normalize_city_name(raw: str) -> str:
    s = (raw or "").strip().lower()
    s = re.sub(r"\b[a-z]{1,3}[-\s]?\d[\d\w\*]*\b", " ", s, flags=re.IGNORECASE)
    s = re.sub(r"\b\d{2,5}[\*\w]*\b", " ", s)
    s = s.replace("*", " ")
    s = re.sub(r"\s+", " ", s).strip(" ,-/")
    return s


def _geocode_city_lightweight(city_query: str) -> tuple[float, float] | None:
    if not city_query or len(city_query) < 2:
        return None
    headers = {
        "User-Agent": "eKurier-Hareth-Agent/1.0 (dispatch-assistant)",
        "Accept": "application/json",
    }
    params = {
        "q": city_query,
        "format": "json",
        "limit": 1,
    }
    try:
        with httpx.Client(timeout=2.0, headers=headers) as client:
            resp = client.get("https://nominatim.openstreetmap.org/search", params=params)
            if resp.status_code != 200:
                return None
            data = resp.json()
            if isinstance(data, list) and data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                return (lat, lon)
    except Exception:
        return None
    return None


def resolve_city_coords(raw_location: str, lookups_remaining: list[int] | None = None) -> tuple[float, float] | None:
    key = _normalize_city_name(raw_location)
    if not key:
        return None

    if key in EU_CITIES_COORDS:
        return EU_CITIES_COORDS[key]

    with _GEO_LOCK:
        if key in _DYNAMIC_COORDS:
            return _DYNAMIC_COORDS[key]
        if key in _FAILED_CITIES:
            return None
        if lookups_remaining is not None and lookups_remaining[0] <= 0:
            return None
        if lookups_remaining is not None:
            lookups_remaining[0] -= 1

    time.sleep(1.05)
    coords = _geocode_city_lightweight(key)
    with _GEO_LOCK:
