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
# 2. تخزين موقع حارث الحي في الذاكرة
# ==========================================
hareth_live_location = {
    "lat": None,
    "lng": None,
    "timestamp": None,
    "accuracy": None,
    "speed": None,
    "device": "Hareth-Device"
}

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
        if coords is not None:
            _DYNAMIC_COORDS[key] = coords
            _save_dynamic_coords()
        else:
            _FAILED_CITIES.add(key)
    return coords


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 1)


def extract_city_coords(location_text: str, lookups_remaining: list[int] | None = None):
    if not location_text:
        return None
    lower = location_text.lower()
    for city_name, coords in EU_CITIES_COORDS.items():
        if city_name in lower:
            return coords
    with _GEO_LOCK:
        for city_name, coords in _DYNAMIC_COORDS.items():
            if city_name in lower:
                return coords
    return resolve_city_coords(location_text, lookups_remaining=lookups_remaining)


def parse_weight_to_kg(text: str):
    if not text:
        return None
    lower = text.lower()
    ton_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:t\b|ton\b|tons\b|tonnen\b|طن)', lower)
    if ton_match:
        val = float(ton_match.group(1).replace(",", "."))
        return val * 1000.0
    kg_match = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:kg\b|كجم|كيلو)', lower)
    if kg_match:
        val = float(kg_match.group(1).replace(",", "."))
        return val
    return None


def evaluate_load_for_ducato(load_text: str):
    lower = load_text.lower()

    for kw in HEAVY_TRUCK_KEYWORDS:
        if kw in lower:
            return False, f"كلمة شاحنة ثقيلة: {kw}"

    weight_kg = parse_weight_to_kg(lower)
    if weight_kg is not None and weight_kg > MAX_PAYLOAD_KG:
        return False, f"الوزن {weight_kg} كجم يتجاوز {MAX_PAYLOAD_KG} كجم"

    dim_matches = re.findall(
        r'(\d+(?:[.,]\d+)?)\s*[x×]\s*(\d+(?:[.,]\d+)?)(?:\s*[x×]\s*(\d+(?:[.,]\d+)?))?\s*(cm|m\b|سم|متر)?',
        lower
    )
    for m in dim_matches:
        unit = m[3] or ""
        factor = 100.0 if ("m" in unit and "cm" not in unit) or "متر" in unit else 1.0
        dims = []
        for x in (m[0], m[1], m[2]):
            if x:
                dims.append(float(x.replace(",", ".")) * factor)
        if dims:
            dims_sorted = sorted(dims, reverse=True)
            if dims_sorted[0] > MAX_LENGTH_CM:
                return False, f"طول {dims_sorted[0]} سم يتجاوز {MAX_LENGTH_CM} سم"
            if len(dims_sorted) > 1 and dims_sorted[1] > MAX_WIDTH_CM:
                return False, f"عرض {dims_sorted[1]} سم يتجاوز {MAX_WIDTH_CM} سم"
            if len(dims_sorted) > 2 and dims_sorted[2] > MAX_HEIGHT_CM:
                return False, f"ارتفاع {dims_sorted[2]} سم يتجاوز {MAX_HEIGHT_CM} سم"

    return True, "مناسب لـ Fiat Ducato L4H2"


def _looks_like_freight_card(text_lower: str) -> bool:
    markers = (
        "loading", "unloading", "beladung", "entladung",
        "laden", "entladen", "abholung", "zustellung",
        "abholort", "zielort", "pickup", "delivery"
    )
    if any(m in text_lower for m in markers):
        return True
    has_km = bool(re.search(r'\b\d+(?:[.,]\d+)?\s*km\b', text_lower))
    has_cargo_hint = any(k in text_lower for k in ("kg", "ton", "colli", "pallet", "palette", "goods", "distance", "entfernung"))
    return has_km and has_cargo_hint


