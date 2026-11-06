import os
import requests
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_NAME = "gemini-1.5-flash"

@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.form.get("Body", "").strip()
    resp = MessagingResponse()
    reply = resp.message()

    if not incoming_msg:
        reply.body("أهلاً بك يا أبو شهاب")
        return str(resp)

    if not GEMINI_API_KEY:
        reply.body("مفتاح الـ API غير موجود")
        return str(resp)

    # استخدام النسخة القياسية المستقرة لتجنب أي مشاكل في الموديلات الجديدة
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GEMINI_API_KEY}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{
            "parts": [{"text": incoming_msg}]
        }]
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        print("Google API Status Code:", response.status_code)
        print("Google API Response:", response.text)
        
        if response.status_code == 200:
            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                ai_reply = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                reply.body(ai_reply if ai_reply else "عذراً، لم أتمكن من صياغة الإجابة.")
            else:
                reply.body("عذراً، لم تصدر أي إجابة من النموذج.")
        else:
            reply.body(f"خطأ من الخادم: {response.status_code}")
            
    except Exception as e:
        print("Error connecting to Gemini:", str(e))
        reply.body("حدث خطأ في الاتصال بالذكاء الاصطناعي.")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
