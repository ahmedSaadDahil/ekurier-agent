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

# مسار فحص وتسجيل الدخول مع كشف الحقول
@app.route("/api/loads", methods=["GET"])
def get_live_hareth_loads():
    print("\n==========================================")
    print("🔥 [DIAGNOSTIC] فحص صفحة تسجيل الدخول والحقول")
    print("==========================================")
    try:
        hareth_city = request.args.get("city", "").strip().lower()
        url = "https://e-kurier.net/portal/freights"
        
        username = os.environ.get("EKURIER_USER", "")
        password = os.environ.get("EKURIER_PASS", "")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
        }
        
        with httpx.Client(headers=headers, follow_redirects=True, timeout=30.0) as client:
            login_url = "https://e-kurier.net/portal/login"
            print("🔑 جاري جلب صفحة تسجيل الدخول...")
            login_page = client.get(login_url)
            
            soup_login = BeautifulSoup(login_page.text, 'html.parser')
            
            # طباعة كافة أسماء حقول الإدخال في الصفحة لنراها في اللوجات
            inputs = soup_login.find_all('input')
            input_names = [inp.get('name') for inp in inputs if inp.get('name')]
            print(f"📋 أسماء حقول الفورم المكتشفة في صفحة الدخول: {input_names}")

            token_input = soup_login.select_one('input[name="_token"]')
            token_val = token_input.get('value') if token_input else ""

            # نجرب الاحتمالين الشائعين لحقل البريد/المستخدم (email أو username)
            payload = {
                "email": username,      # سنختبر email أولاً
                "username": username,   # وكاحتياط لو كانوا يستخدمون username
                "password": password
            }
            if token_val:
                payload["_token"] = token_val

            print("🚀 جاري إرسال طلب POST لتسجيل الدخول...")
            login_resp = client.post(login_url, data=payload)
            print(f"🔑 استجابة تسجيل الدخول - Status: {login_resp.status_code} - URL النهائي: {login_resp.url}")

            all_scraped_loads = []
            max_pages = 2 

            for page_num in range(1, max_pages + 1):
                target_url = f"{url}?page={page_num}"
                response = client.get(target_url)
                print(f"📡 فحص الصفحة {page_num} - Status: {response.status_code} - URL النهائي: {response.url}")

                if "login" in str(response.url).lower():
                    print(f"⚠️ تحذير: لا زلنا في صفحة الـ Login للصفحة {page_num}!")

                if response.status_code == 200 and "login" not in str(response.url).lower():
                    soup = BeautifulSoup(response.text, 'html.parser')
                    cards = soup.find_all('article')
                    if not cards:
                        cards = soup.select('div[class*="freight"], tr')
                    
                    print(f"🔎 عدد البطاقات المكتشفة في الصفحة {page_num}: {len(cards)}")

                    for card in cards:
                        text = card.get_text(separator='\n', strip=True)
                        if len(text) > 20:
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            if lines not in all_scraped_loads:
                                all_scraped_loads.append(lines)

        print(f"📦 إجمالي الحمولات الخام المستخرجة: {len(all_scraped_loads)}")

        formatted_loads = []
        for idx, lines in enumerate(all_scraped_loads, start=1):
            origin = lines[0] if len(lines) > 0 else "غير محدد"
            destination = lines[1] if len(lines) > 1 else "غير محدد"
            
            distance_km = 300.0
            for line in lines:
                if "km" in line.lower() or "كم" in line:
                    nums = re.findall(r'\d+', line)
                    if nums:
                        distance_km = float(nums[0])
                        break

            if hareth_city and hareth_city not in origin.lower():
                continue

            floor_price = round(distance_km * 1.3 * 1.2, 2)

            formatted_loads.append({
                "id": idx,
                "origin": origin,
                "destination": destination,
                "weight": "1200 كغ (Fiat Ducato)",
                "distance_km": distance_km,
                "floor_price": floor_price,
                "vehicle_match": "Fiat Ducato L4H2",
                "raw_lines": lines
            })

        print(f"✅ الحمولات النهائية: {len(formatted_loads)}")
        print("==========================================\n")
        
        return jsonify({
            "status": "success",
            "driver": "حارث",
            "total_fetched": len(formatted_loads),
            "loads": formatted_loads
        }), 200

    except Exception as e:
        print(f"❌ [ERROR]: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def home_root():
    return jsonify({"status": "online", "message": "E-Kurier Diagnostic Agent is active!"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