def parse_freights_html(html_text: str, lookups_remaining: list[int] | None = None):
    soup = BeautifulSoup(html_text, "html.parser")
    raw_items = []
    sample_cards = []

    cards = soup.select("div.freight-item, div.card, tr.freight-row, article")
    if not cards:
        cards = soup.find_all(["div", "tr"], limit=160)

    hareth_lat = hareth_live_location.get("lat")
    hareth_lng = hareth_live_location.get("lng")
    has_hareth_gps = hareth_lat is not None and hareth_lng is not None

    idx = 0
    for card in cards:
        lines = [line.strip() for line in card.get_text("\n").splitlines() if line.strip()]
        if len(lines) < 4:
            continue

        joined_text = " | ".join(lines)
        if len(sample_cards) < 2 and len(joined_text) > 20:
            sample_cards.append(joined_text[:180])

        if not _looks_like_freight_card(joined_text.lower()):
            continue

        idx += 1
        origin = "غير محدد"
        destination = "غير محدد"
        for i, line in enumerate(lines):
            low = line.lower()
            if low in LOADING_LABELS and i + 1 < len(lines):
                origin = lines[i + 1]
            elif low in UNLOADING_LABELS and i + 1 < len(lines):
                destination = lines[i + 1]

        if origin == "غير محدد" or destination == "غير محدد":
            place_candidates = [
                ln for ln in lines
                if re.search(r'\b\d{2,5}\b', ln) and not re.search(r'\b\d+(?:[.,]\d+)?\s*km\b', ln.lower())
            ]
            if origin == "غير محدد" and len(place_candidates) >= 1:
                origin = place_candidates[0]
            if destination == "غير محدد" and len(place_candidates) >= 2:
                destination = place_candidates[1]

        dist_match = re.search(r'(\d+(?:[.,]\d+)?)\s*km', joined_text.lower())
        distance_km = float(dist_match.group(1).replace(",", ".")) if dist_match else 0.0
        floor_price = round(distance_km * 1.56, 2) if distance_km > 0 else 0.0

        hareth_distance_km = 9999.0
        if has_hareth_gps:
            origin_coords = extract_city_coords(origin, lookups_remaining=lookups_remaining)
            if origin_coords:
                hareth_distance_km = haversine_km(
                    float(hareth_lat), float(hareth_lng), origin_coords[0], origin_coords[1]
                )

        link_el = card.find("a", href=True)
        href = link_el["href"] if link_el else ""
        if href and href.startswith("/"):
            offer_url = f"https://e-kurier.net{href}"
        elif href.startswith("http"):
            offer_url = href
        else:
            offer_url = "https://e-kurier.net/portal/freights"

        accepted, reason = evaluate_load_for_ducato(joined_text)

        item = {
            "id": idx,
            "origin": origin,
            "destination": destination,
            "distance_km": distance_km,
            "floor_price": floor_price,
            "hareth_distance_km": hareth_distance_km,
            "max_payload_kg": MAX_PAYLOAD_KG,
            "offer_url": offer_url,
            "raw_lines": lines[:45],
            "vehicle_match": "Fiat Ducato L4H2",
            "accepted": accepted,
            "filter_reason": reason,
        }
        raw_items.append(item)

    accepted_loads = [x for x in raw_items if x["accepted"]]
    accepted_loads.sort(key=lambda x: x["hareth_distance_km"])

    return accepted_loads, raw_items, len(cards), sample_cards


