import os
import json
import httpx
from bs4 import BeautifulSoup
import re
from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
from google import genai
from google.genai import types

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
HARETH_WHATSAPP_NUMBER = "whatsapp:+4917656970147"

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
            "أنت مساعد نظام نقل مخصص حصرياً لأخيك حارث. مهامك ثابتة ومحصورة في إدارة شحنات وحمولات "
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

# مسار استقبال وتحديث الكوكيز من تطبيق حارث (WebView)
@app.route("/api/update-cookies", methods=["POST"])
def update_cookies():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data received"}), 400
        
        with open("session.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
            
        print("✅ تم تحديث وحفظ جلسة الكوكيز بنجاح عبر التطبيق!")
        return jsonify({"status": "success", "message": "تم تحديث وحفظ الجلسة بنجاح"}), 200
    except Exception as e:
        print(f"❌ Error updating cookies: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# مسار جلب الحمولات الصافي (الذي كان يعمل بنجاح تام وبدون أي تعقيد)
@app.route("/api/loads", methods=["GET"])
def get_live_hareth_loads():
    try:
        url = "https://e-kurier.net/portal/freights"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Referer": "https://e-kurier.net/portal/dashboard"
        }

        cookies = {}
        if os.path.exists("session.json"):
            try:
                with open("session.json", "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                    
                    cookie_list = []
                    if isinstance(session_data, list):
                        cookie_list = session_data
                    elif isinstance(session_data, dict) and "cookies" in session_data:
                        cookie_list = session_data["cookies"]

                    for cookie in cookie_list:
                        if isinstance(cookie, dict) and "name" in cookie and "value" in cookie:
                            cookies[cookie["name"]] = cookie["value"]
                            
                print(f"✅ تم تحميل {len(cookies)} كوكي بنجاح من session.json")
            except Exception as e:
                print(f"❌ Cookie error: {e}")

        all_scraped_loads = []
        max_pages = 3 

        with httpx.Client(headers=headers, cookies=cookies, follow_redirects=True, timeout=20.0) as client:
            for page_num in range(1, max_pages + 1):
                target_url = f"{url}?page={page_num}"
                response = client.get(target_url)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    cards = soup.find_all(['article', 'tr', 'div'], class_=lambda x: x and ('freight' in x.lower() or 'load' in x.lower() or 'item' in x.lower() or 'card' in x.lower()))
                    if not cards:
                        cards = soup.find_all(['article', 'tr'])

                    for card in cards:
                        text = card.get_text(separator='\n', strip=True)
                        if len(text) > 30 and ('DE ' in text or 'Loading' in text or 'km' in text or 'Unloading' in text):
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            if lines and lines not in all_scraped_loads:
                                all_scraped_loads.append(lines)

        formatted_loads = []
        seen_routes = set()

        for idx, lines in enumerate(all_scraped_loads, start=1):
            origin = "غير محدد"
            destination = "غير محدد"
            
            for i, line in enumerate(lines):
                if "DE " in line or "Loading" in line or "From" in line:
                    origin = line
                    if i + 1 < len(lines):
                        destination = lines[i + 1]
                    break
            
            if origin == "غير محدد" and len(lines) > 0:
                origin = lines[0]
            if destination == "غير محدد" and len(lines) > 1:
                destination = lines[1]

            route_key = f"{origin}-{destination}"
            if route_key in seen_routes:
                continue
            seen_routes.add(route_key)

            distance_km = 150.0
            for line in lines:
                if "km" in line.lower() or "كم" in line:
                    nums = re.findall(r'\d+', line)
                    if nums:
                        distance_km = float(nums[0])
                        break

            floor_price = round(distance_km * 1.3 * 1.2, 2)

            formatted_loads.append({
                "id": len(formatted_loads) + 1,
                "origin": origin,
                "destination": destination,
                "weight": "1200 كغ (Fiat Ducato)",
                "distance_km": distance_km,
                "floor_price": floor_price,
                "vehicle_match": "Fiat Ducato L4H2",
                "raw_lines": lines
            })

        return jsonify({
            "status": "success",
            "driver": "حارث",
            "total_fetched": len(formatted_loads),
            "loads": formatted_loads
        }), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def home_root():
    return jsonify({"status": "online", "message": "E-Kurier Clean Stable Agent is active!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
