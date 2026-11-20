import os
import re
import math
import time
from datetime import datetime
import httpx
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify

app = Flask(__name__)

HARETH_WHATSAPP_NUMBER = "whatsapp:+4917656970147"

# مواصفات سيارة حارث المعتمدة (Fiat Ducato L4H2)
HARETH_VEHICLE_SPECS = {
    "model": "Fiat Ducato L4H2",
    "max_payload_kg": 1360.0,
    "max_payload_tons": 1.36,
    "cargo_length_cm": 375.0,
    "cargo_width_cm": 170.0,
    "wheel_arch_width_cm": 135.0,
    "wheel_arch_protrusion_cm": 27.0,
}

REAL_DRIVER_LOCATION = {
    "lat": None,
    "lng": None,
    "timestamp": "لم يتم استلام موقع GPS من الهاتف بعد",
}

SESSION_STORE = {
    "client": None,
    "last_login_time": 0,
}

EU_CITIES_COORDS = {
    "münchen": (48.1351, 11.5820), "munich": (48.1351, 11.5820),
    "ingolstadt": (48.7665, 11.4258),
    "nürnberg": (49.4521, 11.0767), "nuremberg": (49.4521, 11.0767),
    "frankfurt": (50.1109, 8.6821),
    "stuttgart": (48.7758, 9.1829),
    "berlin": (52.5200, 13.4050),
    "hamburg": (53.5511, 9.9937),
    "köln": (50.9375, 6.9603), "cologne": (50.9375, 6.9603),
    "düsseldorf": (51.2217, 6.7762),
    "dortmund": (51.5136, 7.4653),
    "leipzig": (51.3397, 12.3731),
    "bremen": (53.0793, 8.8017),
    "hannover": (52.3759, 9.7320),
    "essen": (51.4556, 7.0116),
    "dresden": (51.0504, 13.7373),
    "paris": (48.8566, 2.3522),
    "vienna": (48.2082, 16.3738), "wien": (48.2082, 16.3738),
    "amsterdam": (52.3676, 4.9041),
    "brussels": (50.8503, 4.3517),
    "prague": (50.0755, 14.4378),
    "zossen": (52.2167, 13.4333),
    "crailsheim": (49.1333, 10.0667),
    "warngau": (47.8500, 11.7500),
    "warstein": (51.4500, 8.3500),
    "erkrath": (51.2167, 6.9167),
    "amstetten": (48.5167, 9.8667),
    "traiskirchen": (48.0166, 16.2833),
    "amberg": (49.4447, 11.8536),
    "villingen": (48.0625, 8.4619),
    "styregg": (48.2500, 14.4167),
    "kappelrodeck": (48.5667, 8.1000),
    "calden": (51.4167, 9.4000),
    "mannheim": (49.4875, 8.4660),
    "antwerpen": (51.2194, 4.4025),
    "stutensee": (49.0833, 8.4667),
    "graz": (47.0707, 15.4395),
    "strzelce": (50.5100, 18.2833),
    "fahrenzhausen": (48.3333, 11.6000),
    "sassenberg": (51.9833, 8.0333),
    "bad soden": (50.3167, 9.5667),
    "augsburg": (48.3705, 10.8978),
    "burscheid": (51.1464, 7.1128),
    "aichtal": (48.6333, 9.2667),
    "haltern": (51.7458, 7.1853),
    "sosnowiec": (50.2833, 19.2667),
    "kupferzell": (49.2333, 9.6833),
    "stapelfeld": (53.5833, 10.2167),
    "siegen": (50.8749, 8.0229),
    "schmalkalden": (50.7222, 10.4514),
    "karlsruhe": (49.0069, 8.4037),
    "friedrichshall": (49.2333, 9.2167),
    "novo mesto": (45.8000, 15.1667),
    "waidhofen": (48.8167, 15.2833),
    "werdohl": (51.2500, 7.7500),
    "schwechat": (48.1408, 16.4719),
    "gründau": (50.2167, 9.1333),
    "schwedt": (53.0667, 14.3000),
    "ortenburg": (48.6667, 13.3167),
    "bonn": (50.7374, 7.0982),
    "monte san pietro": (44.3956, 11.1539),
    "las palmas": (28.1235, -15.4363),
    "craiova": (44.3302, 23.7949),
    "sighisoara": (46.2197, 24.7964),
    "schwandorf": (49.3267, 12.1047),
    "göttingen": (51.5413, 9.9158),
    "wnzelsau": (49.2750, 9.7014),
    "ingersheim": (48.9675, 9.1931),
    "krefeld": (51.3388, 6.5853),
    "hofkirchen": (48.3667, 13.8667),
    "troisdorf": (50.8161, 7.1556),
    "lastrup": (52.7833, 7.9833),
}


def _parse_number(num_str: str):
    try:
        return float(num_str.replace(" ", "").replace(",", "."))
    except Exception:
        return None


def _clean_text_for_matching(text: str) -> str:
    cleaned = text.lower()
    cleaned = cleaned.replace("\ufffd", " ")
    cleaned = re.sub(r"[*#]+", " ", cleaned)
    cleaned = re.sub(r"\b\d{4,6}\b", " ", cleaned)
    cleaned = re.sub(
