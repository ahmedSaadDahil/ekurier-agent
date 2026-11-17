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

# دالة تسجيل الدخول التلقائي في حال انقطاع الجلسة
def auto_login_and_get_cookies():
    username = os.environ.get("EKURIER_USER")
    password = os.environ.get("EKURIER_PASS")
    
    if not username or not password:
        print("⚠️ متغيرات تسجيل الدخول غير متوفرة في البيئة.")
        return {}

    login_url = "https://e-kurier.net/portal/login"
    
    client = httpx.Client(follow_redirects=True, timeout=20.0)
    try:
        # جلب صفحة الدخول لأخذ الكوكيز الأولية والتوكنز إن وجدت
        resp = client.get(login_url)
        
        # إرسال بيانات الاعتماد
        login_data = {
            "email": username,
            "password": password
        }
        post_resp = client.post(login_url, data=login_data)
        
        if post_resp.status_code == 200:
            cookies_dict = {name: value for name, value in client.cookies.items()}
            if cookies_dict:
                print("✅ تم تسجيل الدخول تلقائياً وجلب كوكيز جديدة بنجاح!")
                # حفظها في session.json للاستخدام اللاحق
                session_data = {"cookies": [{"name": k, "value": v} for k, v in cookies_dict.items()]}
                with open("session.json", "w", encoding="utf-8") as f:
                    json.dump(session_data, f)
                return cookies_dict
    except Exception as e:
        print(f"Auto-login error: {e}")
    
    return {}

# مسار لتحديث الكوكيز يدوياً عبر التطبيق أيضاً
@app.route("/api/update-cookies", methods=["POST"])
def update_cookies():
    try:
        cookies_data = request.json
        if cookies_data:
            with open("session.json", "w", encoding="utf-8") as f:
                json.dump({"cookies": cookies_data}, f, ensure_ascii=False, indent=4)
            print("✅ تم تحديث وحفظ جلسة الكوكيز بنجاح عبر التطبيق!")
            return jsonify({"status": "success", "message": "Cookies updated successfully"}), 200
        return jsonify({"status": "error", "message": "Empty cookies data"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# مسار ديناميكي لجلب الحمولات الحية وتصفيتها
@app.route("/api/loads", methods=["GET"])
def get_live_hareth_loads():
    try:
        hareth_city = request.args.get("city", "").strip().lower()

        url = "https://e-kurier.net/portal/freights"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
            "Referer": "https://e-kurier.net/portal/dashboard"
        }

        # تحميل الكوكيز النشطة لجلسة الموقع
        cookies = {}
        if os.path.exists("session.json"):
            try:
                with open("session.json", "r", encoding="utf-8") as f:
                    session_data = json.load(f)
                    if "cookies" in session_data:
                        for cookie in session_data["cookies"]:
                            cookies[cookie["name"]] = cookie["value"]
            except Exception as e:
                print(f"Cookie load error: {e}")

        all_scraped_loads = []
        max_pages = 3 

        with httpx.Client(headers=headers, cookies=cookies, follow_redirects=True, timeout=20.0) as client:
            for page_num in range(1, max_pages + 1):
                target_url = f"{url}?page={page_num}"
                response = client.get(target_url)
                
