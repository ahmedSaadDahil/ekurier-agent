import os
import json
import httpx
from bs4 import BeautifulSoup
import re
import math
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
HARETH_WHATSAPP_NUMBER = "whatsapp:+4917656970147"

# تخزين إحداثيات حارث الحقيقية في الذاكرة المؤقتة (يعمل في أي مكان في أوروبا)
REAL_DRIVER_LOCATION = {
    "lat": 51.1657,
    "lng": 10.4515,
    "country": "Germany",
    "timestamp": "في انتظار أول تحديث حقيقي"
}

# ذاكرة مؤقتة للمسافات المحسوبة سابقاً لأي مدينة أوروبية لضمان السرعة الصاروخية ومنع الـ 502
DISTANCE_CACHE = {}

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.form.get("Body", "").strip()
    sender = request.form.get("From", "")
    resp = MessagingResponse()
    reply = resp.message()

    if not incoming_msg:
        reply.body("أهلاً بك يا أبو شهاب")
        return str(resp)

    if not GEMINI_API_KEY:
        reply.body("مفتاح الـ API غير مضبوط")
        return str(resp)

    if sender == HARETH_WHATSAPP_NUMBER:
        system_instruction = (
            "أنت مساعد نظام نقل مخصص حصرياً لأخيك حارث في عموم أوروبا. مهامك ثابتة ومحصورة في إدارة شحنات وحمولات "
            "سيارة Fiat Ducato (L3H2/L4H2). نطاق أسعار الشحن لديك بين 1.00 إلى 1.30 يورو لكل كيلومتر. "
            "كن دقيقاً، مختصراً، ومباشراً في تفاصيل الحمولات وعمليات الحجز."
        )
    else:
        system_instruction = (
            "أنت مساعد شخصي ذكي وشامل لأحمد (أبو شهاب). يمكنك الإجابة على أي سؤال يطلبه، "
            "سواء في البرمجة، التحليل، الأفكار، أو أي استفسار عام."
        )

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=incoming_msg,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7,
            ),
        )
        if response and response.text:
            reply.body(response.text)
        else:
            reply.body("عذراً يا أبو شهاب، لم أتمكن من صياغة الإجابة.")
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        reply.body("حدث خطأ في الاتصال بالنموذج.")

    return str(resp)

@app.route("/api/update-gps", methods=["POST"])
def update_gps():
    try:
        data = request.get_json()
        if data and 'lat' in data and 'lng' in data:
            REAL_DRIVER_LOCATION['lat'] = data['lat']
            REAL_DRIVER_LOCATION['lng'] = data['lng']
            REAL_DRIVER_LOCATION['country'] = data.get('country', 'Europe')
            REAL_DRIVER_LOCATION['timestamp'] = data.get('timestamp', 'فورية')
            print(f"📍 [EU GPS] تم تحديث موقع حارث: {REAL_DRIVER_LOCATION}")
            return jsonify({"status": "success", "message": "GPS updated successfully"}), 200
        return jsonify({"status": "error", "message": "Invalid GPS data"}), 400
    except Exception as e:
        print(f"❌ [GPS ERROR]: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/get-gps", methods=["GET"])
