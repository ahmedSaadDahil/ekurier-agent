import os
import re
import httpx
from bs4 import BeautifulSoup
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
HARETH_WHATSAPP_NUMBER = "whatsapp:+4917656970147"

# تخزين آخر موقع حقيقي وصل من هاتف حارث
REAL_DRIVER_LOCATION = {
    "lat": None,
    "lng": None,
    "timestamp": "لم يتم استلام موقع GPS من الهاتف بعد"
}

CITY_COORDS_CACHE = {}
ROUTE_DISTANCE_CACHE = {}

def get_city_coordinates(full_card_text):
    match = re.search(r'\b(?:[A-Z]{1,2}-)?(\d{4,5})\s+([A-Za-zÄÖÜäöüß\-\s]{3,25})', full_card_text)
    query = ""
    if match:
        postal_code = match.group(1)
        city_name = match.group(2).strip().split('\n')[0]
        query = f"{postal_code} {city_name}, Europe"
    else:
        query = full_card_text[:60]

    if query in CITY_COORDS_CACHE:
        return CITY_COORDS_CACHE[query]

    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": query, "format": "json", "limit": 1}
        headers = {"User-Agent": "eKurierHarethAgent/1.0"}
        res = httpx.get(url, params=params, headers=headers, timeout=5.0)
        if res.status_code == 200 and res.json():
            data = res.json()[0]
            coords = (float(data["lat"]), float(data["lon"]))
            CITY_COORDS_CACHE[query] = coords
            return coords
    except Exception as e:
        print(f"🔍 [Geocoding Error]: {e}")
    return None

def get_real_europe_road_distance(h_lat, h_lng, dest_lat, dest_lng):
    cache_key = f"{round(h_lat,3)},{round(h_lng,3)}->{round(dest_lat,3)},{round(dest_lng,3)}"
    if cache_key in ROUTE_DISTANCE_CACHE:
        return ROUTE_DISTANCE_CACHE[cache_key]

    try:
        osrm_url = f"http://router.project-osrm.org/route/v1/driving/{h_lng},{h_lat};{dest_lng},{dest_lat}?overview=false"
        res = httpx.get(osrm_url, timeout=5.0)
        if res.status_code == 200:
            data = res.json()
            if data.get("code") == "Ok" and data.get("routes"):
                distance_meters = data["routes"][0]["distance"]
                distance_km = round(distance_meters / 1000.0, 1)
                ROUTE_DISTANCE_CACHE[cache_key] = distance_km
                return distance_km
    except Exception as e:
        print(f"🔍 [OSRM Error]: {e}")
    return 9999.0

@app.route("/api/update-gps", methods=["POST"])
def update_gps():
    try:
        data = request.get_json()
        if data and 'lat' in data and 'lng' in data:
            REAL_DRIVER_LOCATION['lat'] = float(data['lat'])
            REAL_DRIVER_LOCATION['lng'] = float(data['lng'])
            REAL_DRIVER_LOCATION['timestamp'] = data.get('timestamp', 'محدث الآن')
            print(f"📍 [GPS UPDATE]: تم استلام موقع حارث بنجاح -> {REAL_DRIVER_LOCATION}")
            return jsonify({"status": "success", "location": REAL_DRIVER_LOCATION}), 200
        return jsonify({"status": "error", "message": "بيانات GPS غير صالحة"}), 400
    except Exception as e:
        print(f"❌ [GPS ERROR]: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/get-gps", methods=["GET"])
def get_gps():
    return jsonify({
        "status": "success",
        "driver": "حارث",
        "location": REAL_DRIVER_LOCATION
    }), 200

