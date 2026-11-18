import os
import re
import math
import time
import httpx
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
HARETH_WHATSAPP_NUMBER = "whatsapp:+4917656970147"

REAL_DRIVER_LOCATION = {
    "lat": None,
    "lng": None,
    "timestamp": "لم يتم استلام موقع GPS من الهاتف بعد"
}

SESSION_STORE = {
    "client": None,
    "last_login_time": 0
}

# قاموس إحداثيات المدن الأوروبية الكبرى لضمان السرعة الفائقة والفلترة الفورية
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
    "karlsruhe": (49.0069, 8.4037),
    "friedrichshall": (49.2333, 9.2167),
    "novo mesto": (45.8000, 15.1667),
    "waidhofen": (48.8167, 15.2833),
    "werdohl": (51.2500, 7.7500),
    "schwechat": (48.1408, 16.4719),
    "gründau": (50.2167, 9.1333),
    "schwedt": (53.0667, 14.3000),
    "ortenburg": (48.6667, 13.3167),
    "bonn": (50.7374, 7.0982)
}

def get_active_client():
    current_time = time.time()
    if SESSION_STORE["client"] is not None and (current_time - SESSION_STORE["last_login_time"] < 1800):
        return SESSION_STORE["client"]

    username = os.environ.get("EKURIER_USER", "")
    password = os.environ.get("EKURIER_PASS", "")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    client = httpx.Client(headers=headers, follow_redirects=True, timeout=30.0)
    try:
        login_page_url = "https://e-kurier.net/portal/login"
        login_page = client.get(login_page_url)
        soup_login = BeautifulSoup(login_page.text, 'html.parser')
        
        form_tag = soup_login.find('form')
        form_action = login_page_url
        if form_tag and form_tag.get('action'):
            action_attr = form_tag.get('action')
            if action_attr.startswith('http'):
                form_action = action_attr
            elif action_attr.startswith('/'):
                form_action = f"https://e-kurier.net{action_attr}"
            else:
                form_action = f"https://e-kurier.net/portal/{action_attr}"

        payload = {}
        if form_tag:
            for input_tag in form_tag.find_all('input'):
                name = input_tag.get('name')
                value = input_tag.get('value', '')
                if name:
                    payload[name] = value

        payload['email'] = username
        payload['password'] = password
        
        login_res = client.post(form_action, data=payload)
        SESSION_STORE["client"] = client
        SESSION_STORE["last_login_time"] = current_time
        return client
    except Exception as e:
        print(f"❌ [SESSION ERROR]: {e}")
        return client

def calculate_fast_road_distance(h_lat, h_lng, card_text):
    target_coords = None
    text_lower = card_text.lower()
    
    for city, coords in EU_CITIES_COORDS.items():
        if city in text_lower:
            target_coords = coords
            break

    if target_coords:
        c_lat, c_lng = target_coords
        R = 6371.0
        dlat = math.radians(c_lat - h_lat)
        dlon = math.radians(c_lng - h_lng)
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(h_lat)) * math.cos(math.radians(c_lat)) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        road_dist = R * c * 1.25
        return round(road_dist, 1)
    
    return 500.0

@app.route("/api/update-gps", methods=["POST"])
def update_gps():
    try:
        data = request.get_json()
        if data and 'lat' in data and 'lng' in data:
            REAL_DRIVER_LOCATION['lat'] = float(data['lat'])
            REAL_DRIVER_LOCATION['lng'] = float(data['lng'])
            REAL_DRIVER_LOCATION['timestamp'] = data.get('timestamp', 'محدث الآن')
            return jsonify({"status": "success", "location": REAL_DRIVER_LOCATION}), 200
        return jsonify({"status": "error", "message": "بيانات غير صالحة"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/get-gps", methods=["GET"])
def get_gps():
    return jsonify({"status": "success", "driver": "حارث", "location": REAL_DRIVER_LOCATION}), 200

@app.route("/api/loads", methods=["GET"])
def get_live_hareth_loads():
    try:
        req_lat = request.args.get('lat', type=float)
        req_lng = request.args.get('lng', type=float)

        if req_lat is not None and req_lng is not None:
            hareth_lat, hareth_lng = req_lat, req_lng
            REAL_DRIVER_LOCATION['lat'] = hareth_lat
            REAL_DRIVER_LOCATION['lng'] = hareth_lng
        else:
            hareth_lat = REAL_DRIVER_LOCATION.get('lat')
            hareth_lng = REAL_DRIVER_LOCATION.get('lng')

        client = get_active_client()
        freights_url = "https://e-kurier.net/portal/freights"

        all_scraped_loads = []
        for page_num in range(1, 3):
            target_page = f"{freights_url}?page={page_num}"
            response = client.get(target_page)
            
            if "login" in str(response.url).lower():
                SESSION_STORE["client"] = None
                client = get_active_client()
                response = client.get(target_page)

            if response.status_code == 200 and "login" not in str(response.url).lower():
                soup = BeautifulSoup(response.text, 'html.parser')
                cards = soup.find_all('article')
                if not cards:
                    cards = soup.select('div[class*="freight"], tr, div[class*="card"], li[class*="load"]')

                for card in cards:
                    text = card.get_text(separator='\n', strip=True)
                    if len(text) > 15:
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        if lines not in all_scraped_loads:
                            all_scraped_loads.append(lines)

        formatted_loads = []
        for idx, lines in enumerate(all_scraped_loads, start=1):
            full_text = " | ".join(lines)
            origin = lines[0] if len(lines) > 0 else "غير محدد"
            destination = lines[1] if len(lines) > 1 else "غير محدد"
            
            distance_km = 100.0
            for line in lines:
                if "km" in line.lower() or "كم" in line:
                    nums = re.findall(r'\d+', line)
                    if nums:
                        distance_km = float(nums[0])
                        break

            hareth_distance = 150.0
            if hareth_lat is not None and hareth_lng is not None:
                hareth_distance = calculate_fast_road_distance(hareth_lat, hareth_lng, full_text)

            floor_price = round(distance_km * 1.3 * 1.2, 2)

            formatted_loads.append({
                "id": idx,
                "origin": origin,
                "destination": destination,
                "distance_km": distance_km,
                "hareth_distance_km": hareth_distance,
                "floor_price": floor_price,
                "vehicle_match": "Fiat Ducato L4H2",
                "raw_lines": lines
            })

        if hareth_lat is not None and hareth_lng is not None:
            formatted_loads.sort(key=lambda x: x['hareth_distance_km'])

        return jsonify({
            "status": "success",
            "driver": "حارث",
            "gps_active": hareth_lat is not None,
            "driver_location": REAL_DRIVER_LOCATION,
            "total_fetched": len(formatted_loads),
            "loads": formatted_loads
        }), 200

    except Exception as e:
        print(f"❌ [CRITICAL ERROR]: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def home_root():
    return jsonify({"status": "online", "message": "E-Kurier Ultra-Fast In-Memory Agent Active"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