def get_gps():
    try:
        return jsonify({
            "status": "success",
            "driver": "حارث",
            "location": REAL_DRIVER_LOCATION
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# دالة ذكية وعامة لأوروبا تستخدم Gemini مع نظام تخزين مؤقت (Cache) لمنع بطء السيرفر
def get_europe_road_distance(hareth_lat, hareth_lng, origin_text):
    # تنظيف نص العنوان للبحث في الذاكرة المؤقتة
    cache_key = origin_text.strip().lower()
    if cache_key in DISTANCE_CACHE:
        return DISTANCE_CACHE[cache_key]

    if not GEMINI_API_KEY:
        return 150.0

    prompt = (
        f"حارث السائق متواجد في أوروبا عند الإحداثيات (خط العرض {hareth_lat}, خط الطول {hareth_lng}).\n"
        f"عنوان نقطة التحميل في أي دولة أوروبية هو: '{origin_text}'.\n"
        f"باعتبارك خبيراً بجغرافية الطرق الأوروبية، قدر مسافة القيادة الفعلية بالطرق (Road Distance) بالكيلومتر بين موقع حارث ونقطة التحميل.\n"
        f"أجب حصراً برقم صحيح أو عشري يمثل المسافة بالكيلومتر (مثال: 75 أو 340.5)، بدون أي كلمات أو حروف إضافية."
    )

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        if response and response.text:
            clean_nums = re.findall(r'\d+\.?\d*', response.text)
            if clean_nums:
                dist = float(clean_nums[0])
                # حفظ النتيجة في الذاكرة المؤقتة لكي لا يتم استدعاء النموذج لهذه المدینة مرة أخرى
                DISTANCE_CACHE[cache_key] = dist
                return dist
    except Exception as e:
        print(f"⚠️ EU AI Distance Error: {str(e)}")

    return 100.0  # قيمة احتياطية آمنة

# مسار جلب وترتيب الحمولات لعموم أوروبا بناءً على موقع حارث اللحظي
@app.route("/api/loads", methods=["GET"])
def get_live_hareth_loads():
    try:
        hareth_lat = REAL_DRIVER_LOCATION.get('lat', 51.1657)
        hareth_lng = REAL_DRIVER_LOCATION.get('lng', 10.4515)
        freights_url = "https://e-kurier.net/portal/freights"
        
        username = os.environ.get("EKURIER_USER", "")
        password = os.environ.get("EKURIER_PASS", "")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        }
        
        with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
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

            client.post(form_action, data=payload)

            all_scraped_loads = []
            max_pages = 2 

            for page_num in range(1, max_pages + 1):
                target_url = f"{freights_url}?page={page_num}"
                response = client.get(target_url)

                if response.status_code == 200 and "login" not in str(response.url).lower():
                    soup = BeautifulSoup(response.text, 'html.parser')
                    cards = soup.find_all('article')
                    if not cards:
                        cards = soup.select('div[class*="freight"], tr')

                    for card in cards:
                        text = card.get_text(separator='\n', strip=True)
                        if len(text) > 20:
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            if lines not in all_scraped_loads:
                                all_scraped_loads.append(lines)

        formatted_loads = []
        for idx, lines in enumerate(all_scraped_loads, start=1):
            origin = lines[0] if len(lines) > 0 else "غير محدد"
            destination = lines[1] if len(lines) > 1 else "غير محدد"
            
            distance_km = 100.0
            for line in lines:
                if "km" in line.lower() or "كم" in line:
                    nums = re.findall(r'\d+', line)
                    if nums:
                        distance_km = float(nums[0])
                        break

            # حساب المسافة الذكية لعموم أوروبا بناءً على موقع حارث اللحظي
            hareth_distance_to_origin = get_europe_road_distance(hareth_lat, hareth_lng, origin)

            floor_price = round(distance_km * 1.3 * 1.2, 2)

            formatted_loads.append({
                "id": idx,
                "origin": origin,
                "destination": destination,
                "weight": "1200 كغ (Fiat Ducato)",
                "distance_km": distance_km,
                "hareth_distance_km": hareth_distance_to_origin,
                "floor_price": floor_price,
                "vehicle_match": "Fiat Ducato L4H2",
                "raw_lines": lines
            })

        # ترتيب الحمولات تصاعدياً حسب الأقرب لموقع حارث أينما كان في أوروبا
        formatted_loads.sort(key=lambda x: x['hareth_distance_km'])

        return jsonify({
            "status": "success",
            "driver": "حارث",
            "driver_location": REAL_DRIVER_LOCATION,
            "total_fetched": len(formatted_loads),
            "loads": formatted_loads
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def home_root():
    return jsonify({"status": "online", "message": "E-Kurier Pan-European AI Routing Agent is active!"})

@app.route("/favicon.ico")
def favicon():
    return "", 204

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
