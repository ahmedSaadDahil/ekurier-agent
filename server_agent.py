import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# استدعاء مفتاح الـ API والمتغيرات البيئية من إعدادات Render
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-2.0-flash"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    # استقبال الرسالة القادمة من الواتساب عبر Twilio
    incoming_msg = request.form.get("Body", "").strip()
    resp = MessagingResponse()
    reply = resp.message()

    if not incoming_msg:
        reply.body("أهلاً بك يا أبو شهاب، لم تصلني أي رسالة نصية.")
        return str(resp)

    if not GEMINI_API_KEY:
        reply.body("عذراً يا أبو شهاب، مفتاح النظام (API Key) غير مضبوط في السيرفر.")
        return str(resp)

    # إعداد رابط الطلب لـ Google Gemini API
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": incoming_msg}]
        }]
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            # استخراج الرد من استجابة نموذج الذكاء الاصطناعي
            ai_reply = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if ai_reply:
                reply.body(ai_reply)
            else:
                reply.body("عذراً يا أبو شهاب، لم أتمكن من صياغة إجابة واضحة.")
        else:
            # معالجة أخطاء الضغط العالي أو حالة السيرفر
            reply.body("عذراً يا أبو شهاب، حدث خطأ في النظام أو ضغط مؤقت على الخادم.")
            
    except Exception as e:
        reply.body(f"عذراً يا أبو شهاب، حدث خطأ غير متوقع في الاتصال.")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