def get_live_hareth_loads():
    max_pages = int(request.args.get("max_pages", "10"))
    max_pages = max(1, min(max_pages, 15))

    cookie_header = _clean_cookie_value(os.environ.get("EKURIER_COOKIE", ""))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "de,en;q=0.9",
    }
    if cookie_header:
        headers["Cookie"] = cookie_header

    all_accepted = []
    all_audit = []
    pages_scanned = 0
    lookups_remaining = [5]
    diag = {
        "cookie_configured": bool(cookie_header),
        "first_page_status": None,
        "first_page_length": 0,
        "first_page_cards": 0,
        "first_page_snippet": "",
        "sample_cards": [],
    }

    try:
        with httpx.Client(timeout=15.0, headers=headers, follow_redirects=True) as client:
            for page in range(1, max_pages + 1):
                url = f"https://e-kurier.net/portal/freights?page={page}"
                resp = client.get(url)
                if page == 1:
                    diag["first_page_status"] = resp.status_code
                    diag["first_page_length"] = len(resp.text or "")
                    clean_snippet = re.sub(r"\s+", " ", (resp.text or "")).strip()[:350]
                    diag["first_page_snippet"] = clean_snippet

                if resp.status_code != 200 or not resp.text.strip():
                    break
                pages_scanned += 1
                accepted, audit, cards_count, samples = parse_freights_html(
                    resp.text, lookups_remaining=lookups_remaining
                )
                if page == 1:
                    diag["first_page_cards"] = cards_count
                    diag["sample_cards"] = samples

                if not audit:
                    break
                all_accepted.extend(accepted)
                all_audit.extend(audit)

        if not all_audit:
            print(
                f"[DIAGNOSTIC] empty loads: status={diag['first_page_status']} "
                f"len={diag['first_page_length']} cards={diag['first_page_cards']} "
                f"cookie={diag['cookie_configured']} samples={diag['sample_cards']!r}",
                flush=True,
            )

        all_accepted.sort(key=lambda x: x["hareth_distance_km"])

        payload = {
            "status": "success",
            "driver": "حارث",
            "gps_active": hareth_live_location.get("lat") is not None,
            "driver_location": hareth_live_location,
            "pages_scanned": pages_scanned,
            "total_raw_before_filter": len(all_audit),
            "total_fetched": len(all_accepted),
            "sorted_by": "nearest_to_hareth_live_gps",
            "vehicle_specs": {
                "model": "Fiat Ducato L4H2",
                "max_payload_kg": MAX_PAYLOAD_KG,
                "max_payload_tons": MAX_PAYLOAD_KG / 1000.0,
                "cargo_length_cm": MAX_LENGTH_CM,
                "cargo_width_cm": MAX_WIDTH_CM,
                "max_height_cm": MAX_HEIGHT_CM,
            },
            "loads": all_accepted,
            "audit_comparison": all_audit,
            "diagnostics": diag,
        }
        return jsonify(payload), 200
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
        }), 500


@app.route("/", methods=["GET", "HEAD"])
def home():
    return jsonify({
        "status": "online",
        "service": "eKurier Hareth Agent",
        "gps_active": hareth_live_location.get("lat") is not None,
        "dynamic_cities_count": len(_DYNAMIC_COORDS),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }), 200


@app.route("/api/update-gps", methods=["POST"])
def update_gps():
    data = request.get_json(silent=True) or {}
    lat = data.get("lat")
    lng = data.get("lng")
    if lat is None or lng is None:
        return jsonify({"status": "error", "message": "lat and lng are required"}), 400

    hareth_live_location["lat"] = float(lat)
    hareth_live_location["lng"] = float(lng)
    hareth_live_location["accuracy"] = data.get("accuracy")
    hareth_live_location["speed"] = data.get("speed")
    hareth_live_location["device"] = data.get("device", "Hareth-Device")
    hareth_live_location["timestamp"] = data.get("timestamp") or datetime.now(timezone.utc).isoformat()

    return jsonify({
        "status": "success",
        "location": hareth_live_location,
    }), 200


@app.route("/api/get-gps", methods=["GET"])
def get_gps():
    return jsonify({
        "status": "success",
        "location": hareth_live_location,
    }), 200


@app.route("/api/loads", methods=["GET"])
def api_loads():
    return get_live_hareth_loads()


@app.route("/api/loads/before-filter", methods=["GET"])
def loads_before_filter():
    resp, code = get_live_hareth_loads()
    if code != 200:
        return resp, code
    payload = resp.get_json() or {}
    items = payload.get("audit_comparison", [])
    return jsonify({
        "status": "success",
        "stage": "before_filter",
        "pages_scanned": payload.get("pages_scanned", 0),
        "total": len(items),
        "items": items,
    }), 200


@app.route("/api/loads/after-filter", methods=["GET"])
def loads_after_filter():
    resp, code = get_live_hareth_loads()
    if code != 200:
        return resp, code
    payload = resp.get_json() or {}
    items = payload.get("loads", [])
    return jsonify({
        "status": "success",
        "stage": "after_filter",
        "pages_scanned": payload.get("pages_scanned", 0),
        "total": len(items),
        "items": items,
    }), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