@app.route("/api/loads", methods=["GET"])
def get_live_hareth_loads():
    try:
        req_lat = request.args.get('lat', type=float)
        req_lng = request.args.get('lng', type=float)

        if req_lat is not None and req_lng is not None:
            hareth_lat, hareth_lng = req_lat, req_lng
            REAL_DRIVER_LOCATION['lat'] = hareth_lat
            REAL_DRIVER_LOCATION['lng'] = hareth_lng
            print(f"📍 [LOADS API] استخدام إحداثيات حارث الواردة من التطبيق: {hareth_lat}, {hareth_lng}")
        else:
            hareth_lat = REAL_DRIVER_LOCATION.get('lat')
            hareth_lng = REAL_DRIVER_LOCATION.get('lng')
            print(f"📍 [LOADS API] استخدام الإحداثيات المخزنة مسبقاً: {hareth_lat}, {hareth_lng}")

        freights_url = "https://e-kurier.net/portal/freights"
        username = os.environ.get("EKURIER_USER", "")
        password = os.environ.get("EKURIER_PASS", "")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }
        
        print("🔐 [SCRAPER] بدء عملية الاتصال وتسجيل الدخول إلى e-kurier.net...")
        with httpx.Client(headers=headers, follow_redirects=True, timeout=25.0) as client:
            login_page_url = "https://e-kurier.net/portal/login"
            login_page = client.get(login_page_url)
            soup_login = BeautifulSoup(login_page.text, 'html.parser')
            
            token_input = soup_login.select_one('input[name="_token"]')
            token_val = token_input.get('value') if token_input else ""
            inv_input = soup_login.select_one('input[name="invitation_token"]')
            inv_val = inv_input.get('value') if inv_input else ""

            payload = {
                "_token": token_val,
                "invitation_token": inv_val,
                "email": username,
                "password": password
            }
            
            login_res = client.post(login_page_url, data=payload)
            print(f"🔐 [SCRAPER] حالة تسجيل الدخول (Status Code): {login_res.status_code}")
            print(f"🔐 [SCRAPER] الرابط الحالي بعد تسجيل الدخول: {login_res.url}")

            all_scraped_loads = []
            for page_num in range(1, 3):
                target_page = f"{freights_url}?page={page_num}"
                print(f"📄 [SCRAPER] جاري جلب الصفحة رقم {page_num}: {target_page}")
                
                response = client.get(target_page)
                print(f"📄 [SCRAPER] استجابة الصفحة {page_num} - Status: {response.status_code}, URL: {response.url}")
                
                if response.status_code == 200 and "login" not in str(response.url).lower():
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    cards = soup.find_all('article')
                    if not cards:
                        cards = soup.select('div[class*="freight"], tr, div[class*="card"], li[class*="load"]')
                    
                    print(f"🔍 [SCRAPER] عدد البطاقات/العناصر المكتشفة في الصفحة {page_num}: {len(cards)}")

                    for idx_card, card in enumerate(cards):
                        text = card.get_text(separator='\n', strip=True)
                        if len(text) > 15:
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            if lines not in all_scraped_loads:
                                all_scraped_loads.append(lines)
                                print(f"✅ [CARD {idx_card}] تم استخراج أسطر بنجاح: {lines[:2]} (عدد الأسطر: {len(lines)})")
                        else:
                            print(f"⚠️ [CARD {idx_card}] تم تخطي بطاقة قصيرة جداً أو فارغة")
                else:
                    print(f"⚠️ [SCRAPER] تم تحويلنا لصفحة تسجيل الدخول أو فشل جلب الصفحة {page_num}!")

        print(f"📦 [PARSER] إجمالي الحمولات الفريدة المستخرجة: {len(all_scraped_loads)}")

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

            road_dist_to_hareth = 9999.0
            if hareth_lat is not None and hareth_lng is not None:
                city_coords = get_city_coordinates(full_text)
                if city_coords:
                    road_dist_to_hareth = get_real_europe_road_distance(
                        hareth_lat, hareth_lng, city_coords[0], city_coords[1]
                    )

            floor_price = round(distance_km * 1.3 * 1.2, 2)

            formatted_loads.append({
                "id": idx,
                "origin": origin,
                "destination": destination,
                "distance_km": distance_km,
                "hareth_distance_km": road_dist_to_hareth,
                "floor_price": floor_price,
                "vehicle_match": "Fiat Ducato L4H2",
                "raw_lines": lines
            })

        if hareth_lat is not None and hareth_lng is not None:
            formatted_loads.sort(key=lambda x: x['hareth_distance_km'])

        print(f"🚀 [RESPONSE] إرسال {len(formatted_loads)} حمولة إلى تطبيق حارث بنجاح.")
        return jsonify({
            "status": "success",
            "driver": "حارث",
            "gps_active": hareth_lat is not None,
            "driver_location": REAL_DRIVER_LOCATION,
            "total_fetched": len(formatted_loads),
            "loads": formatted_loads
        }), 200

    except Exception as e:
        print(f"❌ [CRITICAL ERROR IN /api/loads]: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def home_root():
    return jsonify({"status": "online", "message": "E-Kurier Debug Routing Active"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
